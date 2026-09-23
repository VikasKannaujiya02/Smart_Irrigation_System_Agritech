
"""Weather provider abstract base class and concrete OpenWeatherMap implementation."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WeatherForecast:
    """Weather forecast data point."""
    timestamp: datetime
    temperature: Optional[float] = None  # Celsius
    humidity: Optional[float] = None  # Percent
    wind_speed: Optional[float] = None  # m/s
    rain_probability: Optional[float] = None  # Percent
    rain_volume: Optional[float] = None  # mm
    pressure_hpa: Optional[float] = None
    cloud_cover: Optional[float] = None  # Percent


class WeatherProvider(ABC):
    """Abstract base class for weather providers."""

    @abstractmethod
    def get_current_weather(self, latitude: float, longitude: float) -> Optional[WeatherForecast]:
        """Get current weather conditions."""
        pass

    @abstractmethod
    def get_forecast(self, latitude: float, longitude: float, hours: int = 48) -> List[WeatherForecast]:
        """Get weather forecast for specified number of hours."""
        pass


class OpenMeteoProvider(WeatherProvider):
    """Weather provider using Open-Meteo API (No API Key Required)."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.open-meteo.com/v1",
        timeout: int = 10,
        retries: int = 3,
        backoff_factor: float = 0.5
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        retry_strategy = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
        self.session.mount("http://", HTTPAdapter(max_retries=retry_strategy))

    def get_current_weather(self, latitude: float, longitude: float) -> Optional[WeatherForecast]:
        """Get current weather conditions from Open-Meteo."""
        try:
            url = f"{self.base_url}/forecast"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,surface_pressure,cloud_cover",
                "timezone": "auto"
            }
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            curr = data.get("current", {})
            return WeatherForecast(
                timestamp=datetime.now(timezone.utc),
                temperature=curr.get("temperature_2m"),
                humidity=curr.get("relative_humidity_2m"),
                wind_speed=curr.get("wind_speed_10m"),
                rain_volume=curr.get("precipitation"),
                pressure_hpa=curr.get("surface_pressure"),
                cloud_cover=curr.get("cloud_cover")
            )
        except Exception as e:
            logger.error(f"Failed to get current weather from Open-Meteo: {e}")
            return None

    def get_forecast(self, latitude: float, longitude: float, hours: int = 48) -> List[WeatherForecast]:
        """Get weather hourly forecast from Open-Meteo."""
        forecasts: List[WeatherForecast] = []
        try:
            url = f"{self.base_url}/forecast"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,wind_speed_10m,surface_pressure,cloud_cover",
                "timezone": "auto",
                "forecast_hours": min(hours, 168)
            }
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            
            for i, ts_str in enumerate(times):
                ts = datetime.fromisoformat(ts_str.replace("T", " ") + "+00:00")
                forecasts.append(
                    WeatherForecast(
                        timestamp=ts,
                        temperature=hourly.get("temperature_2m", [])[i],
                        humidity=hourly.get("relative_humidity_2m", [])[i],
                        wind_speed=hourly.get("wind_speed_10m", [])[i],
                        rain_probability=hourly.get("precipitation_probability", [])[i],
                        rain_volume=hourly.get("precipitation", [])[i],
                        pressure_hpa=hourly.get("surface_pressure", [])[i],
                        cloud_cover=hourly.get("cloud_cover", [])[i]
                    )
                )
        except Exception as e:
            logger.error(f"Failed to get forecast from Open-Meteo: {e}")
            
        return forecasts

    def get_daily_forecast(self, latitude: float, longitude: float, days: int = 7) -> List[WeatherForecast]:
        """Get daily forecast using Open-Meteo."""
        forecasts: List[WeatherForecast] = []
        try:
            url = f"{self.base_url}/forecast"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max",
                "timezone": "auto",
                "forecast_days": min(days, 16)
            }
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            daily = data.get("daily", {})
            times = daily.get("time", [])

            for i, ts_str in enumerate(times):
                ts = datetime.fromisoformat(ts_str.replace("T", " ") + "+00:00")
                forecasts.append(
                    WeatherForecast(
                        timestamp=ts,
                        temperature=daily.get("temperature_2m_max", [])[i],
                        # OpenMeteo daily doesn't have humidity directly without specific request, skip or approximate
                        wind_speed=daily.get("wind_speed_10m_max", [])[i],
                        rain_probability=daily.get("precipitation_probability_max", [])[i],
                        rain_volume=daily.get("precipitation_sum", [])[i],
                    )
                )
        except Exception as e:
            logger.info("Daily forecast unavailable, using hourly fallback: %s", e)

        return forecasts

    @staticmethod
    def _rain_volume(data: dict) -> Optional[float]:
        rain = data.get("rain") or {}
        if "1h" in rain:
            return rain["1h"]
        if "3h" in rain:
            return rain["3h"]
        return None
