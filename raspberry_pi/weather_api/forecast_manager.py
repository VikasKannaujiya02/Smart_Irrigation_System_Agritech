
"""Weather forecast manager that integrates provider and cache."""

from __future__ import annotations

import logging
from typing import List, Optional

from .weather_cache import WeatherCache
from .weather_provider import WeatherForecast, WeatherProvider

logger = logging.getLogger(__name__)


class ForecastManager:
    """Manages weather forecast retrieval, caching, and validation."""

    def __init__(
        self,
        provider: WeatherProvider,
        cache: WeatherCache,
        latitude: float,
        longitude: float
    ):
        self.provider = provider
        self.cache = cache
        self.latitude = latitude
        self.longitude = longitude

    def get_current_weather(self, use_cache: bool = True) -> Optional[WeatherForecast]:
        """Get current weather, using cache if available and not expired."""
        if use_cache:
            cached = self.cache.get_current_weather()
            if cached:
                logger.debug("Using cached current weather")
                return cached
        logger.debug("Fetching current weather from provider")
        weather = self.provider.get_current_weather(self.latitude, self.longitude)
        if weather:
            self.cache.save_current_weather(weather)
        return weather

    def get_forecast(self, use_cache: bool = True, hours: int = 48) -> Optional[List[WeatherForecast]]:
        """Get weather forecast, using cache if available and not expired."""
        if use_cache:
            cached = self.cache.get_forecast()
            if cached and self._is_forecast_valid(cached):
                logger.debug("Using cached forecast")
                return cached
        logger.debug("Fetching forecast from provider")
        forecast = self.provider.get_forecast(self.latitude, self.longitude, hours)
        if forecast and self._is_forecast_valid(forecast):
            self.cache.save_forecast(forecast)
        return forecast

    def _is_forecast_valid(self, forecast: List[WeatherForecast]) -> bool:
        """Validate forecast data."""
        if not forecast:
            return False
        # Check that forecast covers at least some future time
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        has_future = any(f.timestamp > now for f in forecast)
        if not has_future:
            logger.debug("Forecast has no future data points")
            return False
        # Check that data points are in order
        for i in range(1, len(forecast)):
            if forecast[i].timestamp <= forecast[i-1].timestamp:
                logger.debug("Forecast data points are out of order")
                return False
        return True
