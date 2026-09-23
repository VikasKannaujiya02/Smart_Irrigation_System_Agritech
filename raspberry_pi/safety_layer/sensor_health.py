"""Sensor Health Validation module for Safety Layer."""

import logging
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class SensorHealthStatus(Enum):
    """Sensor health status."""
    HEALTHY = auto()
    DEGRADED = auto()
    FAULTY = auto()
    OFFLINE = auto()


@dataclass
class SensorReading:
    """Single sensor reading."""
    value: Optional[float]
    timestamp: datetime
    is_valid: bool = True


@dataclass
class SensorHealthState:
    """State for a single sensor."""
    sensor_id: str
    sensor_type: str
    status: SensorHealthStatus = SensorHealthStatus.HEALTHY
    min_valid_value: Optional[float] = None
    max_valid_value: Optional[float] = None
    readings: List[SensorReading] = field(default_factory=list)
    max_readings_history: int = 100
    last_reading_at: Optional[datetime] = None
    timeout_seconds: int = 300
    consecutive_invalid: int = 0
    max_consecutive_invalid: int = 5
    fault_count: int = 0


class SensorHealthMonitor:
    """Monitors and validates sensor health."""

    def __init__(self):
        self.sensors: Dict[str, SensorHealthState] = {}
        logger.info("SensorHealthMonitor initialized")

    def register_sensor(
        self,
        sensor_id: str,
        sensor_type: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        timeout_seconds: int = 300,
        max_consecutive_invalid: int = 5
    ) -> None:
        """
        Register a sensor for monitoring.

        Args:
            sensor_id: Unique sensor identifier
            sensor_type: Type of sensor (e.g., "soil_moisture")
            min_value: Minimum valid value
            max_value: Maximum valid value
            timeout_seconds: Timeout before marking as offline
            max_consecutive_invalid: Max invalid readings before marking as faulty
        """
        self.sensors[sensor_id] = SensorHealthState(
            sensor_id=sensor_id,
            sensor_type=sensor_type,
            min_valid_value=min_value,
            max_valid_value=max_value,
            timeout_seconds=timeout_seconds,
            max_consecutive_invalid=max_consecutive_invalid
        )
        logger.info(f"Registered sensor: {sensor_id} ({sensor_type})")

    def validate_reading(
        self,
        sensor_id: str,
        value: Optional[float],
        timestamp: Optional[datetime] = None
    ) -> tuple[bool, SensorHealthStatus]:
        """
        Validate a sensor reading.

        Args:
            sensor_id: Which sensor
            value: Sensor reading
            timestamp: When reading was taken (defaults to now)

        Returns:
            (is_valid, current_status)
        """
        if sensor_id not in self.sensors:
            logger.warning(f"Sensor {sensor_id} not registered")
            return False, SensorHealthStatus.OFFLINE

        state = self.sensors[sensor_id]
        ts = timestamp or datetime.now()
        state.last_reading_at = ts

        # Check if value is valid
        is_valid = True
        if value is None:
            is_valid = False
        else:
            if state.min_valid_value is not None and value < state.min_valid_value:
                is_valid = False
            if state.max_valid_value is not None and value > state.max_valid_value:
                is_valid = False

        # Add reading to history
        reading = SensorReading(value=value, timestamp=ts, is_valid=is_valid)
        state.readings.append(reading)
        if len(state.readings) > state.max_readings_history:
            state.readings.pop(0)

        # Update status
        if not is_valid:
            state.consecutive_invalid += 1
            if state.consecutive_invalid >= state.max_consecutive_invalid:
                state.status = SensorHealthStatus.FAULTY
                state.fault_count += 1
                logger.error(f"Sensor {sensor_id} FAULTY: {state.consecutive_invalid} invalid readings")
            elif state.consecutive_invalid >= 2:
                state.status = SensorHealthStatus.DEGRADED
                logger.warning(f"Sensor {sensor_id} DEGRADED: {state.consecutive_invalid} invalid readings")
        else:
            state.consecutive_invalid = 0
            if state.status != SensorHealthStatus.FAULTY:
                state.status = SensorHealthStatus.HEALTHY

        return is_valid, state.status

    def check_timeouts(self) -> Dict[str, SensorHealthStatus]:
        """
        Check all sensors for timeout.

        Returns:
            Dict of sensor_id to status
        """
        results = {}
        now = datetime.now()

        for sensor_id, state in self.sensors.items():
            if state.last_reading_at:
                elapsed = (now - state.last_reading_at).total_seconds()
                if elapsed > state.timeout_seconds:
                    if state.status != SensorHealthStatus.FAULTY:
                        state.status = SensorHealthStatus.OFFLINE
                        logger.warning(f"Sensor {sensor_id} OFFLINE (timeout)")

            results[sensor_id] = state.status

        return results

    def get_sensor_status(self, sensor_id: str) -> Optional[SensorHealthStatus]:
        """Get status of a specific sensor."""
        if sensor_id in self.sensors:
            return self.sensors[sensor_id].status
        return None

    def get_all_statuses(self) -> Dict[str, SensorHealthStatus]:
        """Get status of all sensors."""
        return {sid: s.status for sid, s in self.sensors.items()}

    def reset_sensor(self, sensor_id: str) -> bool:
        """Reset a sensor's fault state."""
        if sensor_id not in self.sensors:
            return False

        state = self.sensors[sensor_id]
        state.status = SensorHealthStatus.HEALTHY
        state.consecutive_invalid = 0
        logger.info(f"Sensor {sensor_id} reset to HEALTHY")
        return True
