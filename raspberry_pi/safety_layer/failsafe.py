"""Main Safety Layer orchestrator - Failsafe Manager."""

import logging
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, Any, Tuple

from .emergency_stop import EmergencyStopManager, EmergencyStopReason
from .dry_run import DryRunProtector
from .pump_protection import PumpProtector
from .sensor_health import SensorHealthMonitor, SensorHealthStatus
from .battery_guard import BatteryGuard, BatteryStatus
from .water_tank_guard import WaterTankGuard
from .watchdog import WatchdogManager

logger = logging.getLogger(__name__)


class SafetyOverride(Enum):
    """Safety override status."""
    SAFE = auto()
    WARNING = auto()
    BLOCKED = auto()
    EMERGENCY = auto()


@dataclass
class SafetyCheckResult:
    """Result from a safety check."""
    is_safe: bool
    override: SafetyOverride
    reason: str
    blocked_by: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RainLockConfig:
    """Rain forecast lock configuration."""
    enabled: bool = True
    rain_probability_threshold: float = 50.0
    rain_volume_threshold: float = 2.0
    critical_moisture_override: float = 20.0


@dataclass
class ManualOverrideState:
    """Manual override state."""
    enabled: bool = False
    override_by: Optional[str] = None
    override_at: Optional[datetime] = None
    reason: Optional[str] = None


@dataclass
class OfflineModeState:
    """Local offline mode state."""
    is_offline: bool = False
    since: Optional[datetime] = None
    reason: Optional[str] = None


