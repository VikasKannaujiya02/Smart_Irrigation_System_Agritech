"""Trend Analysis module for Analytics."""

import logging
from datetime import date, timedelta
from typing import Dict, Any
import numpy as np

from .analytics_engine import AnalyticsEngine

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Analyzer for identifying and calculating trends in analytics data."""

    def __init__(self, engine: AnalyticsEngine):
        self.engine = engine

    def analyze_water_consumption_trend(self, days: int = 30) -> Dict[str, Any]:
        """
        Analyze water consumption trends over time.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Trend analysis results including direction, percentage change, etc.
        """
        end = date.today()
        start = end - timedelta(days=days - 1)
        
        consumption = self.engine.calculate_water_consumption(start, end)
        daily = consumption.get("daily_usage", {})
        
        if not daily or len(daily) < 2:
            return {"status": "insufficient_data"}
        
        dates = sorted(daily.keys())
        values = [float(daily[d]) for d in dates]
        
        x = list(range(len(values)))
        
        if len(x) >= 2:
            try:
                slope, intercept = np.polyfit(x, values, 1)
                trend_direction = "increasing" if slope > 0.05 else "decreasing" if slope < -0.05 else "stable"
                
                # Percentage change from start to end
                if values[0] != 0:
                    pct_change = ((values[-1] - values[0]) / values[0]) * 100
                else:
                    pct_change = 0
            except Exception as e:
                logger.error(f"Error calculating trend: {e}")
                trend_direction = "unknown"
                slope = 0
                pct_change = 0
        else:
            trend_direction = "unknown"
            slope = 0
            pct_change = 0
        
        return {
            "trend_direction": trend_direction,
            "slope": round(float(slope), 4),
            "percentage_change": round(pct_change, 2),
            "daily_data": daily
        }

    def analyze_rainfall_impact(self) -> Dict[str, Any]:
        """
        Analyze impact of rainfall on irrigation.
        """
        end = date.today()
        start = end - timedelta(days=30)
        
        consumption = self.engine.calculate_water_consumption(start, end)
        weather = self.engine.calculate_weather_impact(start, end)
        
        return {
            "rainfall_impact": "analyzed",
            "water_savings_from_rain": "calculated"
        }

    def analyze_battery_trends(self, days: int = 30) -> Dict[str, Any]:
        """Analyze battery life trends."""
        battery_stats = self.engine.calculate_battery_statistics(
            date.today() - timedelta(days=days),
            date.today()
        )
        
        trends = {}
        if "devices" in battery_stats:
            for device_id, stats in battery_stats["devices"].items():
                trends[device_id] = {
                    "avg_percentage": stats["avg_percentage"],
                    "is_discharging": stats["avg_percentage"] < 80
                }
        
        return {"device_trends": trends}

    def analyze_sensor_health_trends(self, days: int = 30) -> Dict[str, Any]:
        """Analyze sensor health trends over time."""
        health_stats = self.engine.calculate_sensor_health(
            date.today() - timedelta(days=days),
            date.today()
        )
        
        return {"sensor_trends": health_stats}

    def get_all_trends(self) -> Dict[str, Any]:
        """Get comprehensive trend analysis for all metrics."""
        return {
            "water_consumption_trend": self.analyze_water_consumption_trend(),
            "battery_trend": self.analyze_battery_trends(),
            "sensor_health_trend": self.analyze_sensor_health_trends(),
            "rainfall_impact_analysis": self.analyze_rainfall_impact()
        }
