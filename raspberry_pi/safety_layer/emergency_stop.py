"""Emergency Stop module for Safety Layer."""

import logging
from datetime import datetime
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

logger = logging.getLogger(__name__)


class EmergencyStopReason(Enum):
    """Reasons for emergency stop."""
    MANUAL = auto()
    DRY_RUN_DETECTED = auto()
    PUMP_OVERRUN = auto()
    TANK_EMPTY = auto()
    SENSOR_FAULT_CRITICAL = auto()
    SYSTEM_WATCHDOG = auto()
    COMMUNICATION_FAILURE = auto()


@dataclass
class EmergencyStopState:
    """Emergency stop state."""
    is_active: bool = False
    reason: Optional[EmergencyStopReason] = None
    activated_at: Optional[datetime] = None
    deactivated_at: Optional[datetime] = None
    deactivated_by: Optional[str] = None


class EmergencyStopManager:
    """Manages emergency stop functionality."""

    def __init__(self):
        self.state = EmergencyStopState()
        logger.info("EmergencyStopManager initialized")

    def activate(self, reason: EmergencyStopReason) -> bool:
        """
        Activate emergency stop.

        Args:
            reason: Reason for emergency stop

        Returns:
            True if activated, False if already active
        """
        if self.state.is_active:
            logger.warning(f"Emergency stop already active (reason: {self.state.reason})")
            return False

        self.state.is_active = True
        self.state.reason = reason
        self.state.activated_at = datetime.now()
        logger.critical(f"EMERGENCY STOP ACTIVATED! Reason: {reason.name}")
        return True

    def deactivate(self, deactivated_by: str = "system") -> bool:
        """
        Deactivate emergency stop.

        Args:
            deactivated_by: Who deactivated the stop

        Returns:
            True if deactivated, False if not active
        """
        if not self.state.is_active:
            logger.warning("Emergency stop is not active")
            return False

        self.state.is_active = False
        self.state.deactivated_at = datetime.now()
        self.state.deactivated_by = deactivated_by
        logger.warning(f"Emergency stop deactivated by {deactivated_by}")
        return True

    def is_emergency_active(self) -> bool:
        """Check if emergency stop is active."""
        return self.state.is_active

    def get_state(self) -> EmergencyStopState:
        """Get current emergency stop state."""
        return self.state
