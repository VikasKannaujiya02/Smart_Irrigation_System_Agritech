"""Pump Controller Logic handles pump commands based on system constraints."""

from __future__ import annotations

import logging

from .models import (
    PumpStatus,
    TankStatus,
    SystemConfig,
    PumpCommand,
    IrrigationAction,
    IrrigationDecision,
)

logger = logging.getLogger(__name__)


class PumpControllerLogic:
    """Processes final pump commands, applying safety constraints."""

    def __init__(
        self,
        system_config: SystemConfig,
    ):
        """Initialize pump controller logic.
        
        Args:
            system_config: System-wide configuration
        """
        self.system_config = system_config

    def evaluate(
        self,
        proposed_action: IrrigationAction,
        pump_status: PumpStatus,
        tank_status: TankStatus,
    ) -> IrrigationAction:
        """Evaluate proposed action and apply safety constraints.
        
        Args:
            proposed_action: Proposed irrigation action
            pump_status: Current pump status
            tank_status: Current tank status
            
        Returns:
            Final irrigation action with safety constraints applied
        """
        logger.info("Evaluating pump safety constraints")
        
        reasons = proposed_action.reasons.copy()
        
        # 1. Check if tank is empty (highest priority)
        if tank_status.is_empty:
            logger.warning("Tank is empty, cannot irrigate")
            return IrrigationAction(
                pump_command=PumpCommand.OFF,
                decision=IrrigationDecision.DO_NOT_IRRIGATE,
                mode=proposed_action.mode,
                confidence=1.0,
                reasons=["Tank is empty - cannot pump"] + reasons,
                duration_seconds=0,
            )
            
        # 2. Check if tank is low
        if tank_status.is_low:
            logger.warning("Tank level is low")
            reasons.append("Tank level is low")
            
        # 3. Check pump max runtime
        if pump_status.runtime_seconds >= self.system_config.max_pump_runtime_seconds:
            logger.warning("Pump has reached maximum runtime")
            reasons.append(f"Pump max runtime reached ({self.system_config.max_pump_runtime_seconds}s)")
            
        # 4. Check pump fault
        if pump_status.is_fault:
            logger.warning("Pump has active fault")
            return IrrigationAction(
                pump_command=PumpCommand.OFF,
                decision=IrrigationDecision.DO_NOT_IRRIGATE,
                mode=proposed_action.mode,
                confidence=1.0,
                reasons=["Pump has active fault"] + reasons,
            )
            
        # If we get here, apply the proposed action
        return IrrigationAction(
            pump_command=proposed_action.pump_command,
            decision=proposed_action.decision,
            mode=proposed_action.mode,
            confidence=proposed_action.confidence,
            reasons=reasons,
            duration_seconds=proposed_action.duration_seconds,
            water_volume_liters=proposed_action.water_volume_liters,
        )
