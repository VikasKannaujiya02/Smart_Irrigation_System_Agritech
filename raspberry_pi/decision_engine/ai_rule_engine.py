"""AI Rule Engine for decision making based on AI predictions."""

from __future__ import annotations

import logging

from .models import (
    AIPrediction,
    SystemConfig,
    RuleResult,
    IrrigationDecision,
)

logger = logging.getLogger(__name__)


class AIRuleEngine:
    """Rule engine that makes irrigation decisions based on AI model predictions."""

    def __init__(
        self,
        system_config: SystemConfig,
    ):
        """Initialize AI rule engine.
        
        Args:
            system_config: System-wide configuration
        """
        self.system_config = system_config

    def evaluate(
        self,
        ai_prediction: AIPrediction,
    ) -> RuleResult:
        """Evaluate AI rules and return a decision.
        
        Args:
            ai_prediction: Current AI prediction data
            
        Returns:
            RuleResult with decision and reasoning
        """
        logger.info("Evaluating AI rules")

        # Check if confidence is too low to use AI
        if ai_prediction.confidence < self.system_config.ai_confidence_threshold:
            return RuleResult(
                engine_name="AIRuleEngine",
                decision=IrrigationDecision.DO_NOT_IRRIGATE,
                confidence=0.0,
                reason=f"AI confidence ({ai_prediction.confidence:.2f}) below threshold ({self.system_config.ai_confidence_threshold:.2f}) - switch to rule-based",
                details={
                    "ai_confidence": ai_prediction.confidence,
                    "threshold": self.system_config.ai_confidence_threshold,
                    "used_fallback": ai_prediction.used_fallback,
                },
            )

        # If irrigation need score is high enough
        if ai_prediction.irrigation_need_score is not None and ai_prediction.irrigation_need_score > 0.7:
            return RuleResult(
                engine_name="AIRuleEngine",
                decision=IrrigationDecision.IRRIGATE_NOW,
                confidence=ai_prediction.confidence,
                reason=f"AI predicts high irrigation need (score: {ai_prediction.irrigation_need_score:.2f})",
                details={
                    "irrigation_need_score": ai_prediction.irrigation_need_score,
                    "soil_moisture_predicted": ai_prediction.soil_moisture_predicted,
                    "water_requirement_liters": ai_prediction.water_requirement_liters,
                    "confidence": ai_prediction.confidence,
                },
            )

        # If soil moisture is predicted to drop below threshold
        if ai_prediction.soil_moisture_predicted is not None and ai_prediction.soil_moisture_predicted < 30:
            return RuleResult(
                engine_name="AIRuleEngine",
                decision=IrrigationDecision.IRRIGATE_NOW,
                confidence=ai_prediction.confidence,
                reason=f"AI predicts low soil moisture ({ai_prediction.soil_moisture_predicted:.1f}%) soon",
                details={
                    "soil_moisture_predicted": ai_prediction.soil_moisture_predicted,
                    "confidence": ai_prediction.confidence,
                },
            )

        # No urgent AI recommendation
        return RuleResult(
            engine_name="AIRuleEngine",
            decision=IrrigationDecision.DO_NOT_IRRIGATE,
            confidence=ai_prediction.confidence,
            reason="AI does not recommend immediate irrigation",
            details={
                "soil_moisture_predicted": ai_prediction.soil_moisture_predicted,
                "irrigation_need_score": ai_prediction.irrigation_need_score,
                "water_requirement_liters": ai_prediction.water_requirement_liters,
                "confidence": ai_prediction.confidence,
            },
        )
