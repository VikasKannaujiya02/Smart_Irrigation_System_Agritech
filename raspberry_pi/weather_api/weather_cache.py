
"""Weather caching implementation with file-based offline cache."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from .weather_provider import WeatherForecast

logger = logging.getLogger(__name__)


class WeatherCache:
    """File-based weather cache with TTL (time-to-live) support."""

    def __init__(
        self,
        cache_dir: str = "data/weather_cache",
        cache_ttl_seconds: int = 1800  # 30 minutes
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.current_weather_file = self.cache_dir / "current_weather.json"
        self.forecast_file = self.cache_dir / "forecast.json"

    def save_current_weather(self, weather: WeatherForecast) -> None:
        """Save current weather data to cache file."""
        data = self._forecast_to_dict(weather)
        with open(self.current_weather_file, "w") as f:
            json.dump(data, f)
        logger.debug(f"Saved current weather to {self.current_weather_file}")

    def save_forecast(self, forecast: List[WeatherForecast]) -> None:
        """Save forecast data to cache file."""
        data = [self._forecast_to_dict(f) for f in forecast]
        with open(self.forecast_file, "w") as f:
            json.dump(data, f)
        logger.debug(f"Saved forecast to {self.forecast_file}")

    def get_current_weather(self) -> Optional[WeatherForecast]:
        """Get current weather from cache, if not expired."""
        if not self.current_weather_file.exists():
            return None
        file_mtime = datetime.fromtimestamp(self.current_weather_file.stat().st_mtime, tz=timezone.utc)
        if datetime.now(timezone.utc) - file_mtime > self.cache_ttl:
            logger.debug("Current weather cache expired")
            return None
        try:
            with open(self.current_weather_file, "r") as f:
                data = json.load(f)
            return self._dict_to_forecast(data)
        except Exception as e:
            logger.error(f"Failed to load cached current weather: {e}")
            return None

    def get_forecast(self) -> Optional[List[WeatherForecast]]:
        """Get forecast from cache, if not expired."""
        if not self.forecast_file.exists():
            return None
        file_mtime = datetime.fromtimestamp(self.forecast_file.stat().st_mtime, tz=timezone.utc)
        if datetime.now(timezone.utc) - file_mtime > self.cache_ttl:
            logger.debug("Forecast cache expired")
            return None
        try:
            with open(self.forecast_file, "r") as f:
                data_list = json.load(f)
            return [self._dict_to_forecast(d) for d in data_list]
        except Exception as e:
            logger.error(f"Failed to load cached forecast: {e}")
            return None

    def _forecast_to_dict(self, forecast: WeatherForecast) -> dict:
        """Convert WeatherForecast to serializable dict."""
        return {
            "timestamp": forecast.timestamp.isoformat(),
            "temperature": forecast.temperature,
            "humidity": forecast.humidity,
            "wind_speed": forecast.wind_speed,
            "rain_probability": forecast.rain_probability,
            "rain_volume": forecast.rain_volume
        }

    def _dict_to_forecast(self, data: dict) -> WeatherForecast:
        """Convert dict to WeatherForecast."""
        return WeatherForecast(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            temperature=data["temperature"],
            humidity=data["humidity"],
            wind_speed=data["wind_speed"],
            rain_probability=data["rain_probability"],
            rain_volume=data["rain_volume"]
        )
