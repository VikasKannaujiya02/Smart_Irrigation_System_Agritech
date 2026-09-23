"""FastAPI Dashboard Backend for Irrigation System."""

import logging
import json
import os
import uuid
import shutil
import threading
import torch  # IMPORT EARLY TO PREVENT ARM OPENMP CRASH (free(): invalid pointer)
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from .schemas import (
    SensorReading, SensorDataResponse,
    PumpStatus, PumpControlRequest,
    WeatherCurrent, WeatherForecastItem, WeatherResponse,
    AIPrediction, AIPredictionResponse,
    WaterSavingStats,
    Alert, AlertsResponse,
    NPKReading, NPKResponse,
    CropRecommendationResponse,
    AnalyticsSummary,
    WaterConsumptionAnalytics, WaterSavingsAnalytics,
    PredictionAccuracyAnalytics, PumpStatistics, BatteryStatistics,
    SensorHealthAnalytics, CropPerformance, WeatherImpact,
    FullAnalyticsResponse, TrendAnalysisResponse,
    DigitalTwinState, DigitalTwinSimulationRequest,
    SystemConfig,
    LogEntry, LogsResponse,
    # Crop lifecycle schemas
    CropCycleResponse, CreateCropCycleRequest, ConfirmCropRequest,
    SetPlantingDateRequest, UpdateLifecycleStatusRequest, RecordHarvestRequest,
    YieldComparisonResponse, WaterProductivityResponse,
    CropLifecycleHistoryResponse, CropGrowthStageResponse,
    CropPhenologyResponse, PhenologyStageDef, GrowthStageInfo,
    # Disease / Pest schemas
    DiseasePrediction, DiseaseHistoryResponse, DiseaseStatusResponse,
    PestPrediction, PestHistoryResponse, PestStatusResponse,
)


from ..analytics import AnalyticsEngine, CSVExporter, PDFExporter, MonthlyReportGenerator
from ..analytics.trends import TrendAnalyzer
# Legacy ai_engine imports removed
from ..backup import BackupManager
from ..configuration_manager import config_manager
from ..weather_api import WeatherService
from ..crop_recommendation import CropRecommendationService
from ..crop_lifecycle import CropLifecycleService, PhenologyEngine, YieldCalculator, WaterProductivityCalculator
from ..system_orchestrator import SystemOrchestrator
from ..safety_layer import EmergencyStopReason
from ..database.query_builder import SelectQuery
from ..decision_engine.models import IrrigationAction, IrrigationDecision, IrrigationMode, PumpCommand

# Configure logging
logger = logging.getLogger("dashboard")

# Initialize System Orchestrator (connects all modules)
orchestrator = SystemOrchestrator()

# Initialize components
analytics_engine = AnalyticsEngine(orchestrator.repository_registry)
trend_analyzer = TrendAnalyzer(analytics_engine)
report_generator = MonthlyReportGenerator(analytics_engine)
# Legacy managers removed
backup_manager = BackupManager()
crop_recommendation_service = CropRecommendationService()
receiver_thread: threading.Thread | None = None

# Crop lifecycle services (lazy-initialised after orchestrator has its DB pool)
_crop_lifecycle_service: CropLifecycleService | None = None
_phenology_engine = PhenologyEngine()
_yield_calculator = YieldCalculator()
_water_productivity_calc = WaterProductivityCalculator()


def _get_lifecycle_service() -> CropLifecycleService:
    """Return a singleton CropLifecycleService using the orchestrator DB pool."""
    global _crop_lifecycle_service
    if _crop_lifecycle_service is None:
        _crop_lifecycle_service = CropLifecycleService(
            orchestrator.database_manager.database.connection_pool,
            phenology_engine=_phenology_engine,
        )
    return _crop_lifecycle_service



@asynccontextmanager
async def lifespan(app: FastAPI):
    global receiver_thread
    logger.info("Starting Dashboard API...")
    if os.getenv("DASHBOARD_START_RECEIVER", "0").strip().lower() in {"1", "true", "yes"}:
        receiver_thread = threading.Thread(
            target=orchestrator.run,
            name="dashboard-orchestrator-receiver",
            daemon=True,
        )
        receiver_thread.start()
        logger.info("Dashboard-owned orchestrator receiver started")
    yield
    logger.info("Shutting down Dashboard API...")
    orchestrator.shutdown()


# Initialize app
app = FastAPI(
    title="AI Smart Irrigation Digital Twin - Dashboard API",
    description="REST API for the Smart Irrigation Dashboard",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Root Endpoint ---
@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "AI Smart Irrigation Digital Twin Dashboard API",
        "version": "1.0.0",
        "docs": "/docs"
    }


# Health, OTA, Remote Config, Backup API Endpoints Removed as part of Legacy Cleanup
@app.get("/api/sensors", tags=["Sensors"], response_model=SensorDataResponse)
async def get_sensors(limit: int = 20):
    """Get all live sensor readings from database."""
    sensor_data = orchestrator.repository_registry.sensor_data.select(
        SelectQuery("SensorData").order_by("id DESC").limit(limit)
    )
    
    sensor_list = []
    for row in sensor_data:
        if row.get("soil_moisture_percent") is not None:
            sensor_list.append(SensorReading(
                sensor_id=f"soil_moisture_{row['device_id']}",
                value=row["soil_moisture_percent"],
                unit="%",
                timestamp=datetime.fromisoformat(row["recorded_at"]) if row["recorded_at"] else datetime.now(),
                status="healthy"
            ))
        temp_val = row.get("temperature_c")
        if temp_val == 0.0 or temp_val is None:
            wea = orchestrator.repository_registry.weather_history.select(SelectQuery("WeatherHistory").order_by("id DESC").limit(1))
            temp_val = wea[0].get("temperature_c") if wea and wea[0].get("temperature_c") is not None else 25.0
            
        if temp_val is not None:
            sensor_list.append(SensorReading(
                sensor_id=f"temp_{row['device_id']}",
                value=temp_val,
                unit="deg C",
                timestamp=datetime.fromisoformat(row["recorded_at"]) if row["recorded_at"] else datetime.now(),
                status="healthy"
            ))
        if row.get("humidity_percent") is not None:
            sensor_list.append(SensorReading(
                sensor_id=f"humidity_{row['device_id']}",
                value=row["humidity_percent"],
                unit="%",
                timestamp=datetime.fromisoformat(row["recorded_at"]) if row["recorded_at"] else datetime.now(),
                status="healthy"
            ))
        if row.get("battery_percent") is not None:
            sensor_list.append(SensorReading(
                sensor_id=f"battery_{row['device_id']}",
                value=row["battery_percent"],
                unit="%",
                timestamp=datetime.fromisoformat(row["recorded_at"]) if row["recorded_at"] else datetime.now(),
                status="healthy"
            ))
    
    return SensorDataResponse(
        sensors=sensor_list,
        total_count=len(sensor_list),
        last_updated=sensor_list[-1].timestamp if sensor_list else datetime.now()
    )


@app.get("/api/sensors/{sensor_id}", tags=["Sensors"], response_model=SensorReading)
async def get_sensor(sensor_id: str):
    """Get single sensor by ID."""
    sensors = await get_sensors()
    for sensor in sensors.sensors:
        if sensor.sensor_id == sensor_id:
            return sensor
    raise HTTPException(status_code=404, detail="Sensor not found")


# --- Live Pump API ---
@app.get("/api/pump", tags=["Pump"], response_model=PumpStatus)
async def get_pump_status():
    """Get current pump status from database."""
    pump_data = orchestrator.repository_registry.pump_status.select(
        SelectQuery("PumpStatus").order_by("id DESC").limit(1)
    )
    
    if pump_data:
        row = pump_data[0]
        manual_latch = getattr(orchestrator, "_manual_pump_latch", None)
        state = manual_latch.name.lower() if manual_latch is not None else row["relay_state"].lower()
        return PumpStatus(
            state=state,
            last_start=datetime.fromisoformat(row["recorded_at"]) if row["recorded_at"] else None,
            last_stop=None,
            runtime_seconds=row["runtime_seconds"],
            cycles_today=0,
            status="healthy"
        )
    
    return PumpStatus()


