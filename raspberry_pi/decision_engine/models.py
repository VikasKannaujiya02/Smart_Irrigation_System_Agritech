"""Core data models and enums for Decision Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional
from datetime import datetime


class IrrigationMode(Enum):
    """Irrigation control mode."""
    AI = auto()
    RULES = auto()
    MANUAL = auto()
    EMERGENCY = auto()


class PumpCommand(Enum):
    """Command to send to pump controller."""
    ON = auto()
    OFF = auto()
    NO_CHANGE = auto()


class IrrigationDecision(Enum):
    """Overall irrigation decision."""
    IRRIGATE_NOW = auto()
    IRRIGATE_LATER = auto()
    DO_NOT_IRRIGATE = auto()
    EMERGENCY_IRRIGATE = auto()


class SensorStatus(Enum):
    """Sensor health status."""
    OK = auto()
    WARNING = auto()
    FAULTY = auto()


@dataclass
class SensorData:
    """Sensor data from field nodes."""
    soil_moisture_percent: Optional[float] = None
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    battery_voltage: Optional[float] = None
    battery_percent: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    sensor_status: SensorStatus = SensorStatus.OK


@dataclass
class NPKData:
    """NPK sensor data."""
    nitrogen_mg_kg: Optional[float] = None
    phosphorus_mg_kg: Optional[float] = None
    potassium_mg_kg: Optional[float] = None
    ph: Optional[float] = None
    electrical_conductivity: Optional[float] = None
    soil_temperature_c: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    sensor_status: SensorStatus = SensorStatus.OK


@dataclass
class WeatherData:
    """Weather data from API or history."""
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    rainfall_mm: Optional[float] = None
    wind_speed_mps: Optional[float] = None
    pressure_hpa: Optional[float] = None
    rain_expected_24h: bool = False
    rain_expected_72h: bool = False
    forecast_horizon_hours: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AIPrediction:
    """AI model predictions."""
    soil_moisture_predicted: Optional[float] = None
    irrigation_need_score: Optional[float] = None
    water_requirement_liters: Optional[float] = None
    confidence: float = 1.0
    used_fallback: bool = False
    prediction_horizon_hours: int = 24
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TankStatus:
    """Water tank status."""
    level_percent: Optional[float] = None
    is_empty: bool = False
    is_low: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PumpStatus:
    """Pump controller status."""
    is_on: bool = False
    relay_state: str = "OFF"
    feedback_state: str = "STOPPED"
    runtime_seconds: int = 0
    is_fault: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class CropConfig:
    """Crop-specific configuration."""
    name: str = "default_crop"
    min_soil_moisture: float = 30.0
    ideal_soil_moisture: float = 50.0
    max_soil_moisture: float = 80.0
    emergency_moisture_threshold: float = 15.0
    preferred_irrigation_time_hours: List[int] = field(default_factory=lambda: [6, 18])


@dataclass
class SystemConfig:
    """System-wide configuration for Decision Engine."""
    emergency_moisture_threshold: float = 15.0
    ai_confidence_threshold: float = 0.7
    low_battery_threshold_percent: float = 20.0
    tank_empty_threshold_percent: float = 5.0
    tank_low_threshold_percent: float = 20.0
    max_pump_runtime_seconds: int = 3600
    rain_delay_hours: int = 24
    irrigation_mode: IrrigationMode = IrrigationMode.AI


@dataclass
class RuleResult:
    """Result from a single rule engine."""
    engine_name: str
    decision: IrrigationDecision
    confidence: float
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IrrigationAction:
    """Final irrigation action to execute."""
    pump_command: PumpCommand
    decision: IrrigationDecision
    mode: IrrigationMode
    confidence: float
    reasons: List[str] = field(default_factory=list)
    duration_seconds: Optional[int] = None
    water_volume_liters: Optional[float] = None
    scheduled_time: Optional[datetime] = None
    timestamp: datetime = field(default_factory=datetime.now)
