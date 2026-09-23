
"""Rain prediction and irrigation recommendation logic."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from .weather_provider import WeatherForecast

logger = logging.getLogger(__name__)


@dataclass
class RainPrediction:
    """Rain prediction result."""
    will_rain: bool
    rain_probability: float
    rain_volume: float
    rain_time_window_start: Optional[datetime]
    rain_time_window_end: Optional[datetime]


@dataclass
class IrrigationRecommendation:
    """Irrigation recommendation based on weather and soil conditions."""
    should_irrigate: bool
    reason: str
    rain_prediction: Optional[RainPrediction] = None


class RainPredictor:
    """Class for analyzing rain forecasts and making irrigation recommendations."""

    def __init__(
        self,
        rain_threshold_probability: float = 50.0,  # Percent
        rain_threshold_volume: float = 2.0,  # mm
        rain_time_window_hours: int = 24,
        critical_soil_moisture_threshold: float = 20.0  # Percent
    ):
        self.rain_threshold_probability = rain_threshold_probability
        self.rain_threshold_volume = rain_threshold_volume
        self.rain_time_window = timedelta(hours=rain_time_window_hours)
        self.critical_soil_moisture = critical_soil_moisture_threshold

    def predict_rain(
        self,
        forecast: List[WeatherForecast]
    ) -> RainPrediction:
        """Analyze forecast to predict rain within the configured window."""
        now = datetime.now(timezone.utc)
        window_end = now + self.rain_time_window
        relevant_forecasts = [
            f for f in forecast if now <= f.timestamp <= window_end
        ]

        if not relevant_forecasts:
            logger.debug("No relevant forecast data for rain prediction")
            return RainPrediction(
                will_rain=False,
                rain_probability=0.0,
                rain_volume=0.0,
                rain_time_window_start=None,
                rain_time_window_end=None
            )

        max_probability = 0.0
        total_volume = 0.0
        rain_start: Optional[datetime] = None
        rain_end: Optional[datetime] = None

        for f in relevant_forecasts:
            if f.rain_probability is not None and f.rain_probability > max_probability:
                max_probability = f.rain_probability
            if f.rain_volume is not None:
                total_volume += f.rain_volume
            if f.rain_probability is not None and f.rain_probability >= self.rain_threshold_probability:
                if rain_start is None:
                    rain_start = f.timestamp
                rain_end = f.timestamp

        will_rain = (
            max_probability >= self.rain_threshold_probability and
            total_volume >= self.rain_threshold_volume
        )

        return RainPrediction(
            will_rain=will_rain,
            rain_probability=max_probability,
            rain_volume=total_volume,
            rain_time_window_start=rain_start,
            rain_time_window_end=rain_end
        )

    def get_irrigation_recommendation(
        self,
        forecast: List[WeatherForecast],
        current_soil_moisture: Optional[float] = None
    ) -> IrrigationRecommendation:
        """Get irrigation recommendation based on rain forecast and soil moisture."""
        rain_prediction = self.predict_rain(forecast)

        if rain_prediction.will_rain:
            # If rain is predicted
            if current_soil_moisture is None:
                return IrrigationRecommendation(
                    should_irrigate=False,
                    reason="Rain is predicted; soil moisture data not available to confirm critical level.",
                    rain_prediction=rain_prediction
                )
            if current_soil_moisture < self.critical_soil_moisture:
                return IrrigationRecommendation(
                    should_irrigate=True,
                    reason=f"Rain is predicted but soil moisture ({current_soil_moisture:.1f}%) is below critical threshold ({self.critical_soil_moisture:.1f}%).",
                    rain_prediction=rain_prediction
                )
            else:
                return IrrigationRecommendation(
                    should_irrigate=False,
                    reason=f"Rain is predicted and soil moisture ({current_soil_moisture:.1f}%) is sufficient.",
                    rain_prediction=rain_prediction
                )
        else:
            # No rain predicted
            return IrrigationRecommendation(
                should_irrigate=True,
                reason="No significant rain predicted in the configured time window.",
                rain_prediction=rain_prediction
            )