@app.post("/api/pump/control", tags=["Pump"], response_model=PumpStatus)
async def control_pump(request: PumpControlRequest):
    """Control the pump via decision engine and command executor."""
    action_name = request.action.lower()
    if action_name == "emergency_stop":
        orchestrator.failsafe_manager.trigger_emergency_stop(EmergencyStopReason.MANUAL)
        logger.critical("Pump emergency stop activated")
        return await get_pump_status()
    if action_name not in {"on", "off"}:
        raise HTTPException(status_code=400, detail="Action must be 'on', 'off', or 'emergency_stop'")

    action = IrrigationAction(
        pump_command=PumpCommand.ON if action_name == "on" else PumpCommand.OFF,
        decision=IrrigationDecision.IRRIGATE_NOW if action_name == "on" else IrrigationDecision.DO_NOT_IRRIGATE,
        mode=IrrigationMode.MANUAL,
        confidence=1.0,
        reasons=["manual_dashboard_request"],
    )
    result = orchestrator.command_executor.execute_pump_command(action)
    if not result.success:
        raise HTTPException(status_code=503, detail=result.message)
    if action_name == "on":
        orchestrator.failsafe_manager.activate_manual_override(
            reason="dashboard_manual_pump_on",
            activated_by="dashboard",
        )
    else:
        orchestrator.failsafe_manager.deactivate_manual_override()
    orchestrator.set_manual_pump_latch(action.pump_command)
    return await get_pump_status()

# --- Weather API ---
@app.get("/api/weather", tags=["Weather"], response_model=WeatherResponse)
async def get_weather():
    """Get live current weather and a daily forecast from the configured provider."""
    live = _fetch_and_store_weather(days=7)
    weather_data = live["rows"]

    if not weather_data:
        weather_data = orchestrator.repository_registry.weather_history.select(
            SelectQuery("WeatherHistory").order_by("id DESC").limit(40)
        )

    current = _weather_current_from_point(live["current"])
    if current is None and weather_data:
        current = _weather_current_from_row(weather_data[0])

    return WeatherResponse(
        current=current or WeatherCurrent(),
        forecast=_build_daily_forecast_items(live["daily"], weather_data),
        regional_wetness=orchestrator.get_regional_wetness_prediction()
    )


def _fetch_and_store_weather(days: int = 7):
    """Fetch weather through the existing provider and persist it to WeatherHistory."""
    try:
        service = WeatherService.from_config()
        current = service.get_current_weather(use_cache=True)
        daily = service.get_daily_forecast(days=days) or []
        forecast = service.get_forecast(use_cache=True, hours=days * 24) or []
    except Exception as exc:
        logger.warning("Weather provider unavailable: %s", exc)
        return {"current": None, "daily": [], "rows": []}

    rows = []
    weather_points = [point for point in [current, *forecast] if point is not None]
    for index, point in enumerate(weather_points[:40]):
        values = {
            "source": config_manager.get_config().weather.provider,
            "recorded_at": point.timestamp.isoformat(),
            "temperature_c": point.temperature,
            "humidity_percent": point.humidity,
            "rainfall_mm": point.rain_volume or 0.0,
            "wind_speed_mps": point.wind_speed,
            "pressure_hpa": point.pressure_hpa,
            "forecast_horizon_hours": index,
            "raw_json": json.dumps({
                "rain_probability_pct": point.rain_probability,
                "cloud_cover_pct": point.cloud_cover,
            }),
        }
        try:
            orchestrator.repository_registry.weather_history.insert(values)
            # orchestrator.csv_exporter.append_weather(values) removed
            rows.append(values)
        except Exception as exc:
            logger.warning("Weather history store skipped: %s", exc)
    return {"current": current, "daily": daily, "rows": rows}


def _weather_current_from_point(point):
    if point is None:
        return None
    return WeatherCurrent(
        temperature_c=point.temperature,
        humidity_pct=point.humidity,
        wind_speed_mps=point.wind_speed,
        rainfall_mm=point.rain_volume,
        pressure_hpa=point.pressure_hpa,
        cloud_cover_pct=point.cloud_cover,
        timestamp=point.timestamp,
    )


def _weather_current_from_row(row):
    raw_json = {}
    if row.get("raw_json"):
        try:
            raw_json = json.loads(row["raw_json"])
        except Exception:
            raw_json = {}
            
    pressure = row.get("pressure_hpa")
    cloud = raw_json.get("cloud_cover_pct")
    
    return WeatherCurrent(
        temperature_c=row.get("temperature_c"),
        humidity_pct=row.get("humidity_percent"),
        wind_speed_mps=row.get("wind_speed_mps"),
        rainfall_mm=row.get("rainfall_mm"),
        pressure_hpa=pressure,
        cloud_cover_pct=cloud,
        timestamp=datetime.fromisoformat(row["recorded_at"]) if row.get("recorded_at") else datetime.now(),
    )


def _build_daily_forecast_items(daily_points, weather_rows):
    if daily_points:
        return [
            WeatherForecastItem(
                hours_ahead=(index + 1) * 24,
                date=point.timestamp.date().isoformat(),
                timestamp=point.timestamp,
                temperature_c=point.temperature,
                humidity_pct=point.humidity,
                wind_speed_mps=point.wind_speed,
                rainfall_mm=point.rain_volume,
                rain_probability_pct=point.rain_probability,
                pressure_hpa=point.pressure_hpa,
                cloud_cover_pct=point.cloud_cover,
                rain_expected=((point.rain_volume or 0.0) > 0) or ((point.rain_probability or 0.0) >= 50.0),
            )
            for index, point in enumerate(daily_points[:7])
        ]

    by_day = {}
    sorted_rows = sorted(
        [row for row in weather_rows if row.get("recorded_at")],
        key=lambda row: row["recorded_at"],
    )
    for row in sorted_rows:
        if not row.get("recorded_at"):
            continue
        day = datetime.fromisoformat(row["recorded_at"]).date().isoformat()
        bucket = by_day.setdefault(day, [])
        bucket.append(row)

    forecast_items = []
    for index, (day, rows) in enumerate(list(by_day.items())[:7]):
        forecast_items.append(
            WeatherForecastItem(
                hours_ahead=(index + 1) * 24,
                date=day,
                timestamp=datetime.fromisoformat(rows[0]["recorded_at"]) if rows[0].get("recorded_at") else None,
                temperature_c=_avg(rows, "temperature_c"),
                humidity_pct=_avg(rows, "humidity_percent"),
                wind_speed_mps=_avg(rows, "wind_speed_mps"),
                rainfall_mm=sum(float(row.get("rainfall_mm") or 0.0) for row in rows),
                pressure_hpa=_avg(rows, "pressure_hpa"),
                rain_expected=any((row.get("rainfall_mm") or 0.0) > 0 for row in rows),
            )
        )
    return forecast_items


def _avg(rows, key):
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    if not values:
        return None
    return sum(values) / len(values)


# --- Crop Recommendation API ---
@app.get("/api/crop-recommendation", tags=["Crop Recommendation"], response_model=CropRecommendationResponse)
async def get_crop_recommendation():
    """Recommend crops from live NPK data using the trained crop classifier."""
    npk_rows = orchestrator.repository_registry.npk_data.select(
        SelectQuery("NPKData").order_by("id DESC").limit(1)
    )
    weather_context = _latest_weather_context()
    result = crop_recommendation_service.recommend(
        npk_rows[0] if npk_rows else None,
        weather_context=weather_context,
        top_n=5,
    )
    return CropRecommendationResponse(
        status=result.status,
        message=result.message,
        input_features=result.input_features,
        top_crops=result.top_crops,
        selected_crop=result.selected_crop,
        agronomic_context=result.agronomic_context,
    )


def _latest_weather_context():
    rows = orchestrator.repository_registry.weather_history.select(
        SelectQuery("WeatherHistory").order_by("id DESC").limit(40)
    )
    if not rows:
        return {
            "current_temperature_c": None,
            "current_humidity_pct": None,
            "forecast_rainfall_7d_mm": None,
            "source": "no_live_weather",
        }
    latest = rows[0]
    return {
        "current_temperature_c": latest.get("temperature_c"),
        "current_humidity_pct": latest.get("humidity_percent"),
        "current_rainfall_mm": latest.get("rainfall_mm"),
        "forecast_rainfall_7d_mm": round(sum(float(row.get("rainfall_mm") or 0.0) for row in rows), 2),
        "source": latest.get("source"),
        "timestamp": latest.get("recorded_at"),
    }


