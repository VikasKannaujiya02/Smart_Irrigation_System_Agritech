"""Dry Run Protection module for Safety Layer."""

import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

logger = logging.getLogger(__name__)


class DryRunStatus(Enum):
    """Dry run detection status."""
    NORMAL = auto()
    MONITORING = auto()
    DRY_RUN_DETECTED = auto()
    RECOVERING = auto()


@dataclass
class DryRunState:
    """Dry run state."""
    status: DryRunStatus = DryRunStatus.NORMAL
    pump_start_time: Optional[datetime] = None
    flow_sensor_reading: Optional[float] = None
    last_checked_at: Optional[datetime] = None
    dry_run_count: int = 0
    last_dry_run_at: Optional[datetime] = None


class DryRunProtector:
    """Protects pump from dry running."""

    def __init__(
        self,
        no_flow_detection_seconds: int = 30,
        max_dry_runs_before_lockout: int = 3,
        lockout_duration_minutes: int = 30
    ):
        self.no_flow_detection_seconds = no_flow_detection_seconds
        self.max_dry_runs_before_lockout = max_dry_runs_before_lockout
        self.lockout_duration_minutes = lockout_duration_minutes
        self.state = DryRunState()
        logger.info("DryRunProtector initialized")

    def start_monitoring(self, pump_start_time: Optional[datetime] = None) -> None:
        """
        Start dry run monitoring when pump turns on.

        Args:
            pump_start_time: When the pump started (defaults to now)
        """
        self.state.pump_start_time = pump_start_time or datetime.now()
        self.state.status = DryRunStatus.MONITORING
        logger.info("Dry run monitoring started")

    def update_flow_reading(self, flow_reading: Optional[float]) -> DryRunStatus:
        """
        Update with current flow sensor reading.

        Args:
            flow_reading: Current flow rate (L/min or similar)

        Returns:
            Current dry run status
        """
        self.state.flow_sensor_reading = flow_reading
        self.state.last_checked_at = datetime.now()

        if self.state.status != DryRunStatus.MONITORING:
            return self.state.status

        # Check if no flow for detection period
        if self.state.pump_start_time:
            elapsed = (datetime.now() - self.state.pump_start_time).total_seconds()
            if elapsed >= self.no_flow_detection_seconds:
                # Check if flow is too low or None
                if flow_reading is None or flow_reading <= 0.1:
                    self._detect_dry_run()

        return self.state.status

    def _detect_dry_run(self) -> None:
        """Handle dry run detection."""
        self.state.status = DryRunStatus.DRY_RUN_DETECTED
        self.state.dry_run_count += 1
        self.state.last_dry_run_at = datetime.now()
        logger.critical(f"DRY RUN DETECTED! Dry run count: {self.state.dry_run_count}")

    def reset_monitoring(self) -> None:
        """Reset monitoring when pump stops."""
        self.state.pump_start_time = None
        if self.state.status == DryRunStatus.MONITORING:
            self.state.status = DryRunStatus.NORMAL
        logger.info("Dry run monitoring reset")

    def is_locked_out(self) -> bool:
        """
        Check if system is locked out due to repeated dry runs.

        Returns:
            True if locked out
        """
        if self.state.dry_run_count < self.max_dry_runs_before_lockout:
            return False

        if self.state.last_dry_run_at:
            lockout_end = self.state.last_dry_run_at + timedelta(minutes=self.lockout_duration_minutes)
            if datetime.now() < lockout_end:
                return True

        return False

    def get_state(self) -> DryRunState:
        """Get current dry run state."""
        return self.state

    def reset_dry_run_count(self) -> None:
        """Reset dry run counter."""
        self.state.dry_run_count = 0
        self.state.status = DryRunStatus.NORMAL
        logger.info("Dry run counter reset")
