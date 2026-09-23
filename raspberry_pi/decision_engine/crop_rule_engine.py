"""Crop Rule Engine for decision making based on crop-specific requirements."""

from __future__ import annotations

import logging
from datetime import datetime

from .models import (
    CropConfig,
    SensorData,
    NPKData,
    WeatherData,
    RuleResult,
    IrrigationDecision,
)

logger = logging.getLogger(__name__)


class CropRuleEngine:
    """Rule engine that makes irrigation decisions based on crop requirements."""

    def __init__(
        self,
        crop_config: CropConfig,
    ):
        """Initialize crop rule engine.
        
        Args:
            crop_config: Crop-specific configuration
        """
        self.crop_config = crop_config

    def evaluate(
        self,
        sensor_data: SensorData,
        npk_data: NPKData,
        weather_data: WeatherData,
    ) -> RuleResult:
        """Evaluate crop rules and return a decision.
        
        Args:
            sensor_data: Current sensor data
            npk_data: Current NPK data
            weather_data: Current weather data
            
        Returns:
            RuleResult with decision and reasoning
        """
        logger.info("Evaluating crop rules")
        reasons: list[str] = []
        details: dict = {}

        # Check if current time is in preferred irrigation time
        now = datetime.now()
        current_hour = now.hour
        is_preferred_time = current_hour in self.crop_config.preferred_irrigation_time_hours
        details["preferred_irrigation_time"] = is_preferred_time
        details["current_hour"] = current_hour

        if is_preferred_time:
            reasons.append("Current time is in preferred irrigation window")

        # Check NPK levels if available
        if npk_data.nitrogen_mg_kg is not None:
            details["nitrogen_mg_kg"] = npk_data.nitrogen_mg_kg
        if npk_data.ph is not None:
            details["ph"] = npk_data.ph
            if npk_data.ph < 5.0 or npk_data.ph > 7.5:
                reasons.append(f"Soil pH ({npk_data.ph:.1f}) outside ideal range")

        # No direct crop-based irrigation decision - just contextual info
        return RuleResult(
            engine_name="CropRuleEngine",
            decision=IrrigationDecision.DO_NOT_IRRIGATE,
            confidence=0.3,
            reason="; ".join(reasons) if reasons else "Crop requirements evaluated, no immediate decision",
            details=details,
        )