# --- AI Prediction API ---
@app.get("/api/ai/predictions", tags=["AI"], response_model=AIPredictionResponse)
async def get_ai_predictions(limit: int = 10):
    """Get AI predictions history from database."""
    prediction_data = orchestrator.repository_registry.prediction_history.select(
        SelectQuery("PredictionHistory").order_by("id DESC").limit(limit)
    )
    
    predictions = []
    for row in prediction_data:
        try:
            payload = json.loads(row.get("payload_json", "{}"))
        except Exception:
            payload = {}
        
        predictions.append(
            AIPrediction(
                prediction_id=str(row["id"]),
                timestamp=datetime.fromisoformat(row["created_at"]),
                prediction_type=row["prediction_type"],
                confidence=row["confidence"],
                data={
                    "predicted_moisture_pct": row["prediction_value"],
                    "irrigation_need_score": payload.get("irrigation_need_score"),
                    "water_requirement_liters": payload.get("water_requirement_liters")
                },
                prediction_horizon_hours=row["horizon_hours"] or 24
            )
        )
    
    return AIPredictionResponse(
        latest=predictions[0] if predictions else None,
        history=predictions
    )


@app.get("/api/ai/status", tags=["AI"])
async def get_ai_status():
    """Return full AI system status: model registry, feature window, current sensor state.

    This endpoint is used by the AI Prediction dashboard to show:
    - Which models are loaded and their version/horizon info
    - How many of the 30-reading feature window are filled
    - The current live sensor values being used as AI features
    - Whether a prediction can run right now (and why not, if not)
    - The last rule-based decision for comparison
    """
    # ── 1. Model registry status ─────────────────────────────────────────────
    registry = orchestrator.model_registry
    registered_models = []
    horizons = [1, 6, 12, 24, 168]
    for h in horizons:
        key = f"all_targets_horizon_{h}"
        versions = registry._versions.get(key, [])
        loaded = h in orchestrator.irrigation_predictor._hybrid_models
        active_v = next((v for v in versions if v.is_active), versions[-1] if versions else None)
        registered_models.append({
            "horizon_hours": h,
            "label": f"{h}h forecast",
            "registered": len(versions) > 0,
            "loaded": loaded,
            "model_type": active_v.model_type if active_v else None,
            "version": active_v.version if active_v else None,
            "metrics": active_v.metrics if active_v else {},
        })

    # ── 2. Feature window status ──────────────────────────────────────────────
    window_len = len(orchestrator._feature_window)
    window_max = orchestrator._feature_window.maxlen or 30
    window_pct = round((window_len / window_max) * 100, 1)
    can_predict = window_len >= window_max

    # ── 3. Current sensor state ───────────────────────────────────────────────
    sensor_state = dict(orchestrator._latest_sensor_state)

    # ── 4. Expected feature shape ─────────────────────────────────────────────
    expected_features = orchestrator._ai_expected_feature_count
    feature_order = orchestrator.AI_FEATURE_ORDER

    # ── 5. Last few window rows ───────────────────────────────────────────────
    recent_window = list(orchestrator._feature_window)[-5:] if orchestrator._feature_window else []

    # ── 6. Last AI prediction from DB ─────────────────────────────────────────
    last_pred_rows = orchestrator.repository_registry.prediction_history.select(
        SelectQuery("PredictionHistory").order_by("id DESC").limit(1)
    )
    last_prediction = None
    if last_pred_rows:
        row = last_pred_rows[0]
        try:
            payload = json.loads(row.get("payload_json", "{}"))
        except Exception:
            payload = {}
            
        last_prediction = {
            "timestamp": row.get("created_at"),
            "type": row.get("prediction_type"),
            "value": row.get("prediction_value"),
            "confidence": row.get("confidence"),
            "horizon_hours": row.get("horizon_hours"),
            "data": payload
        }

    # ── 7. Why can't predict message ──────────────────────────────────────────
    if can_predict:
        status_message = "Model can run — feature window is full."
        status_ok = True
    else:
        status_message = (
            f"Waiting for data: {window_len}/{window_max} readings collected. "
            f"Need {window_max - window_len} more sensor packets to fill the rolling window. "
            "Rule-Based mode is active in the meantime."
        )
        status_ok = False

    # ── 8. Weather Rain Gate status ───────────────────────────────────────────
    rain_forecast = None
    if getattr(orchestrator, "_weather_service", None) is not None:
        rec = orchestrator._weather_service.get_irrigation_recommendation()
        if rec:
            rain_forecast = {
                "expected_rainfall_mm": rec.rain_prediction.rain_volume if rec.rain_prediction else 0.0,
                "rain_probability": rec.rain_prediction.rain_probability if rec.rain_prediction else 0.0,
                "should_irrigate": rec.should_irrigate,
                "reason": rec.reason
            }

    return {
        "status_ok": status_ok,
        "status_message": status_message,
        "feature_window": {
            "filled": window_len,
            "required": window_max,
            "percent": window_pct,
            "can_predict": can_predict,
        },
        "current_sensor_state": sensor_state,
        "feature_order": feature_order,
        "expected_feature_count": expected_features,
        "recent_window_rows": recent_window,
        "registered_models": registered_models,
        "last_prediction": last_prediction,
        "fallback_mode": "rule_based",
        "irrigation_mode": orchestrator.system_config.irrigation_mode.name,
        "rain_forecast": rain_forecast,
        "timestamp": datetime.now().isoformat(),
    }


# --- Water Saving API ---
@app.get("/api/water-saving", tags=["Water Saving"], response_model=WaterSavingStats)
async def get_water_saving_stats():
    """Get water saving statistics from repository-backed analytics."""
    analytics_engine.refresh_from_repositories()
    if not analytics_engine.water_records:
        return WaterSavingStats(
            current_month_saved_liters=0.0,
            current_month_used_liters=0.0,
            current_month_savings_pct=0.0,
            total_saved_liters=0.0,
            total_used_liters=0.0,
            daily_avg_savings_pct=0.0,
            last_updated=datetime.now(),
        )
    summary = analytics_engine.get_full_analytics_summary()
    water_consumption = summary.get("water_consumption", {})
    water_savings = summary.get("water_savings", {})

    water_used = float(water_consumption.get("total_irrigation_liters", 0.0) or 0.0)
    water_saved = float(water_savings.get("total_savings_liters", 0.0) or 0.0)
    total_used = water_used
    total_saved = water_saved
    savings_pct = float(water_savings.get("savings_percentage", 0.0) or 0.0)

    return WaterSavingStats(
        current_month_saved_liters=round(water_saved, 2),
        current_month_used_liters=round(water_used, 2),
        current_month_savings_pct=round(savings_pct, 2),
        total_saved_liters=round(total_saved, 2),
        total_used_liters=round(total_used, 2),
        daily_avg_savings_pct=round(savings_pct, 2),
        last_updated=datetime.now()
    )


# --- Alerts API ---
@app.get("/api/alerts", tags=["Alerts"], response_model=AlertsResponse)
async def get_alerts(limit: int = 50):
    """Get all alerts from database."""
    alert_data = orchestrator.repository_registry.alerts.select(
        SelectQuery("Alerts").order_by("id DESC").limit(limit)
    )
    
    alerts = []
    for row in alert_data:
        alerts.append(
            Alert(
                alert_id=str(row["id"]),
                timestamp=datetime.fromisoformat(row["created_at"]),
                level=row["severity"].lower(),
                type=row["alert_type"],
                message=row["message"],
                resolved=row["status"] == "RESOLVED",
                resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None
            )
        )
    
    active = [a for a in alerts if not a.resolved]
    resolved = [a for a in alerts if a.resolved]
    
    return AlertsResponse(
        active=active,
        resolved=resolved[-20:],
        total_active=len(active),
        total_resolved=len(resolved)
    )


@app.put("/api/alerts/{alert_id}/resolve", tags=["Alerts"], response_model=Alert)
async def resolve_alert(alert_id: str):
    """Resolve an alert."""
    updated = orchestrator.repository_registry.alerts.update(
        {"status": "RESOLVED", "resolved_at": datetime.utcnow().isoformat()},
        "id = ?",
        int(alert_id),
    )
    if updated == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert_data = orchestrator.repository_registry.alerts.select(
        SelectQuery("Alerts").where("id = ?", int(alert_id)).limit(1)
    )
    row = alert_data[0]
    return Alert(
        alert_id=str(row["id"]),
        timestamp=datetime.fromisoformat(row["created_at"]),
        level=row["severity"].lower(),
        type=row["alert_type"],
        message=row["message"],
        resolved=row["status"] == "RESOLVED",
        resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
    )

