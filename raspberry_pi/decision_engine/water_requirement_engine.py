"""Water Requirement Engine calculates irrigation duration and volume."""

from __future__ import annotations

import logging
from typing import Optional

from .models import (
    SensorData,
    WeatherData,
    CropConfig,
    AIPrediction,
)

logger = logging.getLogger(__name__)


class WaterRequirementEngine:
    """Calculates required water and irrigation duration."""

    def __init__(
        self,
        crop_config: CropConfig,
    ):
        """Initialize water requirement engine.
        
        Args:
            crop_config: Crop-specific configuration
        """
        self.crop_config = crop_config
        # Default irrigation efficiency estimate (liters per minute)
        self.pump_flow_rate_liters_per_min: float = 10.0
        self.target_moisture: float = crop_config.ideal_soil_moisture

    def calculate_water_requirement(
        self,
        sensor_data: SensorData,
        weather_data: WeatherData,
        ai_prediction: Optional[AIPrediction] = None,
    ) -> dict:
        """Calculate required water volume and duration.
        
        Args:
            sensor_data: Current sensor data
            weather_data: Current weather data
            ai_prediction: AI prediction data (optional)
            
        Returns:
            Dict with water volume liters and duration seconds
        """
        logger.info("Calculating water requirement")
        
        if sensor_data.soil_moisture_percent is None:
            return {"water_liters": 0.0, "duration_seconds": 0}

        current_moisture = sensor_data.soil_moisture_percent

        if current_moisture >= self.target_moisture:
            return {"water_liters": 0.0, "duration_seconds": 0}

        # Calculate deficit (percentage points)
        deficit = self.target_moisture - current_moisture
        logger.debug(f"Soil moisture deficit: {deficit:.1f}%")
        
        # Simple calculation based on deficit
        # Assume 1% deficit = 5 liters per 100 sqm (example)
        # Adjust for crop type, but keep simple for now
        water_liters = deficit * 2.0

        # Cap at reasonable max
        water_liters = min(water_liters, 100.0)

        # If we have an AI prediction, use that
        if ai_prediction and ai_prediction.water_requirement_liters:
            water_liters = ai_prediction.water_requirement_liters

        # Adjust for weather: if it's hot/dry, add 10% more
        if weather_data.temperature_c is not None and weather_data.temperature_c > 30:
            water_liters *= 1.1
        if weather_data.humidity_percent is not None and weather_data.humidity_percent < 30:
            water_liters *= 1.1

        duration_minutes = water_liters / self.pump_flow_rate_liters_per_min
        duration_seconds = duration_minutes * 60

        logger.info(f"Water requirement: {water_liters:.1f}L, {duration_seconds:.0f}s")

        return {
            "water_liters": water_liters,
            "duration_seconds": duration_seconds,
        }
