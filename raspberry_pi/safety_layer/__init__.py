"""Safety Layer for AI Smart Irrigation Digital Twin.

This module provides comprehensive safety features:
- Emergency Stop
- Dry Run Protection
- Pump Runtime Protection
- Sensor Health Monitoring
- Battery Guard
- Water Tank Guard
- Watchdog and Recovery
- Rain Forecast Lock
- Manual Override
- Offline Mode
"""

from .failsafe import (
    FailsafeManager,
    SafetyCheckResult,
    SafetyOverride,
    RainLockConfig,
    ManualOverrideState,
    OfflineModeState
)
from .emergency_stop import (
    EmergencyStopManager,
    EmergencyStopState,
    EmergencyStopReason
)
from .dry_run import (
    DryRunProtector,
    DryRunState,
    DryRunStatus
)
from .pump_protection import (
    PumpProtector,
    PumpProtectionState,
    PumpProtectionStatus
)
from .sensor_health import (
    SensorHealthMonitor,
    SensorHealthState,
    SensorHealthStatus
)
from .battery_guard import (
    BatteryGuard,
    BatteryState,
    BatteryStatus
)
from .water_tank_guard import (
    WaterTankGuard,
    WaterTankState,
    TankStatus
)
from .watchdog import (
    WatchdogManager,
    WatchdogEntry,
    DeviceTimeoutEntry,
    WatchdogStatus,
    RecoveryAction
)

__all__ = [
    "FailsafeManager",
    "SafetyCheckResult",
    "SafetyOverride",
    "RainLockConfig",
    "ManualOverrideState",
    "OfflineModeState",
    "EmergencyStopManager",
    "EmergencyStopState",
    "EmergencyStopReason",
    "DryRunProtector",
    "DryRunState",
    "DryRunStatus",
    "PumpProtector",
    "PumpProtectionState",
    "PumpProtectionStatus",
    "SensorHealthMonitor",
    "SensorHealthState",
    "SensorHealthStatus",
    "BatteryGuard",
    "BatteryState",
    "BatteryStatus",
    "WaterTankGuard",
    "WaterTankState",
    "TankStatus",
    "WatchdogManager",
    "WatchdogEntry",
    "DeviceTimeoutEntry",
    "WatchdogStatus",
    "RecoveryAction",
]
