
"""Main weather service class that ties all components together."""

from __future__ import annotations

import logging
from typing import Optional

import yaml

from .forecast_manager import ForecastManager
from .rain_prediction import IrrigationRecommendation, RainPredictor
from .weather_cache import WeatherCache
from .weather_provider import WeatherForecast, OpenMeteoProvider

logger = logging.getLogger(__name__)


class WeatherService:
    """Main weather service for irrigation system."""

    def __init__(
        self,
        forecast_manager: ForecastManager,
        rain_predictor: RainPredictor
    ):
        self.forecast_manager = forecast_manager
        self.rain_predictor = rain_predictor

    @classmethod
    def from_config(cls, config_path: str = "configs/system.yaml") -> "WeatherService":
        """Create WeatherService instance from config file."""
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        weather_config = config.get("weather", {})
        
        provider = OpenMeteoProvider(
            api_key=weather_config.get("api_key", ""),
            base_url=weather_config.get("base_url", "https://api.open-meteo.com/v1"),
            timeout=weather_config.get("timeout_seconds", 10),
            retries=weather_config.get("retries", 3)
        )
        
        cache = WeatherCache(
            cache_dir=weather_config.get("cache_dir", "data/weather_cache"),
            cache_ttl_seconds=weather_config.get("cache_ttl_seconds", 1800)
        )
        
        forecast_manager = ForecastManager(
            provider=provider,
            cache=cache,
            latitude=weather_config.get("latitude", 0.0),
            longitude=weather_config.get("longitude", 0.0)
        )
        
        rain_predictor = RainPredictor(
            rain_threshold_probability=weather_config.get("rain_threshold_probability", 50.0),
            rain_threshold_volume=weather_config.get("rain_threshold_volume", 2.0),
            rain_time_window_hours=weather_config.get("rain_time_window_hours", 24),
            critical_soil_moisture_threshold=weather_config.get("critical_soil_moisture_threshold", 20.0)
        )
        
        return cls(forecast_manager, rain_predictor)

    def get_current_weather(self, use_cache: bool = True) -> Optional[WeatherForecast]:
        """Get current weather conditions."""
        return self.forecast_manager.get_current_weather(use_cache)

    def get_forecast(self, use_cache: bool = True, hours: int = 48):
        """Get weather forecast."""
        return self.forecast_manager.get_forecast(use_cache, hours)

    def get_daily_forecast(self, days: int = 7):
        """Get daily weather forecast directly from the configured provider."""
        return self.forecast_manager.provider.get_daily_forecast(
            self.forecast_manager.latitude,
            self.forecast_manager.longitude,
            days=days,
        )

    def get_irrigation_recommendation(
        self,
        current_soil_moisture: Optional[float] = None
    ) -> Optional[IrrigationRecommendation]:
        """Get irrigation recommendation based on forecast and soil moisture."""
        forecast = self.get_forecast(use_cache=True)
        if not forecast:
            logger.error("No forecast data available for irrigation recommendation")
            return None
        return self.rain_predictor.get_irrigation_recommendation(
            forecast=forecast,
            current_soil_moisture=current_soil_moisture
        )
