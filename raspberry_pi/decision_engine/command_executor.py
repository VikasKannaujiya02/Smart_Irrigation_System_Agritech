"""Command execution manager for pump commands with safety, LoRa send, ACK tracking, and persistence."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any

from .models import PumpCommand, IrrigationAction
from raspberry_pi.communication import (
    CommandManager,
    AckManager,
    RetryManager,
    CommandType,
)
from raspberry_pi.safety_layer import FailsafeManager, SafetyOverride

logger = logging.getLogger(__name__)


class CommandExecutionResult:
    """Result of executing a pump command."""

    def __init__(
        self,
        success: bool,
        action: IrrigationAction,
        message: str,
        attempts: int = 0,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.action = action
        self.message = message
        self.attempts = attempts
        self.details = details or {}
        self.timestamp = time.time()


class CommandExecutor:
    """Executes pump commands through the existing communication and gateway layers."""

    def __init__(
        self,
        failsafe_manager: FailsafeManager,
        command_manager: Optional[CommandManager] = None,
        ack_manager: Optional[AckManager] = None,
        retry_manager: Optional[RetryManager] = None,
        gateway: Any | None = None,
        repository_registry: Any | None = None,
        pump_device_id: int = 4,  # PUMP_CONTROLLER (was wrongly 2 = SENSOR_NODE)
        command_timeout_seconds: float = 10.0,
    ):
        self.failsafe_manager = failsafe_manager
        self.command_manager = command_manager or CommandManager()
        self.ack_manager = ack_manager or AckManager(command_timeout_seconds)
        self.retry_manager = retry_manager or RetryManager()
        self.gateway = gateway
        self.repository_registry = repository_registry
        self.pump_device_id = pump_device_id
        self.command_timeout_seconds = command_timeout_seconds
        self._command_history: list[CommandExecutionResult] = []
        logger.info("CommandExecutor initialized")

    def execute_pump_command(self, action: IrrigationAction) -> CommandExecutionResult:
        """Execute a pump command after failsafe checks and register it for ACK tracking."""
        logger.info("Executing pump command: %s", action.pump_command.name)
        if action.pump_command == PumpCommand.ON and action.mode.name != "MANUAL":
            safety_result = self.failsafe_manager.check_irrigation_safety()
            if safety_result.override in [SafetyOverride.BLOCKED, SafetyOverride.EMERGENCY]:
                result = CommandExecutionResult(
                    success=False,
                    action=action,
                    message=f"Failsafe blocked: {safety_result.reason}",
                    attempts=0,
                    details={"safety_override": safety_result.override.name},
                )
                self._persist_result(result)
                self._log_command(result)
                return result
        elif action.pump_command == PumpCommand.ON:
            logger.info("Bypassing irrigation safety gate for manual ON command")
        elif action.pump_command == PumpCommand.OFF:
            logger.info("Bypassing irrigation safety gate for OFF command")

        command_type = CommandType.MOTOR_ON if action.pump_command == PumpCommand.ON else CommandType.MOTOR_OFF
        command_params: dict[str, object] = {}
        if action.duration_seconds:
            command_params["duration_seconds"] = int(action.duration_seconds)
        if action.water_volume_liters is not None:
            command_params["water_volume_liters"] = float(action.water_volume_liters)

        command_packet = self.command_manager.build_command(
            destination_device=self.pump_device_id,
            command_type=command_type,
            parameters=command_params,
        )
        self.ack_manager.register(command_packet)

        details = {
            "target_device_id": command_packet.destination_device,
            "sequence_number": command_packet.sequence_number,
            "command_type": command_type.name,
            "ack_status": "PENDING",
        }

        try:
            if self.gateway is None:
                raise RuntimeError("Hardware Validation Required: gateway transport is not configured")
            self.gateway.send_packet(command_packet)
        except Exception as exc:
            self.ack_manager.remove(command_packet)
            result = CommandExecutionResult(
                success=False,
                action=action,
                message=str(exc),
                attempts=1,
                details={**details, "ack_status": "NOT_SENT"},
            )
            self._persist_result(result)
            self._log_command(result)
            return result

        if action.pump_command == PumpCommand.ON:
            self.failsafe_manager.on_pump_start()
        elif action.pump_command == PumpCommand.OFF:
            self.failsafe_manager.on_pump_stop()

        result = CommandExecutionResult(
            success=True,
            action=action,
            message="Command sent; ACK verification is tracked by AckManager and requires pump-controller hardware response",
            attempts=1,
            details={**details, "ack_status": "Hardware Validation Required"},
        )
        self._persist_result(result)
        self._log_command(result)
        return result

    def _persist_result(self, result: CommandExecutionResult) -> None:
        """Persist command and ACK tracking state when repositories are available."""
        if self.repository_registry is None:
            return
        command_id = f"cmd-{int(result.timestamp * 1000)}"
        status = "SENT" if result.success else "FAILED"
        sent_at = datetime.utcfromtimestamp(result.timestamp).isoformat() if result.success else None
        try:
            self.repository_registry.commands.insert({
                "command_id": command_id,
                "target_device_id": int(result.details.get("target_device_id", self.pump_device_id)),
                "command_type": result.details.get("command_type", result.action.pump_command.name),
                "status": status,
                "payload_json": json.dumps({
                    "message": result.message,
                    "action": result.action.pump_command.name,
                    "decision": result.action.decision.name,
                    "details": result.details,
                }),
                "sequence_number": result.details.get("sequence_number"),
                "retry_count": max(result.attempts - 1, 0),
                "sent_at": sent_at,
                "error_message": None if result.success else result.message,
            })
            if result.details.get("sequence_number") is not None:
                self.repository_registry.ack_history.insert({
                    "device_id": int(result.details.get("target_device_id", self.pump_device_id)),
                    "sequence_number": int(result.details["sequence_number"]),
                    "packet_type": "COMMAND",
                    "latency_ms": None,
                    "retry_count": max(result.attempts - 1, 0),
                    "status": "ACKED" if result.details.get("ack_status") == "ACKED" else "TIMEOUT",
                })
        except Exception:
            logger.exception("Failed to persist command execution result")

    def _log_command(self, result: CommandExecutionResult) -> None:
        """Log command execution history."""
        self._command_history.append(result)
        if len(self._command_history) > 100:
            self._command_history.pop(0)
        status = "SUCCESS" if result.success else "FAILURE"
        logger.info(
            "[%s] Command: %s, Decision: %s, Message: %s, Attempts: %s",
            status,
            result.action.pump_command.name,
            result.action.decision.name,
            result.message,
            result.attempts,
        )

    def get_command_history(self, limit: int = 20) -> list[CommandExecutionResult]:
        """Get command execution history."""
        return self._command_history[-limit:]
