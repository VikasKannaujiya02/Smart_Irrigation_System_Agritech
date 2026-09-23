"""Pydantic schemas for Dashboard API."""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# Sensor schemas
class SensorReading(BaseModel):
    sensor_id: str = Field(..., description="Unique sensor identifier")
    value: Optional[float] = Field(None, description="Sensor reading value")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    timestamp: datetime = Field(default_factory=datetime.now, description="Reading timestamp")
    status: str = Field("healthy", description="Sensor health status (healthy, warning, faulty)")


class SensorDataResponse(BaseModel):
    sensors: List[SensorReading]
    total_count: int
    last_updated: datetime


# Pump schemas
class PumpStatus(BaseModel):
    pump_id: str = "main_pump"
    state: str = "off"
    current_flow_rate: Optional[float] = None
    pressure: Optional[float] = None
    power_kw: Optional[float] = None
    temperature_c: Optional[float] = None
    runtime_seconds: int = 0
    total_runtime_today: int = 0
    cycles_today: int = 0
    last_start: Optional[datetime] = None
    last_stop: Optional[datetime] = None


class PumpControlRequest(BaseModel):
    action: str = Field(..., description="Action: 'on', 'off', or 'emergency_stop'")


# Weather schemas
class WeatherCurrent(BaseModel):
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    wind_speed_mps: Optional[float] = None
    solar_radiation_w_m2: Optional[float] = None
    rainfall_mm: Optional[float] = None
    pressure_hpa: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    eto_mm_day: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class WeatherForecastItem(BaseModel):
    hours_ahead: int
    date: Optional[str] = None
    timestamp: Optional[datetime] = None
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    wind_speed_mps: Optional[float] = None
    rainfall_mm: Optional[float] = None
    rain_probability_pct: Optional[float] = None
    pressure_hpa: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    rain_expected: bool = False


class WeatherResponse(BaseModel):
    current: WeatherCurrent
    forecast: List[WeatherForecastItem]
    regional_wetness: Optional[Dict[str, Any]] = None


# AI Prediction schemas
class AIPrediction(BaseModel):
    prediction_id: str
    timestamp: datetime
    prediction_type: str
    confidence: float
    data: Dict[str, Any]
    prediction_horizon_hours: int


class AIPredictionResponse(BaseModel):
    latest: Optional[AIPrediction] = None
    history: List[AIPrediction] = []


# Water Saving schemas
class WaterSavingStats(BaseModel):
    current_month_saved_liters: float
    current_month_used_liters: float
    current_month_savings_pct: float
    total_saved_liters: float
    total_used_liters: float
    daily_avg_savings_pct: float
    last_updated: Optional[datetime] = None


# Alerts schemas
class Alert(BaseModel):
    alert_id: str
    timestamp: datetime
    level: str
    type: str
    message: str
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class AlertsResponse(BaseModel):
    active: List[Alert]
    resolved: List[Alert]
    total_active: int
    total_resolved: int


# NPK schemas
class NPKReading(BaseModel):
    sensor_id: str = "npk_1"
    nitrogen_mg_kg: Optional[float] = None
    phosphorus_mg_kg: Optional[float] = None
    potassium_mg_kg: Optional[float] = None
    ph: Optional[float] = None
    ec: Optional[float] = None
    soil_temp_c: Optional[float] = None
    soil_moisture_percent: Optional[float] = None
    battery_voltage: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    status: str = "healthy"


class NPKResponse(BaseModel):
    latest: Optional[NPKReading] = None
    history: List[NPKReading] = []


# Crop recommendation schemas
class CropRecommendationCrop(BaseModel):
    crop: str
    probability: float
    water_requirement_mm_day: Optional[float] = None
    weather_adjusted_water_mm_day: Optional[float] = None
    ideal_profile: Dict[str, Any] = {}


class CropRecommendationResponse(BaseModel):
    status: str
    message: str
    input_features: Dict[str, Optional[float]]
    top_crops: List[CropRecommendationCrop] = []
    selected_crop: Optional[CropRecommendationCrop] = None
    agronomic_context: Dict[str, Any] = {}


# Analytics schemas
class AnalyticsSummary(BaseModel):
    period_start: datetime
    period_end: datetime
    total_irrigation_events: int
    total_water_used_liters: float
    avg_soil_moisture_pct: float
    crop_water_stress_days: int
    ai_predictions_made: int
    alerts_generated: int