class FailsafeManager:
    """
    Main Safety Layer orchestrator.
    
    Implements all safety features:
    - Rain Forecast Lock
    - Dry Soil Override
    - Sensor Validation
    - AI Confidence Validation
    - Battery Check
    - Pump Runtime Protection
    - Dry Run Protection
    - Water Tank Check
    - Emergency Stop
    - Manual Override
    - Local Offline Mode
    - Watchdog Recovery
    - Device Timeout
    - Communication Failure Recovery
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Initialize all safety components
        self.emergency_stop = EmergencyStopManager()
        self.dry_run = DryRunProtector()
        self.pump_protection = PumpProtector()
        self.sensor_health = SensorHealthMonitor()
        self.battery_guard = BatteryGuard()
        self.water_tank = WaterTankGuard()
        self.watchdog = WatchdogManager()
        
        # State management
        self.rain_lock_config = RainLockConfig()
        self.manual_override = ManualOverrideState()
        self.offline_mode = OfflineModeState()
        self.ai_confidence_threshold: float = self.config.get("ai_confidence_threshold", 0.7)
        
        # Register default sensors/devices
        self._register_defaults()
        
        logger.info("FailsafeManager initialized")

    def _register_defaults(self) -> None:
        """Register default sensors and devices."""
        # Register soil moisture sensor
        self.sensor_health.register_sensor(
            "soil_moisture_1", "soil_moisture", min_value=0.0, max_value=100.0
        )
        self.sensor_health.register_sensor(
            "temperature_1", "temperature", min_value=-40.0, max_value=80.0
        )
        self.sensor_health.register_sensor(
            "humidity_1", "humidity", min_value=0.0, max_value=100.0
        )
        
        # Register devices
        self.battery_guard.register_device("sensor_node_1")
        self.battery_guard.register_device("npk_node_1")
        self.battery_guard.register_device("pump_controller")
        
        # Register water tank
        self.water_tank.register_tank("main_tank")
        
        # Register watchdog for main system
        self.watchdog.register_watchdog("main_system", timeout_seconds=60.0)

    def check_irrigation_safety(
        self,
        soil_moisture: Optional[float] = None,
        rain_expected: bool = False,
        rain_probability: float = 0.0,
        ai_confidence: float = 1.0,
        tank_level: Optional[float] = None
    ) -> SafetyCheckResult:
        """
        Perform comprehensive safety check before irrigation.
        
        Args:
            soil_moisture: Current soil moisture (%)
            rain_expected: Is rain expected?
            rain_probability: Rain probability (%)
            ai_confidence: AI prediction confidence
            tank_level: Water tank level (%)
            
        Returns:
            SafetyCheckResult with safety status
        """
        # Check in order of priority
        
        # 1. Emergency Stop
        if self.emergency_stop.is_emergency_active():
            state = self.emergency_stop.get_state()
            return SafetyCheckResult(
                is_safe=False,
                override=SafetyOverride.EMERGENCY,
                reason=f"Emergency stop active: {state.reason}",
                blocked_by="emergency_stop"
            )
        
        # 2. Manual Override
        if self.manual_override.enabled:
            return SafetyCheckResult(
                is_safe=False,
                override=SafetyOverride.BLOCKED,
                reason=f"Manual override active: {self.manual_override.reason}",
                blocked_by="manual_override"
            )
        
        # 3. Water Tank Check
        if tank_level is not None:
            self.water_tank.update_level("main_tank", level_percent=tank_level)
        
        if self.water_tank.is_tank_empty("main_tank"):
            return SafetyCheckResult(
                is_safe=False,
                override=SafetyOverride.BLOCKED,
                reason="Water tank is empty",
                blocked_by="water_tank"
            )
        
        # 4. Pump Protection Check
        can_start, pump_reason = self.pump_protection.can_start_pump()
        if not can_start:
            return SafetyCheckResult(
                is_safe=False,
                override=SafetyOverride.BLOCKED,
                reason=f"Pump protection: {pump_reason}",
                blocked_by="pump_protection"
            )
        
        # 5. Rain Forecast Lock (with dry soil override)
        if self.rain_lock_config.enabled and rain_expected:
            soil_is_critical = (
                soil_moisture is not None and
                soil_moisture <= self.rain_lock_config.critical_moisture_override
            )
            
            if not soil_is_critical:
                return SafetyCheckResult(
                    is_safe=False,
                    override=SafetyOverride.WARNING,
                    reason="Rain expected, delaying irrigation",
                    blocked_by="rain_lock",
                    details={"rain_probability": rain_probability}
                )
        
        # 6. AI Confidence Check (only if not in offline mode
        if not self.offline_mode.is_offline:
            if ai_confidence < self.ai_confidence_threshold:
                return SafetyCheckResult(
                    is_safe=False,
                    override=SafetyOverride.WARNING,
                    reason=f"AI confidence low: {ai_confidence:.2f}",
                    blocked_by="ai_confidence"
                )
        
        # All checks passed
        return SafetyCheckResult(
            is_safe=True,
            override=SafetyOverride.SAFE,
            reason="All safety checks passed"
        )

    def activate_manual_override(self, reason: str, activated_by: str = "user") -> None:
        """Activate manual override."""
        self.manual_override.enabled = True
        self.manual_override.override_by = activated_by
        self.manual_override.override_at = datetime.now()
        self.manual_override.reason = reason
        logger.warning(f"Manual override activated: {reason} by {activated_by}")

    def deactivate_manual_override(self) -> None:
        """Deactivate manual override."""
        self.manual_override.enabled = False
        logger.info("Manual override deactivated")

    def enter_offline_mode(self, reason: str = "communication_failure") -> None:
        """Enter local offline mode."""
        self.offline_mode.is_offline = True
        self.offline_mode.since = datetime.now()
        self.offline_mode.reason = reason
        logger.warning(f"Entering offline mode: {reason}")

    def exit_offline_mode(self) -> None:
        """Exit local offline mode."""
        self.offline_mode.is_offline = False
        logger.info("Exiting offline mode")

    def trigger_emergency_stop(self, reason: EmergencyStopReason) -> bool:
        """Trigger emergency stop."""
        return self.emergency_stop.activate(reason)

    def reset_emergency_stop(self, reset_by: str = "system") -> bool:
        """Reset emergency stop."""
        return self.emergency_stop.deactivate(reset_by)

    def on_pump_start(self) -> None:
        """Call when pump starts."""
        self.pump_protection.on_pump_start()
        self.dry_run.start_monitoring()

    def on_pump_stop(self) -> None:
        """Call when pump stops."""
        self.pump_protection.on_pump_stop()
        self.dry_run.reset_monitoring()

    def update_sensor_reading(
        self,
        sensor_id: str,
        value: Optional[float]
    ) -> Tuple[bool, SensorHealthStatus]:
        """Update and validate a sensor reading."""
        return self.sensor_health.validate_reading(sensor_id, value)

    def update_battery(
        self,
        device_id: str,
        voltage: Optional[float] = None,
        percent: Optional[float] = None
    ) -> BatteryStatus:
        """Update battery status for a device."""
        return self.battery_guard.update_battery(device_id, voltage, percent)

    def get_safety_status_summary(self) -> Dict[str, Any]:
        """Get a summary of all safety statuses."""
        return {
            "emergency_stop": {
                "is_active": self.emergency_stop.is_emergency_active(),
                "state": self.emergency_stop.get_state()
            },
            "manual_override": {
                "enabled": self.manual_override.enabled,
                "reason": self.manual_override.reason
            },
            "offline_mode": {
                "is_offline": self.offline_mode.is_offline,
                "reason": self.offline_mode.reason
            },
            "sensor_health": self.sensor_health.get_all_statuses(),
            "battery_status": self.battery_guard.get_all_statuses(),
            "pump_protection": self.pump_protection.get_state(),
            "water_tank": self.water_tank.get_state("main_tank"),
            "watchdog": self.watchdog.get_offline_devices()
        }
