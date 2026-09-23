
"""Weather API module for AI Smart Irrigation Digital Twin."""

from .weather_provider import (
    WeatherProvider,
    OpenMeteoProvider,
    WeatherForecast
)
from .weather_cache import WeatherCache
from .rain_prediction import (
    RainPredictor,
    RainPrediction,
    IrrigationRecommendation
)
from .forecast_manager import ForecastManager
from .weather_service import WeatherService

__all__ = [
    "WeatherProvider",
    "OpenMeteoProvider",
    "WeatherForecast",
    "WeatherCache",
    "RainPredictor",
    "RainPrediction",
    "IrrigationRecommendation",
    "ForecastManager",
    "WeatherService"
]