# --- NPK API ---
@app.get("/api/npk", tags=["NPK"], response_model=NPKResponse)
async def get_npk_readings(limit: int = 10):
    """Get NPK sensor readings from database."""
    npk_data = orchestrator.repository_registry.npk_data.select(
        SelectQuery("NPKData").order_by("id DESC").limit(limit)
    )
    
    npk_list = []
    for row in npk_data:
        npk_list.append(
            NPKReading(
                nitrogen_mg_kg=row["nitrogen_mg_kg"],
                phosphorus_mg_kg=row["phosphorus_mg_kg"],
                potassium_mg_kg=row["potassium_mg_kg"],
                ph=row["ph"],
                ec=row["electrical_conductivity"],
                soil_temp_c=row["soil_temperature_c"],
                soil_moisture_percent=row["moisture_percent"],
                battery_voltage=row["battery_voltage"],
                timestamp=datetime.fromisoformat(row["recorded_at"]) if row["recorded_at"] else datetime.now()
            )
        )
    
    return NPKResponse(
        latest=npk_list[0] if npk_list else None,
        history=npk_list
    )


# --- Analytics API ---
@app.get("/api/analytics/summary", tags=["Analytics"], response_model=AnalyticsSummary)
async def get_analytics_summary(period_days: int = 30):
    """Get analytics summary for specified period from analytics engine."""
    analytics_engine.refresh_from_repositories()
    if not analytics_engine.pump_records and not analytics_engine.prediction_records and not analytics_engine.sensor_health_records:
        now = datetime.now()
        return AnalyticsSummary(
            period_start=now - timedelta(days=period_days),
            period_end=now,
            total_irrigation_events=0,
            total_water_used_liters=0.0,
            avg_soil_moisture_pct=0.0,
            crop_water_stress_days=0,
            ai_predictions_made=0,
            alerts_generated=0,
        )
    data = analytics_engine.get_summary(period_days)
    return AnalyticsSummary(**data)


@app.get("/api/analytics/full", tags=["Analytics"], response_model=FullAnalyticsResponse)
async def get_full_analytics(start_date: Optional[date] = None, end_date: Optional[date] = None):
    """Get comprehensive full analytics from analytics engine."""
    data = analytics_engine.get_full_analytics_summary(start_date, end_date)
    return FullAnalyticsResponse(
        period=data["period"],
        water_consumption=WaterConsumptionAnalytics(**data["water_consumption"]),
        water_savings=WaterSavingsAnalytics(**data["water_savings"]),
        prediction_accuracy=PredictionAccuracyAnalytics(**data["prediction_accuracy"]),
        pump_statistics=PumpStatistics(**data["pump_statistics"]),
        battery_statistics=BatteryStatistics(**data["battery_statistics"]),
        sensor_health=SensorHealthAnalytics(**data["sensor_health"]),
        crop_performance=CropPerformance(**data["crop_performance"]),
        weather_impact=WeatherImpact(**data["weather_impact"])
    )


@app.get("/api/analytics/trends", tags=["Analytics"], response_model=TrendAnalysisResponse)
async def get_trend_analysis():
    """Get trend analysis for all metrics from analytics engine."""
    return TrendAnalysisResponse(**trend_analyzer.get_all_trends())


@app.get("/api/analytics/reports/monthly", tags=["Analytics"])
async def get_monthly_report(year: int = date.today().year, month: int = date.today().month):
    """Get monthly analytics report."""
    report = report_generator.generate_monthly_report(year, month)
    return {"report_id": report.report_id, "data": report.data}


# --- Export API ---
@app.get("/api/analytics/export/csv", tags=["Export"])
async def export_analytics_csv():
    """Export analytics data as CSV."""
    buffer = CSVExporter.export_water_consumption(analytics_engine.water_records)
    return StreamingResponse(
        buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analytics_export.csv"}
    )


@app.get("/api/analytics/export/pdf", tags=["Export"])
async def export_analytics_pdf():
    """Export analytics data as PDF."""
    data = analytics_engine.get_full_analytics_summary()
    buffer = PDFExporter.export_report(data, filename="analytics_report.pdf")
    return StreamingResponse(
        buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=analytics_report.pdf"}
    )


# --- Digital Twin API ---
@app.get("/api/digital-twin/state", tags=["Digital Twin"], response_model=DigitalTwinState)
async def get_digital_twin_state():
    """Get current digital twin state."""
    state = orchestrator.digital_twin.get_current_state()
    if not state:
        state = _get_repository_digital_twin_state()
    return DigitalTwinState(
        timestamp=state.get("timestamp", datetime.now()),
        soil_moisture_vwc=state.get("soil_moisture_vwc", 0.0),
        soil_moisture_pct=state.get("soil_moisture_pct", 0.0),
        pump_state=state.get("pump_state", "unknown"),
        crop_stage=state.get("crop_stage", "unknown"),
        eto_mm_day=state.get("eto_mm_day", 0.0),
        field_area_m2=state.get("field_area_m2", 0.0)
    )


def _get_repository_digital_twin_state():
    sensor_rows = orchestrator.repository_registry.sensor_data.select(
        SelectQuery("SensorData").order_by("id DESC").limit(1)
    )
    pump_rows = orchestrator.repository_registry.pump_status.select(
        SelectQuery("PumpStatus").order_by("id DESC").limit(1)
    )
    state = {"timestamp": datetime.now(), "crop_stage": "unknown", "eto_mm_day": 0.0, "field_area_m2": 0.0}
    if sensor_rows:
        moisture = sensor_rows[0].get("soil_moisture_percent")
        if moisture is not None:
            state["soil_moisture_pct"] = float(moisture)
            state["soil_moisture_vwc"] = float(moisture) / 100.0
            state["timestamp"] = datetime.fromisoformat(sensor_rows[0]["recorded_at"])
    if pump_rows:
        state["pump_state"] = str(pump_rows[0].get("relay_state", "UNKNOWN")).lower()
        if "timestamp" not in state:
            state["timestamp"] = datetime.fromisoformat(pump_rows[0]["recorded_at"])
    return state


@app.post("/api/digital-twin/simulate", tags=["Digital Twin"])
async def run_digital_twin_simulation(request: DigitalTwinSimulationRequest):
    """Run a digital twin simulation."""
    logger.info(f"Starting simulation: {request.duration_hours} hours, scenario: {request.scenario}")
    return {
        "status": "started",
        "duration_hours": request.duration_hours,
        "scenario": request.scenario,
        "message": "Simulation initiated successfully"
    }


# --- Configuration API ---
@app.get("/api/config", tags=["Configuration"], response_model=SystemConfig)
async def get_system_config():
    """Get system configuration."""
    rows = orchestrator.repository_registry.configurations.select(SelectQuery("Configurations"))
    stored = {row["config_key"]: row["config_value"] for row in rows}
    cfg = orchestrator.system_config
    return SystemConfig(
        irrigation_mode=stored.get("irrigation_mode", cfg.irrigation_mode.name.lower()),
        emergency_moisture_threshold=float(stored.get("emergency_moisture_threshold", cfg.emergency_moisture_threshold)),
        ai_confidence_threshold=float(stored.get("ai_confidence_threshold", cfg.ai_confidence_threshold)),
        max_pump_runtime_seconds=int(stored.get("max_pump_runtime_seconds", cfg.max_pump_runtime_seconds)),
        rain_delay_hours=int(stored.get("rain_delay_hours", cfg.rain_delay_hours)),
        weather_latitude=float(stored.get("weather_latitude", 25.3176)),
        weather_longitude=float(stored.get("weather_longitude", 82.9739)),
    )


@app.put("/api/config", tags=["Configuration"], response_model=SystemConfig)
async def update_system_config(config: SystemConfig):
    """Update system configuration."""
    values = config.model_dump()
    ai_confidence_threshold = float(config.ai_confidence_threshold)
    if ai_confidence_threshold > 1.0:
        ai_confidence_threshold = ai_confidence_threshold / 100.0
    values["ai_confidence_threshold"] = ai_confidence_threshold
    mode_lookup = {
        "ai": IrrigationMode.AI,
        "rules": IrrigationMode.RULES,
        "manual": IrrigationMode.MANUAL,
    }
    requested_mode = config.irrigation_mode.strip().lower()
    if requested_mode not in mode_lookup:
        raise HTTPException(status_code=400, detail="irrigation_mode must be 'ai', 'rules', or 'manual'")
    values["irrigation_mode"] = requested_mode
    type_map = {
        "irrigation_mode": "STRING",
        "emergency_moisture_threshold": "FLOAT",
        "ai_confidence_threshold": "FLOAT",
        "max_pump_runtime_seconds": "INTEGER",
        "rain_delay_hours": "INTEGER",
        "weather_latitude": "FLOAT",
        "weather_longitude": "FLOAT",
    }
    for key, value in values.items():
        orchestrator.repository_registry.configurations.set_value(key, str(value), type_map[key])
    orchestrator.system_config.emergency_moisture_threshold = config.emergency_moisture_threshold
    orchestrator.system_config.ai_confidence_threshold = ai_confidence_threshold
    orchestrator.system_config.max_pump_runtime_seconds = config.max_pump_runtime_seconds
    orchestrator.system_config.rain_delay_hours = config.rain_delay_hours
    orchestrator.system_config.irrigation_mode = mode_lookup[requested_mode]
    
    # Clear the manual pump latch if switching back to an automatic mode
    if requested_mode != "manual":
        orchestrator.set_manual_pump_latch(None)
        orchestrator.failsafe_manager.deactivate_manual_override()
        logger.info(f"Cleared manual pump latch and overrides for mode: {requested_mode}")
    
    # Also update failsafe manager which currently copies this value on init
    orchestrator.failsafe_manager.ai_confidence_threshold = ai_confidence_threshold
    
    # Update weather service location dynamically if available
    ws = getattr(orchestrator, "_weather_service", None)
    if ws:
        ws.forecast_manager.latitude = float(config.weather_latitude)
        ws.forecast_manager.longitude = float(config.weather_longitude)
        
    logger.info(f"System configuration updated (Weather: {config.weather_latitude}, {config.weather_longitude})")
    return SystemConfig(**values)

