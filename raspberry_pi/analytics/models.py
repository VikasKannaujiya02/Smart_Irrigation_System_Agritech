"""Data models for the Analytics module."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime, date
from enum import Enum, auto


class SensorHealthStatus(Enum):
    HEALTHY = auto()
    WARNING = auto()
    FAULTY = auto()
    OFFLINE = auto()


class CropGrowthStage(Enum):
    SEEDLING = auto()
    VEGETATIVE = auto()
    FLOWERING = auto()
    FRUITING = auto()
    RIPENING = auto()
    HARVEST = auto()


@dataclass
class WaterConsumptionRecord:
    id: str
    timestamp: datetime
    volume_liters: float
    source: str  # "irrigation", "rain"
    field_id: str
    pump_id: Optional[str] = None


@dataclass
class PredictionRecord:
    id: str
    timestamp: datetime
    prediction_type: str  # "soil_moisture", "irrigation_need"
    predicted_value: float
    actual_value: Optional[float] = None
    confidence: float = 1.0
    horizon_hours: int = 24


@dataclass
class PumpRuntimeRecord:
    id: str
    pump_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_runtime_seconds: int = 0
    volume_pumped_liters: float = 0.0
    power_consumed_w: float = 0.0


@dataclass
class BatteryRecord:
    id: str
    device_id: str
    timestamp: datetime
    voltage: Optional[float] = None
    percentage: Optional[float] = None
    temperature_c: Optional[float] = None


@dataclass
class SensorHealthRecord:
    id: str
    sensor_id: str
    timestamp: datetime
    status: SensorHealthStatus
    value: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CropRecord:
    id: str
    crop_type: str
    planting_date: date
    harvest_date: Optional[date] = None
    growth_stage: CropGrowthStage = CropGrowthStage.SEEDLING
    expected_yield_kg: Optional[float] = None
    actual_yield_kg: Optional[float] = None


@dataclass
class WeatherImpactRecord:
    id: str
    date: date
    temperature_c_avg: float
    humidity_pct_avg: float
    rainfall_mm: float
    wind_speed_mps_avg: float
    solar_radiation_wm2_avg: float
    eto_mm: float  # Reference Evapotranspiration


@dataclass
class AnalyticsReport:
    report_id: str
    report_type: str  # "daily", "weekly", "monthly"
    start_date: date
    end_date: date
    generated_at: datetime
    data: Dict[str, Any] = field(default_factory=dict)
