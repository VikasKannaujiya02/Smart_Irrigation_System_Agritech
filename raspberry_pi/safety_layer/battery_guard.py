"""Battery Guard module for Safety Layer."""

import logging
from datetime import datetime
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class BatteryStatus(Enum):
    """Battery health status."""
    FULL = auto()
    NORMAL = auto()
    LOW = auto()
    CRITICAL = auto()
    UNKNOWN = auto()


@dataclass
class BatteryState:
    """Battery state."""
    device_id: str
    voltage: Optional[float] = None
    percent: Optional[float] = None
    status: BatteryStatus = BatteryStatus.UNKNOWN
    last_updated: Optional[datetime] = None
    low_threshold_percent: float = 20.0
    critical_threshold_percent: float = 10.0
    low_threshold_voltage: float = 3.5
    critical_threshold_voltage: float = 3.2


class BatteryGuard:
    """Monitors battery health across devices."""

    def __init__(self):
        self.batteries: Dict[str, BatteryState] = {}
        logger.info("BatteryGuard initialized")

    def register_device(
        self,
        device_id: str,
        low_threshold_percent: float = 20.0,
        critical_threshold_percent: float = 10.0,
        low_threshold_voltage: float = 3.5,
        critical_threshold_voltage: float = 3.2
    ) -> None:
        """
        Register a device for battery monitoring.

        Args:
            device_id: Unique device identifier
            low_threshold_percent: Low battery threshold (%)
            critical_threshold_percent: Critical battery threshold (%)
            low_threshold_voltage: Low voltage threshold (V)
            critical_threshold_voltage: Critical voltage threshold (V)
        """
        self.batteries[device_id] = BatteryState(
            device_id=device_id,
            low_threshold_percent=low_threshold_percent,
            critical_threshold_percent=critical_threshold_percent,
            low_threshold_voltage=low_threshold_voltage,
            critical_threshold_voltage=critical_threshold_voltage
        )
        logger.info(f"Registered device for battery monitoring: {device_id}")

    def update_battery(
        self,
        device_id: str,
        voltage: Optional[float] = None,
        percent: Optional[float] = None
    ) -> BatteryStatus:
        """
        Update battery reading for a device.

        Args:
            device_id: Which device
            voltage: Battery voltage (V)
            percent: Battery charge (%)

        Returns:
            Current battery status
        """
        if device_id not in self.batteries:
            logger.warning(f"Device {device_id} not registered for battery monitoring")
            return BatteryStatus.UNKNOWN

        state = self.batteries[device_id]
        state.voltage = voltage
        state.percent = percent
        state.last_updated = datetime.now()

        # Determine status
        if percent is not None:
            if percent <= state.critical_threshold_percent:
                state.status = BatteryStatus.CRITICAL
                logger.critical(f"Device {device_id} battery CRITICAL: {percent}%")
            elif percent <= state.low_threshold_percent:
                state.status = BatteryStatus.LOW
                logger.warning(f"Device {device_id} battery LOW: {percent}%")
            elif percent >= 95.0:
                state.status = BatteryStatus.FULL
            else:
                state.status = BatteryStatus.NORMAL
        elif voltage is not None:
            if voltage <= state.critical_threshold_voltage:
                state.status = BatteryStatus.CRITICAL
                logger.critical(f"Device {device_id} battery CRITICAL: {voltage}V")
            elif voltage <= state.low_threshold_voltage:
                state.status = BatteryStatus.LOW
                logger.warning(f"Device {device_id} battery LOW: {voltage}V")
            else:
                state.status = BatteryStatus.NORMAL
        else:
            state.status = BatteryStatus.UNKNOWN

        return state.status

    def get_battery_status(self, device_id: str) -> Optional[BatteryStatus]:
        """Get battery status for a device."""
        if device_id in self.batteries:
            return self.batteries[device_id].status
        return None

    def is_battery_critical(self, device_id: str) -> bool:
        """Check if device battery is critical."""
        status = self.get_battery_status(device_id)
        return status == BatteryStatus.CRITICAL

    def is_battery_low(self, device_id: str) -> bool:
        """Check if device battery is low or critical."""
        status = self.get_battery_status(device_id)
        return status in (BatteryStatus.LOW, BatteryStatus.CRITICAL)

    def get_all_statuses(self) -> Dict[str, BatteryStatus]:
        """Get battery status for all devices."""
        return {did: b.status for did, b in self.batteries.items()}

    def get_state(self, device_id: str) -> Optional[BatteryState]:
        """Get full battery state for a device."""
        return self.batteries.get(device_id)