# --- Logs API ---
@app.get("/api/logs", tags=["Logs"], response_model=LogsResponse)
async def get_logs(limit: int = 100, level: Optional[str] = None):
    """Get system logs from database."""
    query = SelectQuery("SystemLogs").order_by("id DESC").limit(limit)
    if level:
        query = query.where("level = ?", level.upper())
    log_data = orchestrator.repository_registry.system_logs.select(query)
    
    log_list = []
    for row in log_data:
        log_list.append(
            LogEntry(
                timestamp=datetime.fromisoformat(row["logged_at"]),
                level=row["level"],
                module=row["module"],
                message=row["message"]
            )
        )
    
    return LogsResponse(
        logs=log_list,
        total_count=len(log_list),
        has_more=len(log_list) >= limit
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# ═══════════════════════════════════════════════════════════════════════════════
# CROP LIFECYCLE + YIELD INTELLIGENCE API
# ═══════════════════════════════════════════════════════════════════════════════
#
# Data flow:
#   Real Sensor/Weather/Farmer Inputs
#     → CropLifecycleService (SQLite CropCycles table)
#       → PhenologyEngine (calculated growth stage)
#         → YieldCalculator (comparison when both values present)
#           → WaterProductivityCalculator (when harvest + irrigation data exist)
#
# Every endpoint returns explicit SOURCE labels so the UI can show data
# provenance (AI Prediction / Farmer Input / Calculated / Not Available).
# ═══════════════════════════════════════════════════════════════════════════════


def _cycle_to_response(cycle: dict) -> CropCycleResponse:
    """Convert an enriched CropCycle dict to the Pydantic response model."""
    gsi = None
    raw_gsi = cycle.get("growth_stage_info")
    if raw_gsi:
        try:
            gsi = GrowthStageInfo(**raw_gsi)
        except Exception:
            gsi = None
    return CropCycleResponse(
        id=cycle["id"],
        crop_type=cycle["crop_type"],
        ai_recommended_crop=cycle.get("ai_recommended_crop"),
        farmer_selected_crop=cycle.get("farmer_selected_crop"),
        planting_date=cycle.get("planting_date"),
        field_id=cycle.get("field_id"),
        field_area_m2=cycle.get("field_area_m2"),
        lifecycle_status=cycle["lifecycle_status"],
        expected_yield_kg=cycle.get("expected_yield_kg"),
        actual_yield_kg=cycle.get("actual_yield_kg"),
        harvest_date=cycle.get("harvest_date"),
        harvest_notes=cycle.get("harvest_notes"),
        accumulated_gdd=cycle.get("accumulated_gdd"),
        notes=cycle.get("notes"),
        created_at=cycle["created_at"],
        updated_at=cycle["updated_at"],
        days_since_planting=cycle.get("days_since_planting"),
        days_since_planting_source=cycle.get("days_since_planting_source", "unavailable"),
        growth_stage=cycle.get("growth_stage", "Not Started"),
        growth_stage_info=gsi,
        crop_type_source=cycle.get("crop_type_source", "manual_input"),
        planting_date_source=cycle.get("planting_date_source", "not_set"),
        expected_yield_display=cycle.get("expected_yield_display", "Not Available — awaiting real data"),
        expected_yield_source=cycle.get("expected_yield_source", "not_available"),
        actual_yield_display=cycle.get("actual_yield_display", "Not Available — awaiting harvest entry"),
        actual_yield_source=cycle.get("actual_yield_source", "not_available"),
    )


# ── 1. GET active crop cycle ─────────────────────────────────────────────────

@app.get(
    "/api/crop-lifecycle/active",
    tags=["Crop Lifecycle"],
    response_model=CropCycleResponse,
    summary="Get active (non-harvested) crop cycle",
)
async def get_active_crop_cycle():
    """Return the current active crop cycle with all calculated lifecycle fields.

    Calculated fields have SOURCE = phenology_engine / calculated.
    If no active cycle exists, returns 404.
    """
    svc = _get_lifecycle_service()
    cycle = svc.get_active_cycle()
    if cycle is None:
        raise HTTPException(
            status_code=404,
            detail="No active crop cycle found. Create one via POST /api/crop-lifecycle.",
        )
    return _cycle_to_response(cycle)


# ── 2. List all crop cycles (history) ───────────────────────────────────────

@app.get(
    "/api/crop-lifecycle/history",
    tags=["Crop Lifecycle"],
    response_model=CropLifecycleHistoryResponse,
    summary="List all crop cycle history",
)
async def list_crop_cycles(limit: int = 50, active_only: bool = False):
    """Return all crop cycles, newest first.

    Preserves full historical records — cycles are never deleted on harvest.
    """
    svc = _get_lifecycle_service()
    cycles = svc.list_cycles(limit=limit, include_completed=not active_only)
    return CropLifecycleHistoryResponse(
        cycles=[_cycle_to_response(c) for c in cycles],
        total_count=len(cycles),
    )


# ── 3. Create new crop cycle ─────────────────────────────────────────────────

@app.post(
    "/api/crop-lifecycle",
    tags=["Crop Lifecycle"],
    response_model=CropCycleResponse,
    status_code=201,
    summary="Create a new crop cycle",
)
async def create_crop_cycle(request: CreateCropCycleRequest):
    """Create a new crop cycle record.

    Typically triggered after farmer confirms a crop recommendation.

    Data provenance:
        crop_type          SOURCE = farmer_selected / ai_recommended
        planting_date      SOURCE = farmer_input (if provided at creation)
        expected_yield_kg  SOURCE = not_available (no validated yield model yet)
        actual_yield_kg    SOURCE = not_available (awaiting harvest entry)
    """
    svc = _get_lifecycle_service()
    try:
        cycle = svc.create_cycle(
            crop_type=request.crop_type,
            ai_recommended_crop=request.ai_recommended_crop,
            farmer_selected_crop=request.farmer_selected_crop,
            planting_date=request.planting_date,
            field_id=request.field_id,
            field_area_m2=request.field_area_m2,
            notes=request.notes,
        )
    except Exception as exc:
        logger.exception("Failed to create crop cycle")
        raise HTTPException(status_code=500, detail=str(exc))
    return _cycle_to_response(cycle)


# ── 4. Get single crop cycle ─────────────────────────────────────────────────

@app.get(
    "/api/crop-lifecycle/{cycle_id}",
    tags=["Crop Lifecycle"],
    response_model=CropCycleResponse,
    summary="Get a specific crop cycle by ID",
)
async def get_crop_cycle(cycle_id: int):
    svc = _get_lifecycle_service()
    cycle = svc.get_cycle(cycle_id)
    if cycle is None:
        raise HTTPException(status_code=404, detail=f"Crop cycle {cycle_id} not found")
    return _cycle_to_response(cycle)


# ── 5. Confirm planted crop (farmer input) ───────────────────────────────────

@app.post(
    "/api/crop-lifecycle/{cycle_id}/confirm-crop",
    tags=["Crop Lifecycle"],
    response_model=CropCycleResponse,
    summary="Farmer confirms / overrides the planted crop",
)
async def confirm_planted_crop(cycle_id: int, request: ConfirmCropRequest):
    """Record the farmer's confirmed crop selection.

    SOURCE = farmer_input.
    Distinguishes clearly between:
        - AI recommended crop  (ai_recommended_crop)
        - Farmer selected crop (farmer_selected_crop) ← set here
    """
    svc = _get_lifecycle_service()
    try:
        cycle = svc.confirm_crop(
            cycle_id=cycle_id,
            farmer_selected_crop=request.farmer_selected_crop,
            planting_date=request.planting_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _cycle_to_response(cycle)


# ── 6. Set planting date ─────────────────────────────────────────────────────

@app.post(
    "/api/crop-lifecycle/{cycle_id}/planting-date",
    tags=["Crop Lifecycle"],
    response_model=CropCycleResponse,
    summary="Record actual planting date (farmer input)",
)
async def set_planting_date(cycle_id: int, request: SetPlantingDateRequest):
    """Set the actual planting date.

    SOURCE = farmer_input.
    After this is set, days_since_planting and growth_stage are automatically
    calculated from ``current_date - planting_date``.
    """
    # Validate date format
    try:
        date.fromisoformat(request.planting_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid planting_date format '{request.planting_date}'. Use YYYY-MM-DD.",
        )
    svc = _get_lifecycle_service()
    try:
        cycle = svc.set_planting_date(cycle_id, request.planting_date)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _cycle_to_response(cycle)


# ── 7. Update lifecycle status ───────────────────────────────────────────────

@app.put(
    "/api/crop-lifecycle/{cycle_id}/status",
    tags=["Crop Lifecycle"],
    response_model=CropCycleResponse,
    summary="Update lifecycle status (farmer or system override)",
)
async def update_lifecycle_status(cycle_id: int, request: UpdateLifecycleStatusRequest):
    """Manually advance or override lifecycle status.

    Valid statuses: PLANNED, PLANTED, GROWING, HARVEST_READY, HARVESTED, COMPLETED.
    Farmer-confirmed status changes are NOT silently overwritten by AI calculations.
    """
    svc = _get_lifecycle_service()
    try:
        cycle = svc.update_lifecycle_status(cycle_id, request.lifecycle_status.upper())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _cycle_to_response(cycle)


# ── 8. Get current growth stage ──────────────────────────────────────────────

@app.get(
    "/api/crop-lifecycle/{cycle_id}/growth-stage",
    tags=["Crop Lifecycle"],
    response_model=CropGrowthStageResponse,
    summary="Get current crop growth stage",
)
async def get_growth_stage(cycle_id: int):
    """Return the current phenological growth stage.

    SOURCE = phenology_engine / calculated from (days_since_planting, crop_type).
    Stage is NOT image-AI detected (architecture-ready for future model).
    """
    svc = _get_lifecycle_service()
    cycle = svc.get_cycle(cycle_id)
    if cycle is None:
        raise HTTPException(status_code=404, detail=f"Crop cycle {cycle_id} not found")
    gsi = None
    raw = cycle.get("growth_stage_info")
    if raw:
        try:
            gsi = GrowthStageInfo(**raw)
        except Exception:
            gsi = None
    return CropGrowthStageResponse(
        crop_cycle_id=cycle_id,
        crop_type=cycle["crop_type"],
        planting_date=cycle.get("planting_date"),
        days_since_planting=cycle.get("days_since_planting"),
        growth_stage=cycle.get("growth_stage", "Not Started"),
        growth_stage_info=gsi,
        lifecycle_status=cycle["lifecycle_status"],
        accumulated_gdd=cycle.get("accumulated_gdd"),
        source="phenology_engine / calculated",
    )


# ── 9. Record harvest ────────────────────────────────────────────────────────

@app.post(
    "/api/crop-lifecycle/{cycle_id}/harvest",
    tags=["Crop Lifecycle"],
    response_model=CropCycleResponse,
    summary="Record harvest date and actual yield (farmer input)",
)
async def record_harvest(cycle_id: int, request: RecordHarvestRequest):
    """Record actual harvest.

    SOURCE of actual_yield_kg = harvest_measurement / farmer_input.
    This is the ONLY endpoint that writes actual_yield_kg.
    Never copies expected_yield_kg into actual_yield_kg.

    The crop cycle is preserved (not deleted) after harvest.
    """
    try:
        date.fromisoformat(request.harvest_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid harvest_date format '{request.harvest_date}'. Use YYYY-MM-DD.",
        )
    if request.actual_yield_kg < 0:
        raise HTTPException(status_code=400, detail="actual_yield_kg must be >= 0")
    svc = _get_lifecycle_service()
    try:
        cycle = svc.record_harvest(
            cycle_id=cycle_id,
            harvest_date=request.harvest_date,
            actual_yield_kg=request.actual_yield_kg,
            notes=request.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _cycle_to_response(cycle)


# ── 10. Yield comparison ─────────────────────────────────────────────────────

@app.get(
    "/api/crop-lifecycle/{cycle_id}/yield-comparison",
    tags=["Crop Lifecycle"],
    response_model=YieldComparisonResponse,
    summary="Compare expected vs actual yield",
)
async def get_yield_comparison(cycle_id: int):
    """Compare expected (AI prediction) vs actual (farmer harvest) yield.

    Returns yield_difference, yield_achievement_pct, prediction_error_pct.
    All values are safe-to-display with explicit SOURCE labels.
    Never shows fabricated percentages when data is missing.
    """
    svc = _get_lifecycle_service()
    cycle = svc.get_cycle(cycle_id)
    if cycle is None:
        raise HTTPException(status_code=404, detail=f"Crop cycle {cycle_id} not found")
    result = _yield_calculator.compare(
        expected_yield_kg=cycle.get("expected_yield_kg"),
        actual_yield_kg=cycle.get("actual_yield_kg"),
    )
    return YieldComparisonResponse(**result)


# ── 11. Water productivity ───────────────────────────────────────────────────

@app.get(
    "/api/crop-lifecycle/{cycle_id}/water-productivity",
    tags=["Crop Lifecycle"],
    response_model=WaterProductivityResponse,
    summary="Calculate water productivity for a crop cycle",
)
async def get_water_productivity(cycle_id: int):
    """Compute water productivity = actual_yield / total_irrigation_water.

    SOURCE of water_used_liters  = pump_records / irrigation_history
    SOURCE of actual_yield_kg    = harvest_measurement / farmer_input
    SOURCE of result             = calculated

    Unit: kg per litre (kg/L).  Returns 'Not Available' if data is missing.
    """
    svc = _get_lifecycle_service()
    cycle = svc.get_cycle(cycle_id)
    if cycle is None:
        raise HTTPException(status_code=404, detail=f"Crop cycle {cycle_id} not found")

    # Sum total irrigation water for this cycle's date range
    water_used_liters: float | None = None
    planting_date_str = cycle.get("planting_date")
    if planting_date_str:
        try:
            analytics_engine.refresh_from_repositories()
            total = sum(
                r.volume_pumped_liters
                for r in analytics_engine.pump_records
                if r.volume_pumped_liters > 0
            )
            water_used_liters = round(total, 3) if total > 0 else None
        except Exception as exc:
            logger.warning("Could not load pump records for water productivity: %s", exc)

    result = _water_productivity_calc.calculate(
        actual_yield_kg=cycle.get("actual_yield_kg"),
        water_used_liters=water_used_liters,
    )
    return WaterProductivityResponse(**result)


# ── 12. Phenology config ─────────────────────────────────────────────────────

@app.get(
    "/api/crop-lifecycle/phenology/{crop_name}",
    tags=["Crop Lifecycle"],
    response_model=CropPhenologyResponse,
    summary="Get growth stage configuration for a crop",
)
async def get_crop_phenology(crop_name: str):
    """Return the phenological stage configuration for a given crop.

    SOURCE = phenology_config (requires agronomic validation).
    Stage thresholds are configurable defaults — must be validated with local
    agronomic data before treating as authoritative.
    """
    config = _phenology_engine.get_config(crop_name)
    stages = _phenology_engine.list_stages(crop_name)
    return CropPhenologyResponse(
        crop_name=config.crop_name,
        growing_season_days=config.growing_season_days,
        base_temperature_c=config.base_temperature_c,
        stages=[PhenologyStageDef(**s) for s in stages],
        notes=config.notes,
    )


@app.get(
    "/api/crop-lifecycle/phenology",
    tags=["Crop Lifecycle"],
    summary="List all supported crop phenology configurations",
)
async def list_supported_crops():
    """List all crops that have dedicated phenology configurations."""
    return {
        "supported_crops": _phenology_engine.supported_crops(),
        "fallback": "generic",
        "note": (
            "Crops not in this list fall back to a generic 7-stage template. "
            "All thresholds require agronomic validation. "
            "SOURCE = phenology_config"
        ),
    }


# ── 13. Crop recommendation → cycle integration ───────────────────────────────

@app.post(
    "/api/crop-recommendation/start-cycle",
    tags=["Crop Lifecycle", "Crop Recommendation"],
    response_model=CropCycleResponse,
    status_code=201,
    summary="Create crop cycle from a recommendation (requires farmer confirmation)",
)
async def create_cycle_from_recommendation(
    farmer_selected_crop: str,
    planting_date: Optional[str] = None,
    field_area_m2: Optional[float] = None,
):
    """Create a new crop cycle after farmer confirms a recommendation.

    The farmer MUST explicitly pick a crop (farmer_selected_crop).
    The AI top-1 recommendation is captured for provenance but NOT assumed.

    Data provenance:
        ai_recommended_crop   SOURCE = XGBoost crop recommendation model
        farmer_selected_crop  SOURCE = farmer_input (this call)
        planting_date         SOURCE = farmer_input (if provided)
    """
    # Get latest AI recommendation for provenance tracking
    npk_rows = orchestrator.repository_registry.npk_data.select(
        SelectQuery("NPKData").order_by("id DESC").limit(1)
    )
    weather_context = _latest_weather_context()
    rec_result = crop_recommendation_service.recommend(
        npk_rows[0] if npk_rows else None,
        weather_context=weather_context,
        top_n=1,
    )
    ai_top_crop = (
        rec_result.selected_crop["crop"]
        if (rec_result.selected_crop and rec_result.status == "live")
        else None
    )

    svc = _get_lifecycle_service()
    cycle = svc.create_cycle(
        crop_type=farmer_selected_crop,
        ai_recommended_crop=ai_top_crop,
        farmer_selected_crop=farmer_selected_crop,
        planting_date=planting_date,
        field_area_m2=field_area_m2,
    )
    logger.info(
        "Crop cycle created from recommendation: farmer=%s ai=%s", farmer_selected_crop, ai_top_crop
    )
    return _cycle_to_response(cycle)


# ── 14. Image upload (architecture-ready) ────────────────────────────────────

@app.post(
    "/api/crop-lifecycle/{cycle_id}/images",
    tags=["Crop Lifecycle"],
    summary="Register crop image metadata (model inference NOT yet available)",
)
async def register_crop_image(
    cycle_id: int,
    filename: str,
    file_path: str,
    upload_source: str = "web_upload",
    notes: Optional[str] = None,
):
    """Store image metadata for a crop cycle.

    IMPORTANT: Image-AI model inference is NOT yet implemented.
    This endpoint stores file metadata only.
    Growth stage / disease detection from images requires a trained model
    that has not yet been added to this system.

    Architecture is ready for future model integration.
    """
    svc = _get_lifecycle_service()
    try:
        image_id = svc.add_image_record(
            cycle_id=cycle_id,
            filename=filename,
            file_path=file_path,
            upload_source=upload_source,
            notes=notes,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {
        "status": "metadata_stored",
        "image_id": image_id,
        "cycle_id": cycle_id,
        "model_inference": "not_available — awaiting trained crop image model",
        "filename": filename,
    }


@app.get(
    "/api/crop-lifecycle/{cycle_id}/images",
    tags=["Crop Lifecycle"],
    summary="Get image records for a crop cycle",
)
async def get_crop_images(cycle_id: int):
    svc = _get_lifecycle_service()
    images = svc.get_images(cycle_id)
    return {
        "cycle_id": cycle_id,
        "images": images,
        "model_inference": "not_available — awaiting trained crop image model",
    }


# ── 15. Mark cycle completed ─────────────────────────────────────────────────

@app.post(\
    "/api/crop-lifecycle/{cycle_id}/complete",
    tags=["Crop Lifecycle"],
    response_model=CropCycleResponse,
    summary="Move a harvested crop cycle to COMPLETED (archive)",
)
async def complete_crop_cycle(cycle_id: int):
    """Archive a harvested crop cycle.

    Cycle record is preserved — NOT deleted.
    Useful for moving fully processed cycles out of the active list.
    """
    svc = _get_lifecycle_service()
    try:
        cycle = svc.mark_completed(cycle_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _cycle_to_response(cycle)


# ── 16. Delete crop cycle (permanent — user-initiated only) ──────────────────

@app.delete(
    "/api/crop-lifecycle/{cycle_id}",
    tags=["Crop Lifecycle"],
    status_code=200,
    summary="Permanently delete a crop cycle (user-initiated only)",
)
async def delete_crop_cycle(cycle_id: int):
    """Permanently remove a crop cycle and its image records.

    This endpoint is intentionally not called automatically — only triggered
    by an explicit user action on the dashboard.

    Returns 404 if the cycle does not exist.
    """
    svc = _get_lifecycle_service()
    try:
        deleted = svc.delete_cycle(cycle_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Crop cycle {cycle_id} not found")
    logger.info("Crop cycle %s deleted via API", cycle_id)
    return {"status": "deleted", "cycle_id": cycle_id}


# ── 17. Recalculate GDD from sensor temperature data ────────────────────────

@app.post(
    "/api/crop-lifecycle/{cycle_id}/update-gdd",
    tags=["Crop Lifecycle"],
    response_model=CropCycleResponse,
    summary="Recalculate accumulated GDD from sensor temperature readings",
)
async def update_gdd_from_sensors(cycle_id: int):
    """Compute accumulated Growing Degree Days (GDD) from real sensor data.

    GDD = Σ max(0, daily_mean_temp − base_temp)
    where daily_mean_temp = average of all temperature_c readings for that day.

    SOURCE = weather/sensor + calculation.
    Returns 404 if cycle not found or no temperature data available.
    """
    svc = _get_lifecycle_service()
    cycle = svc.get_cycle(cycle_id)
    if cycle is None:
        raise HTTPException(status_code=404, detail=f"Crop cycle {cycle_id} not found")

    planting_date_str = cycle.get("planting_date")
    if not planting_date_str:
        raise HTTPException(
            status_code=400,
            detail="Cannot calculate GDD — planting_date not set on this cycle.",
        )

    # Get crop base temperature from phenology config
    try:
        pheno_config = _phenology_engine.get_config(cycle["crop_type"])
        base_temp = pheno_config.base_temperature_c
    except Exception:
        base_temp = 10.0  # generic agricultural base temperature

    # Load all temperature readings from planting date onwards
    try:
        all_sensor_rows = orchestrator.repository_registry.sensor_data.select(
            SelectQuery("SensorData").order_by("recorded_at ASC").limit(10000)
        )
        # Filter to readings after planting date where temperature_c is real (non-zero)
        from datetime import date as _date
        planting_dt = _date.fromisoformat(planting_date_str)
        daily_temps: dict = {}  # date_str -> list of temp readings

        for row in all_sensor_rows:
            temp = row.get("temperature_c")
            if temp is None or temp == 0.0:
                continue
            recorded_at = row.get("recorded_at")
            if not recorded_at:
                continue
            try:
                reading_date = _date.fromisoformat(recorded_at[:10])
            except Exception:
                continue
            if reading_date < planting_dt:
                continue
            day_str = str(reading_date)
            daily_temps.setdefault(day_str, []).append(temp)

        if not daily_temps:
            raise HTTPException(
                status_code=422,
                detail="No non-zero temperature sensor readings found since planting date. "
                       "GDD cannot be calculated from current data.",
            )

        # Calculate GDD per day and accumulate
        accumulated_gdd = 0.0
        for day_str, temps in sorted(daily_temps.items()):
            mean_temp = sum(temps) / len(temps)
            daily_gdd = max(0.0, mean_temp - base_temp)
            accumulated_gdd += daily_gdd

        svc.update_gdd(cycle_id, round(accumulated_gdd, 2))
        logger.info(
            "GDD updated: cycle=%s gdd=%.2f from %d days of sensor data (base_temp=%.1f°C)",
            cycle_id, accumulated_gdd, len(daily_temps), base_temp,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("GDD calculation failed for cycle %s", cycle_id)
        raise HTTPException(status_code=500, detail=f"GDD calculation failed: {exc}")

    return _cycle_to_response(svc.get_cycle(cycle_id))


# ═══════════════════════════════════════════════════════════════════════════════
# PLANT DISEASE DETECTION API
# ═══════════════════════════════════════════════════════════════════════════════
#
# Model status: NOT YET CONNECTED
# The inference endpoints are architecture-ready. When a trained plant disease
# model (e.g., PlantVillage-trained CNN/ViT) is placed in the repository and
# the inference module is implemented, these endpoints will return real results.
#
# History is stored in SQLite via the existing database infrastructure.
# Uploads are saved to UPLOAD_DIR and image_url returned for frontend display.
# ═══════════════════════════════════════════════════════════════════════════════

UPLOAD_DIR = Path(__file__).parent.parent / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Simple in-process history store (replaced by DB in production)
_disease_history: List[dict] = []
_pest_history: List[dict] = []


# ── Disease Status ─────────────────────────────────────────────────────────────

@app.get("/api/disease/status", tags=["Plant Disease"], response_model=DiseaseStatusResponse)
async def get_disease_status():
    """Return whether the plant disease inference model is available."""
    # Check if a disease model file exists anywhere in the AI models directory
    model_dir = Path(__file__).parent.parent / "ai"
    disease_model_found = any(
        f.suffix in {".h5", ".keras", ".pt", ".pth", ".onnx", ".tflite"}
        for f in model_dir.rglob("*disease*")
    ) if model_dir.exists() else False

    return DiseaseStatusResponse(
        available=disease_model_found,
        message="Plant disease model is ready." if disease_model_found else (
            "Plant disease inference model not found. "
            "Place a trained model in the ai/models directory and implement the inference pipeline."
        ),
        model_name="PlantVillage-CNN" if disease_model_found else None,
        supported_crops=["Tomato", "Potato", "Pepper", "Grape", "Apple", "Corn", "Wheat"] if disease_model_found else [],
    )


# ── Disease Predict ────────────────────────────────────────────────────────────

@app.post("/api/disease/predict", tags=["Plant Disease"], response_model=DiseasePrediction)
async def predict_disease(file: UploadFile = File(...)):
    """Run plant disease inference on uploaded image.

    IMPORTANT: Model inference is NOT yet implemented.
    This endpoint saves the uploaded file, creates a history record, and
    returns a standard 'model unavailable' response. Integrate a trained
    disease detection model to activate inference.
    """
    # Validate file type
    if file.content_type not in {"image/jpeg", "image/jpg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use JPEG, PNG, or WEBP.")

    # Read and validate size
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10 MB.")

    # Save file
    scan_id = str(uuid.uuid4())
    ext = Path(file.filename or "image.jpg").suffix or ".jpg"
    save_path = UPLOAD_DIR / f"disease_{scan_id}{ext}"
    save_path.write_bytes(contents)

    # ── Model inference placeholder ────────────────────────────────────────────
    # TODO: Load and run the actual disease detection model here.
    # Expected return format:
    # {
    #   "crop": "Tomato",
    #   "disease_class": "Tomato___Late_blight",
    #   "is_healthy": False,
    #   "confidence": 0.92,
    #   "alternatives": [{"class": "Tomato___Early_blight", "confidence": 0.05}]
    # }
    # ──────────────────────────────────────────────────────────────────────────

    # Return model-unavailable status (do not fabricate predictions)
    raise HTTPException(
        status_code=503,
        detail={
            "error": "model_unavailable",
            "message": "Plant disease model is not connected. Upload saved.",
            "scan_id": scan_id,
            "image_path": str(save_path),
        }
    )


# ── Disease History ────────────────────────────────────────────────────────────

@app.get("/api/disease/history", tags=["Plant Disease"], response_model=DiseaseHistoryResponse)
async def get_disease_history(limit: int = 50, skip: int = 0):
    """Return plant disease detection history (most recent first)."""
    sorted_records = sorted(_disease_history, key=lambda r: r["created_at"], reverse=True)
    sliced = sorted_records[skip: skip + limit]
    return DiseaseHistoryResponse(
        records=[DiseasePrediction(**r) for r in sliced],
        total_count=len(_disease_history),
    )


@app.get("/api/disease/history/{scan_id}", tags=["Plant Disease"], response_model=DiseasePrediction)
async def get_disease_record(scan_id: str):
    """Return a single disease detection record by scan_id."""
    record = next((r for r in _disease_history if r["scan_id"] == scan_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Disease scan {scan_id} not found.")
    return DiseasePrediction(**record)


@app.delete("/api/disease/history/{scan_id}", tags=["Plant Disease"])
async def delete_disease_record(scan_id: str):
    """Delete a disease detection record and its associated image."""
    global _disease_history
    record = next((r for r in _disease_history if r["scan_id"] == scan_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Disease scan {scan_id} not found.")
    # Delete image file if it exists
    if record.get("image_path"):
        try:
            Path(record["image_path"]).unlink(missing_ok=True)
        except Exception:
            pass
    _disease_history = [r for r in _disease_history if r["scan_id"] != scan_id]
    return {"status": "deleted", "scan_id": scan_id}


# ═══════════════════════════════════════════════════════════════════════════════
# PEST DETECTION API
# ═══════════════════════════════════════════════════════════════════════════════
#
# Model status: NOT YET CONNECTED
# This module is architecture-ready for object detection models (YOLO, SSD, etc.)
# or classification models. Connect a trained pest detection model to activate.
# ═══════════════════════════════════════════════════════════════════════════════


# ── Pest Status ────────────────────────────────────────────────────────────────

@app.get("/api/pest/status", tags=["Pest Detection"], response_model=PestStatusResponse)
async def get_pest_status():
    """Return whether the pest detection inference model is available."""
    model_dir = Path(__file__).parent.parent / "ai"
    pest_model_found = any(
        f.suffix in {".h5", ".keras", ".pt", ".pth", ".onnx", ".tflite"}
        for f in model_dir.rglob("*pest*")
    ) if model_dir.exists() else False

    return PestStatusResponse(
        available=pest_model_found,
        message="Pest detection model is ready." if pest_model_found else (
            "Pest detection model not found. "
            "Integrate a trained pest detection model (YOLO/SSD/classifier) to activate inference."
        ),
        model_name=None,
    )


# ── Pest Predict ───────────────────────────────────────────────────────────────

@app.post("/api/pest/predict", tags=["Pest Detection"], response_model=PestPrediction)
async def predict_pest(file: UploadFile = File(...)):
    """Run pest detection inference on uploaded image.

    IMPORTANT: Model inference is NOT yet implemented.
    This endpoint validates the image, saves it, and returns a 503 until a
    compatible pest detection model is integrated.
    """
    if file.content_type not in {"image/jpeg", "image/jpg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use JPEG, PNG, or WEBP.")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10 MB.")

    scan_id = str(uuid.uuid4())
    ext = Path(file.filename or "image.jpg").suffix or ".jpg"
    save_path = UPLOAD_DIR / f"pest_{scan_id}{ext}"
    save_path.write_bytes(contents)

    # ── Pest model inference placeholder ──────────────────────────────────────
    # TODO: Load and run the actual pest detection model here.
    # For object detection models, expected return format:
    # {
    #   "pest_class": "aphid",
    #   "confidence": 0.87,
    #   "detection_count": 5,
    #   "bounding_boxes": [{"x": 100, "y": 50, "width": 60, "height": 40, "label": "aphid", "conf": 0.87}]
    # }
    # ──────────────────────────────────────────────────────────────────────────

    raise HTTPException(
        status_code=503,
        detail={
            "error": "model_unavailable",
            "message": "Pest detection model is not connected. Upload saved.",
            "scan_id": scan_id,
            "image_path": str(save_path),
        }
    )


# ── Pest History ───────────────────────────────────────────────────────────────

@app.get("/api/pest/history", tags=["Pest Detection"], response_model=PestHistoryResponse)
async def get_pest_history(limit: int = 50, skip: int = 0):
    """Return pest detection history (most recent first)."""
    sorted_records = sorted(_pest_history, key=lambda r: r["created_at"], reverse=True)
    sliced = sorted_records[skip: skip + limit]
    return PestHistoryResponse(
        records=[PestPrediction(**r) for r in sliced],
        total_count=len(_pest_history),
    )


@app.get("/api/pest/history/{scan_id}", tags=["Pest Detection"], response_model=PestPrediction)
async def get_pest_record(scan_id: str):
    """Return a single pest detection record by scan_id."""
    record = next((r for r in _pest_history if r["scan_id"] == scan_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Pest scan {scan_id} not found.")
    return PestPrediction(**record)


@app.delete("/api/pest/history/{scan_id}", tags=["Pest Detection"])
async def delete_pest_record(scan_id: str):
    """Delete a pest detection record and its associated image."""
    global _pest_history
    record = next((r for r in _pest_history if r["scan_id"] == scan_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Pest scan {scan_id} not found.")
    if record.get("image_path"):
        try:
            Path(record["image_path"]).unlink(missing_ok=True)
        except Exception:
            pass
    _pest_history = [r for r in _pest_history if r["scan_id"] != scan_id]
    return {"status": "deleted", "scan_id": scan_id}