class WaterConsumptionAnalytics(BaseModel):
    total_irrigation_liters: float
    total_rain_liters: float
    daily_usage: Dict[str, float]
    avg_daily_liters: float
    max_daily_liters: float


class WaterSavingsAnalytics(BaseModel):
    actual_usage_liters: float
    baseline_usage_liters: float
    total_savings_liters: float
    savings_percentage: float


class PredictionAccuracyAnalytics(BaseModel):
    total_predictions: int
    mae: float
    rmse: float
    avg_confidence: float


class PumpStatistics(BaseModel):
    total_runtime_seconds: int
    total_runtime_hours: float
    total_volume_liters: float
    avg_runtime_seconds: float
    number_of_cycles: int


class BatteryStatistics(BaseModel):
    overall_avg_percentage: Optional[float]
    devices: Dict[str, Dict[str, float]]


class SensorHealthAnalytics(BaseModel):
    overall_status: Dict[str, int]
    sensor_details: Dict[str, Dict[str, int]]


class CropPerformance(BaseModel):
    crop_type: str
    days_since_planting: int
    growth_stage: str
    expected_yield_kg: Optional[float] = None
    actual_yield_kg: Optional[float] = None


class WeatherImpact(BaseModel):
    avg_temperature: float
    avg_humidity: float
    total_rainfall_mm: float
    avg_eto_mm: float
    days_with_rain: int


class FullAnalyticsResponse(BaseModel):
    period: Dict[str, str]
    water_consumption: WaterConsumptionAnalytics
    water_savings: WaterSavingsAnalytics
    prediction_accuracy: PredictionAccuracyAnalytics
    pump_statistics: PumpStatistics
    battery_statistics: BatteryStatistics
    sensor_health: SensorHealthAnalytics
    crop_performance: CropPerformance
    weather_impact: WeatherImpact


class TrendAnalysisResponse(BaseModel):
    water_consumption_trend: Dict[str, Any]
    battery_trend: Dict[str, Any]
    sensor_health_trend: Dict[str, Any]
    rainfall_impact_analysis: Dict[str, Any]


# Digital Twin schemas
class DigitalTwinState(BaseModel):
    timestamp: datetime
    soil_moisture_vwc: float
    soil_moisture_pct: float
    pump_state: str
    crop_stage: str
    eto_mm_day: float
    field_area_m2: float


class DigitalTwinSimulationRequest(BaseModel):
    duration_hours: int = 24
    scenario: Optional[str] = None
    initial_state: Optional[Dict[str, Any]] = None


# Configuration schemas
class SystemConfig(BaseModel):
    irrigation_mode: str = "ai"
    emergency_moisture_threshold: float = 15.0
    ai_confidence_threshold: float = 0.7
    max_pump_runtime_seconds: int = 3600
    rain_delay_hours: int = 24
    weather_latitude: float = 25.3176
    weather_longitude: float = 82.9739


# Health schemas
class HealthStatus(BaseModel):
    status: str = "healthy"
    services: Dict[str, str]
    uptime_seconds: float
    version: str


# Logs schemas
class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    module: str
    message: str
    extra: Optional[Dict[str, Any]] = None


class LogsResponse(BaseModel):
    logs: List[LogEntry]
    total_count: int
    has_more: bool


# ─── Crop Lifecycle schemas ────────────────────────────────────────────────────

class GrowthStageInfo(BaseModel):
    stage_name: str
    stage_index: int
    stage_description: str = ""
    stage_fraction: float = 0.0
    detection_method: str = "day_fraction"
    season_days: int
    days_since_planting: int
    accumulated_gdd: Optional[float] = None
    source: str = "phenology_engine / calculated"
    source_note: str = ""


class CropCycleResponse(BaseModel):
    id: int
    crop_type: str
    ai_recommended_crop: Optional[str] = None
    farmer_selected_crop: Optional[str] = None
    planting_date: Optional[str] = None
    field_id: Optional[str] = None
    field_area_m2: Optional[float] = None
    lifecycle_status: str
    expected_yield_kg: Optional[float] = None
    actual_yield_kg: Optional[float] = None
    harvest_date: Optional[str] = None
    harvest_notes: Optional[str] = None
    accumulated_gdd: Optional[float] = None
    notes: Optional[str] = None
    created_at: str
    updated_at: str
    # Calculated fields
    days_since_planting: Optional[int] = None
    days_since_planting_source: str = "unavailable — planting_date not set"
    growth_stage: str = "Not Started"
    growth_stage_info: Optional[GrowthStageInfo] = None
    # Provenance labels
    crop_type_source: str = "manual_input"
    planting_date_source: str = "not_set"
    expected_yield_display: str = "Not Available — awaiting real data"
    expected_yield_source: str = "not_available"
    actual_yield_display: str = "Not Available — awaiting harvest entry"
    actual_yield_source: str = "not_available"


