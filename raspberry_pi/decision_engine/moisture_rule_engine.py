"""Moisture Rule Engine for decision making based on soil moisture levels."""

from __future__ import annotations

import logging


from .models import (
    SensorData,
    CropConfig,
    SystemConfig,
    RuleResult,
    IrrigationDecision,
    SensorStatus,
)

logger = logging.getLogger(__name__)


class MoistureRuleEngine:
    """Rule engine that makes irrigation decisions based on soil moisture levels."""

    def __init__(
        self,
        crop_config: CropConfig,
        system_config: SystemConfig,
    ):
        """Initialize moisture rule engine.
        
        Args:
            crop_config: Crop-specific configuration
            system_config: System-wide configuration
        """
        self.crop_config = crop_config
        self.system_config = system_config

    def evaluate(
        self,
        sensor_data: SensorData,
    ) -> RuleResult:
        """Evaluate moisture rules and return a decision.
        
        Args:
            sensor_data: Current sensor data
            
        Returns:
            RuleResult with decision and reasoning
        """
        logger.info("Evaluating moisture rules")

        # Handle faulty sensor
        if sensor_data.sensor_status == SensorStatus.FAULTY:
            logger.warning("Sensor is faulty, ignoring moisture data")
            return RuleResult(
                engine_name="MoistureRuleEngine",
                decision=IrrigationDecision.DO_NOT_IRRIGATE,
                confidence=0.5,
                reason="Sensor is faulty - moisture data ignored",
                details={"sensor_status": sensor_data.sensor_status.name},
            )

        # If no moisture data, can't make a decision
        if sensor_data.soil_moisture_percent is None:
            return RuleResult(
                engine_name="MoistureRuleEngine",
                decision=IrrigationDecision.DO_NOT_IRRIGATE,
                confidence=0.3,
                reason="No soil moisture data available",
                details={},
            )

        moisture = sensor_data.soil_moisture_percent

        # Emergency case first
        if moisture < self.system_config.emergency_moisture_threshold:
            return RuleResult(
                engine_name="MoistureRuleEngine",
                decision=IrrigationDecision.EMERGENCY_IRRIGATE,
                confidence=1.0,
                reason=(
                    f"Soil moisture ({moisture:.1f}%) below emergency threshold "
                    f"({self.system_config.emergency_moisture_threshold:.1f}%)"
                ),
                details={
                    "moisture": moisture,
                    "threshold": self.system_config.emergency_moisture_threshold,
                },
            )

        # Need to irrigate now
        if moisture < self.crop_config.min_soil_moisture:
            return RuleResult(
                engine_name="MoistureRuleEngine",
                decision=IrrigationDecision.IRRIGATE_NOW,
                confidence=0.9,
                reason=(
                    f"Soil moisture ({moisture:.1f}%) below minimum threshold "
                    f"({self.crop_config.min_soil_moisture:.1f}%)"
                ),
                details={
                    "moisture": moisture,
                    "min_threshold": self.crop_config.min_soil_moisture,
                },
            )

        # Moisture is good, no immediate need
        if self.crop_config.min_soil_moisture <= moisture <= self.crop_config.max_soil_moisture:
            return RuleResult(
                engine_name="MoistureRuleEngine",
                decision=IrrigationDecision.DO_NOT_IRRIGATE,
                confidence=0.85,
                reason=(
                    f"Soil moisture ({moisture:.1f}%) within ideal range "
                    f"({self.crop_config.min_soil_moisture:.1f}% - {self.crop_config.max_soil_moisture:.1f}%)"
                ),
                details={
                    "moisture": moisture,
                    "ideal_min": self.crop_config.min_soil_moisture,
                    "ideal_max": self.crop_config.max_soil_moisture,
                },
            )

        # Moisture is too high
        if moisture > self.crop_config.max_soil_moisture:
            return RuleResult(
                engine_name="MoistureRuleEngine",
                decision=IrrigationDecision.DO_NOT_IRRIGATE,
                confidence=0.95,
                reason=(
                    f"Soil moisture ({moisture:.1f}%) above maximum threshold "
                    f"({self.crop_config.max_soil_moisture:.1f}%)"
                ),
                details={
                    "moisture": moisture,
                    "max_threshold": self.crop_config.max_soil_moisture,
                },
            )

        # Default decision
        return RuleResult(
            engine_name="MoistureRuleEngine",
            decision=IrrigationDecision.DO_NOT_IRRIGATE,
            confidence=0.5,
            reason=f"Unclear moisture condition: {moisture:.1f}%",
            details={"moisture": moisture},
        )
