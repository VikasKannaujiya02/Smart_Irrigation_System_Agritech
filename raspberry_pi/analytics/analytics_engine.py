"""Main Analytics Engine for the Irrigation Digital Twin."""

import logging
import json
from datetime import datetime, date, timedelta, timezone
from typing import Dict, List, Optional, Any
from collections import defaultdict
import numpy as np

from .models import (
    WaterConsumptionRecord,
    PredictionRecord,
    PumpRuntimeRecord,
    BatteryRecord,
    SensorHealthRecord,
    CropRecord,
    WeatherImpactRecord,
    SensorHealthStatus,
    CropGrowthStage
)

logger = logging.getLogger(__name__)


class AnalyticsEngine:
    """
    Core analytics engine for calculating all key metrics.
    """

    def __init__(self, repository_registry: Any | None = None):
        self.repository_registry = repository_registry
        # In-memory storage for analytics snapshots and fallback when no DB rows exist
        self.water_records: List[WaterConsumptionRecord] = []
        self.prediction_records: List[PredictionRecord] = []
        self.pump_records: List[PumpRuntimeRecord] = []
        self.battery_records: List[BatteryRecord] = []
        self.sensor_health_records: List[SensorHealthRecord] = []
        self.crop_records: List[CropRecord] = []
        self.weather_records: List[WeatherImpactRecord] = []
        
        if repository_registry is None:
            self._initialize_sample_data()
        else:
            self.refresh_from_repositories()
        logger.info("Analytics Engine initialized.")

    def _initialize_sample_data(self):
        """Populate sample data for demonstration purposes."""
        now = datetime.now()
        
        # Water consumption
        for i in range(30):
            dt = now - timedelta(days=i)
            self.water_records.append(
                WaterConsumptionRecord(
                    id=f"water_{i}",
                    timestamp=dt,
                    volume_liters=np.random.randint(50, 200),
                    source="irrigation",
                    field_id="field_001"
                )
            )
            if i % 5 == 0:
                self.water_records.append(
                    WaterConsumptionRecord(
                        id=f"water_rain_{i}",
                        timestamp=dt,
                        volume_liters=np.random.randint(10, 50),
                        source="rain",
                        field_id="field_001"
                    )
                )
        
        # Pump runtime
        for i in range(30):
            start = now - timedelta(days=i, hours=np.random.randint(1, 12))
            runtime = np.random.randint(60, 3600)
            self.pump_records.append(
                PumpRuntimeRecord(
                    id=f"pump_{i}",
                    pump_id="pump_001",
                    start_time=start,
                    end_time=start + timedelta(seconds=runtime),
                    total_runtime_seconds=runtime,
                    volume_pumped_liters=np.random.randint(30, 150)
                )
            )
        
        # Predictions
        for i in range(50):
            pred_time = now - timedelta(hours=i*2)
            self.prediction_records.append(
                PredictionRecord(
                    id=f"pred_{i}",
                    timestamp=pred_time,
                    prediction_type="soil_moisture",
                    predicted_value=30 + np.random.rand()*30,
                    actual_value=30 + np.random.rand()*30,
                    confidence=0.8 + np.random.rand()*0.2
                )
            )
        
        # Battery records
        for i in range(30):
            self.battery_records.append(
                BatteryRecord(
                    id=f"bat_{i}",
                    device_id=f"sensor_{i%4}",
                    timestamp=now - timedelta(days=i),
                    percentage=70 + np.random.rand()*30
                )
            )
        
        # Sensor health
        for i in range(30):
            self.sensor_health_records.append(
                SensorHealthRecord(
                    id=f"sensor_health_{i}",
                    sensor_id=f"sensor_{i%4}",
                    timestamp=now - timedelta(days=i),
                    status=SensorHealthStatus.HEALTHY if i%10 !=0 else SensorHealthStatus.WARNING
                )
            )
        
        # Crop
        self.crop_records.append(
            CropRecord(
                id="crop_001",
                crop_type="Tomato",
                planting_date=date.today() - timedelta(days=45),
                growth_stage=CropGrowthStage.VEGETATIVE
            )
        )
        
        # Weather
        for i in range(30):
            dt = now.date() - timedelta(days=i)
            self.weather_records.append(
                WeatherImpactRecord(
                    id=f"weather_{i}",
                    date=dt,
                    temperature_c_avg=20 + np.random.rand()*10,
                    humidity_pct_avg=40 + np.random.rand()*40,
                    rainfall_mm=np.random.rand()*5 if i%3 ==0 else 0,
                    eto_mm=2 + np.random.rand()*4
                )
            )

    def calculate_water_consumption(self, start: date, end: date) -> Dict[str, Any]:
        """Calculate water consumption metrics for a date range."""
        filtered = [r for r in self.water_records 
                    if start <= r.timestamp.date() <= end]
        
        total_irrigation = sum(r.volume_liters for r in filtered if r.source == "irrigation")
        total_rain = sum(r.volume_liters for r in filtered if r.source == "rain")
        
        daily_usage = defaultdict(float)
        for r in filtered:
            daily_usage[r.timestamp.date()] += r.volume_liters
        
        return {
            "total_irrigation_liters": round(total_irrigation, 2),
            "total_rain_liters": round(total_rain, 2),
            "daily_usage": {str(d): round(v, 2) for d, v in sorted(daily_usage.items())},
            "avg_daily_liters": round(np.mean(list(daily_usage.values())) if daily_usage else 0, 2),
            "max_daily_liters": round(max(daily_usage.values()) if daily_usage else 0, 2)
        }

    def calculate_water_savings(self, start: date, end: date, baseline_lpd: Optional[float] = None) -> Dict[str, Any]:
        """Calculate water savings only when a real baseline is configured.

        A fixed demo baseline would make the dashboard show artificial savings.
        Until a real agronomic/baseline value is provided, report actual usage
        and zero savings instead of inventing saved water.
        """
        consumption_data = self.calculate_water_consumption(start, end)
        
        actual_usage = consumption_data["total_irrigation_liters"]
        if baseline_lpd is None or baseline_lpd <= 0:
            baseline_usage = actual_usage
        else:
            num_days = (end - start).days + 1
            baseline_usage = baseline_lpd * num_days
        savings = max(0, baseline_usage - actual_usage)
        savings_pct = (savings / baseline_usage) * 100 if baseline_usage >0 else 0
        
        return {
            "actual_usage_liters": round(actual_usage, 2),
            "baseline_usage_liters": round(baseline_usage, 2),
            "total_savings_liters": round(savings, 2),
            "savings_percentage": round(savings_pct, 2)
        }

    def calculate_prediction_accuracy(self, start: date, end: date) -> Dict[str, Any]:
        """Calculate AI prediction accuracy metrics."""
        filtered = [r for r in self.prediction_records 
                    if start <= r.timestamp.date() <= end and r.actual_value is not None]
        
        if not filtered:
            return {"total_predictions": 0, "mae": 0, "rmse": 0, "avg_confidence": 0}
        
        errors = [abs(r.predicted_value - r.actual_value) for r in filtered]
        squared_errors = [(r.predicted_value - r.actual_value)**2 for r in filtered]
        
        return {
            "total_predictions": len(filtered),
            "mae": round(np.mean(errors), 2),
            "rmse": round(np.sqrt(np.mean(squared_errors)), 2),
            "avg_confidence": round(np.mean([r.confidence for r in filtered]), 3)
        }

    def calculate_pump_statistics(self, start: date, end: date) -> Dict[str, Any]:
        """Calculate pump runtime and performance statistics."""
        filtered = [r for r in self.pump_records 
                    if start <= r.start_time.date() <= end]
        
        if not filtered:
            return {
                "total_runtime_seconds": 0,
                "total_runtime_hours": 0.0,
                "total_volume_liters": 0.0,
                "avg_runtime_seconds": 0.0,
                "number_of_cycles": 0,
            }
        
        total_runtime = sum(r.total_runtime_seconds for r in filtered)
        total_volume = sum(r.volume_pumped_liters for r in filtered)
        
        return {
            "total_runtime_seconds": total_runtime,
            "total_runtime_hours": round(total_runtime / 3600, 2),
            "total_volume_liters": round(total_volume, 2),
            "avg_runtime_seconds": round(np.mean([r.total_runtime_seconds for r in filtered]), 0),
            "number_of_cycles": len(filtered)
        }

    def calculate_battery_statistics(self, start: date, end: date) -> Dict[str, Any]:
        """Calculate battery health and performance statistics."""
        filtered = [r for r in self.battery_records 
                    if start <= r.timestamp.date() <= end]
        
        device_stats = defaultdict(list)
        for r in filtered:
            if r.percentage is not None:
                device_stats[r.device_id].append(r.percentage)
        
        results = {
            "devices": {},
            "overall_avg_percentage": None
        }
        
        all_percentages = []
        for device_id, percentages in device_stats.items():
            results["devices"][device_id] = {
                "avg_percentage": round(np.mean(percentages), 1),
                "min_percentage": round(min(percentages),1),
                "max_percentage": round(max(percentages),1)
            }
            all_percentages.extend(percentages)
        
        if all_percentages:
            results["overall_avg_percentage"] = round(np.mean(all_percentages),1)
        
        return results

    def calculate_sensor_health(self, start: date, end: date) -> Dict[str, Any]:
        """Calculate overall sensor health statistics."""
        filtered = [r for r in self.sensor_health_records 
                    if start <= r.timestamp.date() <= end]
        
        status_counts = defaultdict(int)
        for r in filtered:
            status_counts[r.status.name] +=1
        
        sensor_stats = defaultdict(lambda: {"healthy":0, "warning":0, "faulty":0, "offline":0})
        for r in filtered:
            key = r.status.name.lower()
            if key in sensor_stats[r.sensor_id]:
                sensor_stats[r.sensor_id][key] +=1
        
        return {
            "overall_status": dict(status_counts),
            "sensor_details": {k: dict(v) for k, v in sensor_stats.items()}
        }

    def calculate_crop_performance(self) -> Dict[str, Any]:
        """Calculate crop performance and growth metrics."""
        if not self.crop_records:
            return {
                "crop_type": "UNKNOWN",
                "days_since_planting": 0,
                "growth_stage": "UNKNOWN",
                "expected_yield_kg": None,
                "actual_yield_kg": None,
            }
        
        crop = self.crop_records[-1]
        
        days_since_planting = (date.today() - crop.planting_date).days
        
        return {
            "crop_type": crop.crop_type,
            "days_since_planting": days_since_planting,
            "growth_stage": crop.growth_stage.name,
            "expected_yield_kg": crop.expected_yield_kg,
            "actual_yield_kg": crop.actual_yield_kg
        }

    def calculate_weather_impact(self, start: date, end: date) -> Dict[str, Any]:
        """Analyze weather impact on irrigation needs."""
        filtered = [r for r in self.weather_records if start <= r.date <= end]
        
        if not filtered:
            return {
                "avg_temperature": 0.0,
                "avg_humidity": 0.0,
                "total_rainfall_mm": 0.0,
                "avg_eto_mm": 0.0,
                "days_with_rain": 0,
            }
        
        return {
            "avg_temperature": round(np.mean([r.temperature_c_avg for r in filtered]),1),
            "avg_humidity": round(np.mean([r.humidity_pct_avg for r in filtered]),1),
            "total_rainfall_mm": round(sum([r.rainfall_mm for r in filtered]),2),
            "avg_eto_mm": round(np.mean([r.eto_mm for r in filtered]),2),
            "days_with_rain": len([r for r in filtered if r.rainfall_mm >0])
        }

    def get_full_analytics_summary(self, start_date: Optional[date] = None, 
                                    end_date: Optional[date] = None,
                                    baseline_lpd: Optional[float] = 100.0) -> Dict[str, Any]:
        """Get a comprehensive analytics summary for a date range."""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        
        return {
            "period": {"start": str(start_date), "end": str(end_date)},
            "water_consumption": self.calculate_water_consumption(start_date, end_date),
            "water_savings": self.calculate_water_savings(start_date, end_date, baseline_lpd=baseline_lpd),
            "prediction_accuracy": self.calculate_prediction_accuracy(start_date, end_date),
            "pump_statistics": self.calculate_pump_statistics(start_date, end_date),
            "battery_statistics": self.calculate_battery_statistics(start_date, end_date),
            "sensor_health": self.calculate_sensor_health(start_date, end_date),
            "crop_performance": self.calculate_crop_performance(),
            "weather_impact": self.calculate_weather_impact(start_date, end_date)
        }

    def refresh_from_repositories(self) -> None:
        """Refresh analytics snapshots from the SQLite repositories when available."""
        if self.repository_registry is None:
            return
        try:
            from raspberry_pi.database.query_builder import SelectQuery
            sensor_rows = self.repository_registry.sensor_data.select(SelectQuery("SensorData").order_by("id DESC").limit(10000))
            pump_rows = self.repository_registry.pump_status.select(SelectQuery("PumpStatus").order_by("id DESC").limit(10000))
            prediction_rows = self.repository_registry.prediction_history.select(SelectQuery("PredictionHistory").order_by("id DESC").limit(10000))
            weather_rows = self.repository_registry.weather_history.select(SelectQuery("WeatherHistory").order_by("id DESC").limit(10000))
            alert_rows = self.repository_registry.alerts.select(SelectQuery("Alerts").order_by("id DESC").limit(10000))
        except Exception:
            logger.exception("Failed to refresh analytics from repositories")
            return

        self._sensor_rows = sensor_rows
        self._alert_rows = alert_rows
        self.water_records = []
        self.pump_records = []
        self.prediction_records = []
        self.battery_records = []
        self.weather_records = []

        for row in pump_rows:
            recorded = _parse_datetime(row.get("recorded_at")) or datetime.now()
            runtime = int(row.get("runtime_seconds") or 0)
            volume_liters = _extract_pump_volume_liters(row, runtime)
            self.pump_records.append(PumpRuntimeRecord(
                id=f"pump_{row.get('id')}",
                pump_id=str(row.get("device_id")),
                start_time=recorded,
                end_time=recorded + timedelta(seconds=runtime),
                total_runtime_seconds=runtime,
                volume_pumped_liters=volume_liters,
            ))
            if volume_liters > 0:
                self.water_records.append(WaterConsumptionRecord(
                    id=f"water_pump_{row.get('id')}",
                    timestamp=recorded,
                    volume_liters=volume_liters,
                    source="irrigation",
                    field_id="field_001",
                ))

        for row in prediction_rows:
            created = _parse_datetime(row.get("created_at")) or datetime.now()
            value = float(row.get("prediction_value") or 0.0)
            self.prediction_records.append(PredictionRecord(
                id=f"pred_{row.get('id')}",
                timestamp=created,
                prediction_type=row.get("prediction_type") or "soil_moisture",
                predicted_value=value,
                actual_value=None,
                confidence=float(row.get("confidence") or 0.0),
            ))

        for row in sensor_rows:
            recorded = _parse_datetime(row.get("recorded_at")) or datetime.now()
            if row.get("battery_percent") is not None:
                self.battery_records.append(BatteryRecord(
                    id=f"bat_{row.get('id')}",
                    device_id=str(row.get("device_id")),
                    timestamp=recorded,
                    percentage=float(row.get("battery_percent")),
                ))

        for row in weather_rows:
            recorded = _parse_datetime(row.get("recorded_at")) or datetime.now()
            self.weather_records.append(WeatherImpactRecord(
                id=f"weather_{row.get('id')}",
                date=recorded.date(),
                temperature_c_avg=float(row.get("temperature_c") or 0.0),
                humidity_pct_avg=float(row.get("humidity_percent") or 0.0),
                rainfall_mm=float(row.get("rainfall_mm") or 0.0),
                wind_speed_mps_avg=float(row.get("wind_speed_mps") or 0.0),
                solar_radiation_wm2_avg=0.0,
                eto_mm=0.0,
            ))

    def get_summary(self, period_days: int = 30) -> Dict[str, Any]:
        """Return dashboard summary metrics for the requested period."""
        self.refresh_from_repositories()
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=period_days)

        def _to_aware(dt):
            """Make a datetime timezone-aware (UTC) if it isn't already."""
            if dt is None:
                return None
            if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
                return dt
            return dt.replace(tzinfo=timezone.utc)

        water = self.calculate_water_consumption(start.date(), end.date())
        pump_events = [r for r in self.pump_records
                       if _to_aware(r.start_time) is not None
                       and start <= _to_aware(r.start_time) <= end]
        predictions = [r for r in self.prediction_records
                       if _to_aware(r.timestamp) is not None
                       and start <= _to_aware(r.timestamp) <= end]
        sensor_rows = getattr(self, "_sensor_rows", [])
        period_sensor_rows = [
            row for row in sensor_rows
            if _to_aware(_parse_datetime(row.get("recorded_at"))) is not None
            and start <= _to_aware(_parse_datetime(row.get("recorded_at"))) <= end
        ]
        moisture_values = [
            float(row.get("soil_moisture_percent"))
            for row in period_sensor_rows
            if row.get("soil_moisture_percent") is not None
        ]
        daily_moisture = defaultdict(list)
        for row in period_sensor_rows:
            recorded = _parse_datetime(row.get("recorded_at"))
            moisture = row.get("soil_moisture_percent")
            if recorded is not None and moisture is not None:
                daily_moisture[recorded.date()].append(float(moisture))
        stress_days = sum(
            1 for values in daily_moisture.values()
            if values and float(np.mean(values)) < 30.0
        )
        alert_rows = getattr(self, "_alert_rows", [])
        alerts = [
            row for row in alert_rows
            if _to_aware(_parse_datetime(row.get("created_at"))) is not None
            and start <= _to_aware(_parse_datetime(row.get("created_at"))) <= end
        ]
        return {
            "period_start": start,
            "period_end": end,
            "total_irrigation_events": len(pump_events),
            "total_water_used_liters": water.get("total_irrigation_liters", 0.0),
            "avg_soil_moisture_pct": round(float(np.mean(moisture_values)), 2) if moisture_values else 0.0,
            "crop_water_stress_days": stress_days,
            "ai_predictions_made": len(predictions),
            "alerts_generated": len(alerts),
        }

def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _extract_pump_volume_liters(row: Dict[str, Any], runtime_seconds: int) -> float:
    payload = _parse_json(row.get("payload_json"))
    direct_volume = _first_number(
        payload,
        ("volume_liters", "water_liters", "total_volume_liters", "volume_pumped_liters"),
    )
    if direct_volume is not None:
        return max(0.0, direct_volume)

    flow_lpm = _first_number(payload, ("flow_rate_lpm", "current_flow_rate_lpm"))
    if flow_lpm is not None and runtime_seconds > 0:
        return max(0.0, flow_lpm * runtime_seconds / 60.0)

    flow_lps = _first_number(payload, ("flow_rate_lps", "current_flow_rate_lps"))
    if flow_lps is not None and runtime_seconds > 0:
        return max(0.0, flow_lps * runtime_seconds)

    if runtime_seconds > 0:
        # Fallback to prototype-scale 0.05 L/s flow rate if no direct flow sensor data is found in payload
        return runtime_seconds * 0.05

    return 0.0


def _parse_json(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def _first_number(payload: Dict[str, Any], keys: tuple[str, ...]) -> Optional[float]:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None
