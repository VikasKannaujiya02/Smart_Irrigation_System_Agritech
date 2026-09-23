"""Main Decision Engine orchestrator that combines all rule engines and makes final decisions."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from .models import (
    SensorData,
    NPKData,
    WeatherData,
    AIPrediction,
    TankStatus,
    PumpStatus,
    CropConfig,
    SystemConfig,
    RuleResult,
    IrrigationAction,
    IrrigationDecision,
    PumpCommand,
    IrrigationMode,
)
from .moisture_rule_engine import MoistureRuleEngine
from .weather_rule_engine import WeatherRuleEngine
from .ai_rule_engine import AIRuleEngine
from .crop_rule_engine import CropRuleEngine
from .water_requirement_engine import WaterRequirementEngine
from .irrigation_scheduler import IrrigationScheduler
from .pump_controller_logic import PumpControllerLogic
from ..safety_layer import (
    FailsafeManager,
    SafetyOverride
)

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Main decision engine that orchestrates all rule engines and makes final irrigation decisions."""

    def __init__(
        self,
        crop_config: Optional[CropConfig] = None,
        system_config: Optional[SystemConfig] = None,
        failsafe_manager: Optional[FailsafeManager] = None,
    ):
        """Initialize decision engine.
        
        Args:
            crop_config: Crop-specific configuration
            system_config: System-wide configuration
            failsafe_manager: Failsafe manager for safety checks
        """
        self.crop_config = crop_config or CropConfig()
        self.system_config = system_config or SystemConfig()
        self.failsafe_manager = failsafe_manager or FailsafeManager()
        
        # Initialize all rule engines
        self.moisture_engine = MoistureRuleEngine(self.crop_config, self.system_config)
        self.weather_engine = WeatherRuleEngine(self.system_config)
        self.ai_engine = AIRuleEngine(self.system_config)
        self.crop_engine = CropRuleEngine(self.crop_config)
        self.water_engine = WaterRequirementEngine(self.crop_config)
        self.scheduler = IrrigationScheduler(self.crop_config)
        self.pump_logic = PumpControllerLogic(self.system_config)
        
        logger.info("Decision Engine initialized")

    def evaluate(
        self,
        sensor_data: SensorData,
        npk_data: NPKData,
        weather_data: WeatherData,
        ai_prediction: AIPrediction,
        tank_status: TankStatus,
        pump_status: PumpStatus,
    ) -> IrrigationAction:
        """Evaluate all inputs and make an irrigation decision.
        
        Args:
            sensor_data: Current sensor data
            npk_data: Current NPK data
            weather_data: Current weather data
            ai_prediction: Current AI prediction
            tank_status: Current tank status
            pump_status: Current pump status
            
        Returns:
            Final irrigation action with safety constraints applied
        """
        logger.info("Decision Engine starting evaluation")
        
        # 0. First run all Failsafe checks!
        safety_result = self.failsafe_manager.check_irrigation_safety(
            soil_moisture=sensor_data.soil_moisture_percent,
            rain_expected=weather_data.rain_expected_24h,
            rain_probability=50.0 if weather_data.rain_expected_24h else 0.0,
            ai_confidence=ai_prediction.confidence,
            tank_level=tank_status.level_percent
        )
        
        # If safety is BLOCKED or EMERGENCY, immediately return OFF
        if safety_result.override in [SafetyOverride.BLOCKED, SafetyOverride.EMERGENCY]:
            logger.warning(f"Safety override: {safety_result.reason}")
            return IrrigationAction(
                pump_command=PumpCommand.OFF,
                decision=IrrigationDecision.DO_NOT_IRRIGATE,
                mode=IrrigationMode.EMERGENCY,
                confidence=1.0,
                reasons=[safety_result.reason]
            )
        
        # Step 1. Evaluate all rule engines
        rule_results: Dict[str, RuleResult] = {}
        
        rule_results["MoistureRuleEngine"] = self.moisture_engine.evaluate(sensor_data)
        rule_results["WeatherRuleEngine"] = self.weather_engine.evaluate(weather_data)
        rule_results["AIRuleEngine"] = self.ai_engine.evaluate(ai_prediction)
        rule_results["CropRuleEngine"] = self.crop_engine.evaluate(sensor_data, npk_data, weather_data)
        
        # Step 2. Determine active mode
        mode = self._determine_mode(ai_prediction, rule_results)
        logger.info(f"Using irrigation mode: {mode.name}")
        
        # Step 3. Combine results to make initial decision
        initial_action = self._combine_results(rule_results, mode)
        
        # Step 4. Calculate water requirement
        water_req = self.water_engine.calculate_water_requirement(
            sensor_data, weather_data, ai_prediction
        )
        initial_action.water_volume_liters = water_req["water_liters"]
        initial_action.duration_seconds = water_req["duration_seconds"]
        
        # Step 5. Determine scheduled time (if needed)
        if initial_action.decision in [IrrigationDecision.IRRIGATE_LATER, IrrigationDecision.IRRIGATE_NOW]:
            initial_action.scheduled_time = self.scheduler.find_next_irrigation_time(
                weather_data, sensor_data
            )
            
        # Step 6. Apply pump safety constraints
        final_action = self.pump_logic.evaluate(initial_action, pump_status, tank_status)
        
        logger.info(f"Final decision: {final_action.decision.name}")
        return final_action

    def _determine_mode(
        self,
        ai_prediction: AIPrediction,
        rule_results: Dict[str, RuleResult],
    ) -> IrrigationMode:
        """Determine which irrigation mode to use.
        
        Args:
            ai_prediction: AI prediction data
            rule_results: Results from all rule engines
            
        Returns:
            Irrigation mode to use
        """
        # Priority 1: If manual override is active, use MANUAL mode
        if self.failsafe_manager.manual_override.enabled:
            logger.info("Manual override active - using MANUAL mode")
            return IrrigationMode.MANUAL
        
        # Priority 2: If moisture engine says emergency, use emergency mode
        moisture_result = rule_results.get("MoistureRuleEngine")
        if moisture_result and moisture_result.decision == IrrigationDecision.EMERGENCY_IRRIGATE:
            return IrrigationMode.EMERGENCY
            
        # Priority 3: Check if AI confidence is low, use rule-based mode
        ai_result = rule_results.get("AIRuleEngine")
        if ai_result and ai_result.confidence < self.system_config.ai_confidence_threshold:
            logger.info("Switching to rule-based mode: AI confidence too low")
            return IrrigationMode.RULES
            
        # Default: use AI mode
        return self.system_config.irrigation_mode

    def _combine_results(
        self,
        rule_results: Dict[str, RuleResult],
        mode: IrrigationMode,
    ) -> IrrigationAction:
        """Combine results from all rule engines into a single action.
        
        Args:
            rule_results: Results from all rule engines
            mode: Irrigation mode in use
            
        Returns:
            Initial irrigation action
        """
        reasons: List[str] = []
        max_confidence = 0.0
        final_decision = IrrigationDecision.DO_NOT_IRRIGATE

        # In RULES mode: only moisture, weather, and crop engines count.
        # AIRuleEngine output is ignored so the rule-based threshold logic
        # (e.g. moisture < 30 → irrigate) is not overridden by AI confidence.
        if mode in (IrrigationMode.RULES, IrrigationMode.EMERGENCY):
            active_engines = {"MoistureRuleEngine", "WeatherRuleEngine", "CropRuleEngine"}
        else:
            # AI / MANUAL: all engines participate
            active_engines = set(rule_results.keys())

        # EMERGENCY: moisture engine wins unconditionally
        moisture_result = rule_results.get("MoistureRuleEngine")
        if (
            mode == IrrigationMode.EMERGENCY
            and moisture_result
            and moisture_result.decision == IrrigationDecision.EMERGENCY_IRRIGATE
        ):
            reasons.append(f"MoistureRuleEngine: {moisture_result.reason}")
            pump_command = PumpCommand.ON
            return IrrigationAction(
                pump_command=pump_command,
                decision=IrrigationDecision.EMERGENCY_IRRIGATE,
                mode=mode,
                confidence=1.0,
                reasons=reasons,
            )

        # Process each applicable rule result, highest priority first
        for name, result in rule_results.items():
            if name not in active_engines:
                reasons.append(f"{name}: SKIPPED (mode={mode.name})")
                continue
            reasons.append(f"{name}: {result.reason}")
            if result.confidence > max_confidence:
                max_confidence = result.confidence
                final_decision = result.decision
                
        # Determine pump command from final decision
        pump_command = PumpCommand.OFF
        if final_decision in [IrrigationDecision.IRRIGATE_NOW, IrrigationDecision.EMERGENCY_IRRIGATE]:
            pump_command = PumpCommand.ON
            
        return IrrigationAction(
            pump_command=pump_command,
            decision=final_decision,
            mode=mode,
            confidence=max_confidence,
            reasons=reasons,
        )

