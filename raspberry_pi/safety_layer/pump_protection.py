"""Pump Protection module for Safety Layer."""

import logging
from datetime import datetime
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

logger = logging.getLogger(__name__)


class PumpProtectionStatus(Enum):
    """Pump protection status."""
    OK = auto()
    MAX_RUNTIME_EXCEEDED = auto()
    COOLDOWN_REQUIRED = auto()
    OVERHEATING = auto()


@dataclass
class PumpProtectionState:
    """Pump protection state."""
    status: PumpProtectionStatus = PumpProtectionStatus.OK
    current_runtime_seconds: int = 0
    max_runtime_seconds: int = 3600
    cooldown_required_seconds: int = 600
    last_turned_on_at: Optional[datetime] = None
    last_turned_off_at: Optional[datetime] = None
    total_runs_today: int = 0
    pump_temperature_c: Optional[float] = None
    overheat_threshold_c: float = 80.0


class PumpProtector:
    """Protects pump from overuse and overheating."""

    def __init__(
        self,
        max_runtime_seconds: int = 3600,
        cooldown_required_seconds: int = 30,   # was 600 (10 min) -- reduced for testing. Restore to 600 for production.
        overheat_threshold_c: float = 80.0
    ):
        self.state = PumpProtectionState(
            max_runtime_seconds=max_runtime_seconds,
            cooldown_required_seconds=cooldown_required_seconds,
            overheat_threshold_c=overheat_threshold_c
        )
        logger.info("PumpProtector initialized")

    def on_pump_start(self) -> PumpProtectionStatus:
        """
        Called when pump starts.

        Returns:
            Current protection status
        """
        # Check cooldown
        if self.state.last_turned_off_at:
            cooldown_needed = self.state.cooldown_required_seconds
            elapsed_since_off = (datetime.now() - self.state.last_turned_off_at).total_seconds()
            if elapsed_since_off < cooldown_needed:
                self.state.status = PumpProtectionStatus.COOLDOWN_REQUIRED
                logger.warning(f"Pump requires cooldown. Wait {cooldown_needed - elapsed_since_off:.1f}s")
                return self.state.status

        self.state.last_turned_on_at = datetime.now()
        self.state.current_runtime_seconds = 0
        self.state.status = PumpProtectionStatus.OK
        logger.info("Pump protection monitoring started")
        return self.state.status

    def update_runtime(self, runtime_seconds: int) -> PumpProtectionStatus:
        """
        Update current pump runtime.

        Args:
            runtime_seconds: How long pump has been running

        Returns:
            Current protection status
        """
        self.state.current_runtime_seconds = runtime_seconds

        # Check max runtime
        if runtime_seconds >= self.state.max_runtime_seconds:
            self.state.status = PumpProtectionStatus.MAX_RUNTIME_EXCEEDED
            logger.critical(f"Pump MAX RUNTIME EXCEEDED: {runtime_seconds}s")
            return self.state.status

        return self.state.status

    def update_temperature(self, temperature_c: Optional[float]) -> PumpProtectionStatus:
        """
        Update pump temperature reading.

        Args:
            temperature_c: Pump temperature in Celsius

        Returns:
            Current protection status
        """
        self.state.pump_temperature_c = temperature_c

        if temperature_c is not None and temperature_c >= self.state.overheat_threshold_c:
            self.state.status = PumpProtectionStatus.OVERHEATING
            logger.critical(f"Pump OVERHEATING: {temperature_c}°C")
            return self.state.status

        return self.state.status

    def on_pump_stop(self) -> None:
        """Called when pump stops."""
        self.state.last_turned_off_at = datetime.now()
        self.state.status = PumpProtectionStatus.OK
        logger.info(f"Pump stopped. Runtime: {self.state.current_runtime_seconds}s")

    def can_start_pump(self) -> tuple[bool, str]:
        """
        Check if pump can be started safely.

        Returns:
            (can_start, reason)
        """
        if self.state.status == PumpProtectionStatus.MAX_RUNTIME_EXCEEDED:
            return False, "Max runtime exceeded"

        if self.state.status == PumpProtectionStatus.OVERHEATING:
            return False, "Pump overheating"

        if self.state.last_turned_off_at:
            elapsed = (datetime.now() - self.state.last_turned_off_at).total_seconds()
            if elapsed < self.state.cooldown_required_seconds:
                remaining = self.state.cooldown_required_seconds - elapsed
                return False, f"Cooldown required: {remaining:.1f}s remaining"

        return True, "OK"

    def get_state(self) -> PumpProtectionState:
        """Get current pump protection state."""
        return self.state

    def reset_daily_stats(self) -> None:
        """Reset daily run counter."""
        self.state.total_runs_today = 0
        logger.info("Daily pump stats reset")