class CreateCropCycleRequest(BaseModel):
    crop_type: str
    ai_recommended_crop: Optional[str] = None
    farmer_selected_crop: Optional[str] = None
    planting_date: Optional[str] = None
    field_id: Optional[str] = None
    field_area_m2: Optional[float] = None
    notes: Optional[str] = None


class ConfirmCropRequest(BaseModel):
    farmer_selected_crop: str
    planting_date: Optional[str] = None


class SetPlantingDateRequest(BaseModel):
    planting_date: str  # ISO format YYYY-MM-DD


class UpdateLifecycleStatusRequest(BaseModel):
    lifecycle_status: str


class RecordHarvestRequest(BaseModel):
    harvest_date: str          # ISO format YYYY-MM-DD
    actual_yield_kg: float     # SOURCE = harvest_measurement / farmer_input
    notes: Optional[str] = None


class YieldComparisonResponse(BaseModel):
    expected_yield_kg: Optional[float] = None
    actual_yield_kg: Optional[float] = None
    expected_yield_source: str
    actual_yield_source: str
    yield_difference_kg: Optional[float] = None
    yield_achievement_pct: Optional[float] = None
    prediction_error_pct: Optional[float] = None
    comparison_available: bool = False
    summary: str
    source: str = "calculated"


class WaterProductivityResponse(BaseModel):
    actual_yield_kg: Optional[float] = None
    water_used_liters: Optional[float] = None
    actual_yield_source: str
    water_used_source: str
    water_productivity_kg_per_liter: Optional[float] = None
    water_cost_liters_per_kg: Optional[float] = None
    calculation_available: bool = False
    unit_note: str = "Water: litres (L) | Yield: kilograms (kg)"
    summary: str


class CropLifecycleHistoryResponse(BaseModel):
    cycles: List[CropCycleResponse]
    total_count: int


class CropGrowthStageResponse(BaseModel):
    crop_cycle_id: int
    crop_type: str
    planting_date: Optional[str] = None
    days_since_planting: Optional[int] = None
    growth_stage: str
    growth_stage_info: Optional[GrowthStageInfo] = None
    lifecycle_status: str
    accumulated_gdd: Optional[float] = None
    source: str = "phenology_engine / calculated"


class PhenologyStageDef(BaseModel):
    index: int
    name: str
    day_fraction_start: float
    day_fraction_end: float
    day_start: int
    day_end: int
    description: str = ""


class CropPhenologyResponse(BaseModel):
    crop_name: str
    growing_season_days: int
    base_temperature_c: float
    stages: List[PhenologyStageDef]
    notes: str = ""


# ─── Plant Disease Detection schemas ──────────────────────────────────────────

class DiseasePrediction(BaseModel):
    scan_id: str
    created_at: datetime
    crop: Optional[str] = None
    disease_class: Optional[str] = None
    is_healthy: Optional[bool] = None
    confidence: Optional[float] = None
    alternatives: List[Dict[str, Any]] = []
    model_version: Optional[str] = None
    image_url: Optional[str] = None
    inference_available: bool = True


class DiseaseHistoryResponse(BaseModel):
    records: List[DiseasePrediction]
    total_count: int


class DiseaseStatusResponse(BaseModel):
    available: bool
    message: str
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    supported_crops: List[str] = []


# ─── Pest Detection schemas ────────────────────────────────────────────────────

class PestPrediction(BaseModel):
    scan_id: str
    created_at: datetime
    pest_class: Optional[str] = None
    confidence: Optional[float] = None
    detection_count: Optional[int] = None
    bounding_boxes: List[Dict[str, Any]] = []
    alternatives: List[Dict[str, Any]] = []
    model_version: Optional[str] = None
    image_url: Optional[str] = None
    inference_available: bool = True


class PestHistoryResponse(BaseModel):
    records: List[PestPrediction]
    total_count: int


class PestStatusResponse(BaseModel):
    available: bool
    message: str
    model_name: Optional[str] = None
    model_version: Optional[str] = None
