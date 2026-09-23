"""Weather Rule Engine for decision making based on weather conditions."""

from __future__ import annotations

import logging

from .models import (
    WeatherData,
    SystemConfig,
    RuleResult,
    IrrigationDecision,
)

logger = logging.getLogger(__name__)


class WeatherRuleEngine:
    """Rule engine that makes irrigation decisions based on weather data."""

    def __init__(
        self,
        system_config: SystemConfig,
    ):
        """Initialize weather rule engine.
        
        Args:
            system_config: System-wide configuration
        """
        self.system_config = system_config

    def evaluate(
        self,
        weather_data: WeatherData,
    ) -> RuleResult:
        """Evaluate weather rules and return a decision.
        
        Args:
            weather_data: Current weather data
            
        Returns:
            RuleResult with decision and reasoning
        """
        logger.info("Evaluating weather rules")

        # Rule 1: If rain is expected soon, don't irrigate
        if weather_data.rain_expected_24h:
            return RuleResult(
                engine_name="WeatherRuleEngine",
                decision=IrrigationDecision.DO_NOT_IRRIGATE,
                confidence=0.9,
                reason="Rain expected within 24 hours, delaying irrigation",
                details={
                    "rain_expected_24h": True,
                    "rainfall_mm": weather_data.rainfall_mm,
                },
            )

        # Rule 2: If it's already raining, definitely don't irrigate
        if weather_data.rainfall_mm is not None and weather_data.rainfall_mm > 0:
            return RuleResult(
                engine_name="WeatherRuleEngine",
                decision=IrrigationDecision.DO_NOT_IRRIGATE,
                confidence=0.98,
                reason=f"Currently raining ({weather_data.rainfall_mm:.1f}mm)",
                details={"rainfall_mm": weather_data.rainfall_mm},
            )

        # Rule 3: High humidity may reduce need
        if (weather_data.humidity_percent is not None and weather_data.humidity_percent > 90):
            return RuleResult(
                engine_name="WeatherRuleEngine",
                decision=IrrigationDecision.DO_NOT_IRRIGATE,
                confidence=0.6,
                reason=f"Very high humidity ({weather_data.humidity_percent:.1f}%) may reduce water need",
                details={"humidity_percent": weather_data.humidity_percent},
            )

        # No weather-based restrictions
        return RuleResult(
            engine_name="WeatherRuleEngine",
            decision=IrrigationDecision.DO_NOT_IRRIGATE,
            confidence=0.3,
            reason="No weather conditions that require or prevent irrigation",
            details={
                "temperature_c": weather_data.temperature_c,
                "humidity_percent": weather_data.humidity_percent,
                "rainfall_mm": weather_data.rainfall_mm,
            },
        )
