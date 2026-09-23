"""Irrigation Scheduler determines optimal times to schedule irrigation."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from .models import (
    CropConfig,
    WeatherData,
    SensorData,
)

logger = logging.getLogger(__name__)


class IrrigationScheduler:
    """Schedules irrigation events based on crop preferences and weather."""

    def __init__(
        self,
        crop_config: CropConfig,
    ):
        """Initialize irrigation scheduler.
        
        Args:
            crop_config: Crop-specific configuration
        """
        self.crop_config = crop_config

    def find_next_irrigation_time(
        self,
        weather_data: WeatherData,
        sensor_data: SensorData,
    ) -> Optional[datetime]:
        """Find the next best time to irrigate.
        
        Args:
            weather_data: Current weather data
            sensor_data: Current sensor data
            
        Returns:
            Optimal irrigation time or None
        """
        logger.info("Finding next irrigation time")
        
        now = datetime.now()
        
        # Check preferred times first
        preferred_hours = self.crop_config.preferred_irrigation_time_hours
        next_time: Optional[datetime] = None
        
        for hour in preferred_hours:
            candidate = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if candidate > now:
                next_time = candidate
                break
        
        if next_time:
            logger.info(f"Next preferred irrigation time: {next_time}")
            return next_time
        
        # If no preferred time soon, check next day
        for hour in preferred_hours:
            candidate = (now + timedelta(days=1)).replace(hour=hour, minute=0, second=0, microsecond=0)
            next_time = candidate
            break
        
        logger.info(f"Next irrigation time scheduled: {next_time}")
        return next_time
