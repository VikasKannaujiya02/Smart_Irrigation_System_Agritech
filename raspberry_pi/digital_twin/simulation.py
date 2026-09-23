"""Main Digital Twin simulation engine."""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, Dict
from datetime import datetime, timedelta
from enum import Enum, auto

from .field_model import FieldModel
from .soil_model import SoilModel
from .pump_model import PumpModel
from .crop_model import CropModel
from .weather_model import WeatherModel
from .state_manager import StateManager
from .sync_engine import SyncEngine

logger = logging.getLogger(__name__)


class SimulationMode(Enum):
    """Simulation mode."""
    REAL_TIME = auto()
    FAST_FORWARD = auto()
    SCENARIO = auto()
    PREDICTION = auto()


@dataclass
class SimulationConfig:
    """Simulation configuration."""
    mode: SimulationMode = SimulationMode.REAL_TIME
    time_step_s: float = 1.0
    duration_s: Optional[float] = None
    fast_forward_multiplier: float = 60.0  # 60x speed
    auto_snapshot: bool = True
    snapshot_interval_s: float = 60.0
    use_diurnal_cycle: bool = True


class SimulationEngine:
    """
    Main simulation engine for the Digital Twin.
    
    Features:
    - Real-time simulation
    - Fast-forward simulation
    - Scenario testing
    - AI prediction integration
    - Prediction comparison
    - Irrigation effect simulation
    """

    def __init__(
        self,
        field: Optional[FieldModel] = None,
        soil: Optional[SoilModel] = None,
        pump: Optional[PumpModel] = None,
        crop: Optional[CropModel] = None,
        weather: Optional[WeatherModel] = None,
        state_manager: Optional[StateManager] = None,
        config: Optional[SimulationConfig] = None
    ):
        self.field = field or FieldModel()
        self.soil = soil or SoilModel()
        self.pump = pump or PumpModel()
        self.crop = crop or CropModel()
        self.weather = weather or WeatherModel()
        self.state_manager = state_manager or StateManager()
        self.config = config or SimulationConfig()
        
        self.sync_engine = SyncEngine(
            field=self.field,
            soil=self.soil,
            pump=self.pump,
            crop=self.crop,
            weather=self.weather,
            state_manager=self.state_manager
        )
        
        self._simulation_thread: Optional[threading.Thread] = None
        self._running = False
        self._paused = False
        
        self.simulated_time: datetime = datetime.now()
        self.simulation_steps = 0
        self.last_snapshot_time: Optional[datetime] = None
        
        self._ai_prediction_func: Optional[Callable] = None
        self._irrigation_decision_func: Optional[Callable] = None
        self._callbacks: Dict[str, list[Callable]] = {
            "step_complete": [],
            "snapshot_taken": [],
            "prediction_made": [],
            "irrigation_decision": [],
            "simulation_complete": []
        }
        
        logger.info("SimulationEngine initialized")

    def register_callback(self, event: str, callback: Callable) -> None:
        """
        Register a callback.
        
        Args:
            event: Event name
            callback: Callback function
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _trigger_callbacks(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Trigger registered callbacks."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")

    def set_ai_prediction_func(self, func: Callable) -> None:
        """
        Set the AI prediction function.
        
        Args:
            func: Function that returns AI predictions
        """
        self._ai_prediction_func = func

    def set_irrigation_decision_func(self, func: Callable) -> None:
        """
        Set the irrigation decision function.
        
        Args:
            func: Function that makes irrigation decisions
        """
        self._irrigation_decision_func = func

    def _simulate_step(self) -> None:
        """Perform one simulation step."""
        dt = self.config.time_step_s
        
        # Weather update
        if self.config.use_diurnal_cycle:
            weather_state = self.weather.simulate_diurnal_cycle(
                current_time=self.simulated_time.time()
            )
            self.weather.update_state(weather_state, timestamp=self.simulated_time)
        
        # Calculate ET for time step
        eto_mm = (self.weather.state.eto_mm_day / 86400) * dt
        
        # Crop update
        self.crop.update(dt, eto_mm)
        
        # Soil update
        irrigation_mm = 0.0
        if self.field.state.irrigation_active:
            irrigation_rate_mm_s = self.field.calculate_irrigation_rate_mm_h() / 3600
            irrigation_mm = irrigation_rate_mm_s * dt
        
        rainfall_mm = self.weather.state.rainfall_mm * (dt / 86400)
        
        self.soil.update(
            time_step_s=dt,
            irrigation_mm=irrigation_mm,
            rainfall_mm=rainfall_mm,
            eto_mm=eto_mm
        )
        
        # Pump update
        self.pump.update(dt)
        
        # Field update
        self.field.update(dt)
        
        # AI prediction
        ai_pred = None
        if self._ai_prediction_func:
            try:
                ai_pred = self._ai_prediction_func(
                    soil_moisture=self.soil.moisture_percent,
                    weather={
                        "temperature_c": self.weather.state.temperature_c,
                        "humidity_pct": self.weather.state.humidity_pct,
                        "eto_mm_day": self.weather.state.eto_mm_day
                    }
                )
                self.state_manager.store_prediction(ai_pred, self.simulated_time)
                self._trigger_callbacks("prediction_made", prediction=ai_pred)
            except Exception as e:
                logger.error(f"AI prediction error: {e}")
        
        # Irrigation decision
        irr_decision = None
        if self._irrigation_decision_func:
            try:
                irr_decision = self._irrigation_decision_func(
                    soil_moisture=self.soil.moisture_percent,
                    weather_state=self.weather.state,
                    crop_state=self.crop.state,
                    ai_prediction=ai_pred
                )
                self._trigger_callbacks("irrigation_decision", decision=irr_decision)
                
                # Apply decision
                if irr_decision.get("irrigate"):
                    if not self.field.state.irrigation_active:
                        self.field.start_irrigation()
                        self.pump.turn_on()
                else:
                    if self.field.state.irrigation_active:
                        self.field.stop_irrigation()
                        self.pump.turn_off()
            except Exception as e:
                logger.error(f"Irrigation decision error: {e}")
        
        # Snapshot
        if self.config.auto_snapshot:
            time_since_snapshot = (
                (self.simulated_time - self.last_snapshot_time).total_seconds()
                if self.last_snapshot_time
                else float('inf')
            )
            if time_since_snapshot >= self.config.snapshot_interval_s:
                self.state_manager.snapshot(
                    field=self.field,
                    soil=self.soil,
                    pump=self.pump,
                    crop=self.crop,
                    weather=self.weather,
                    timestamp=self.simulated_time,
                    ai_prediction=ai_pred,
                    irrigation_decision=irr_decision
                )
                self.last_snapshot_time = self.simulated_time
                self._trigger_callbacks("snapshot_taken")
        
        self.simulated_time += timedelta(seconds=dt)
        self.simulation_steps += 1

    def _simulation_loop(self) -> None:
        """Main simulation loop."""
        start_time = datetime.now()
        target_end_time = (
            self.simulated_time + timedelta(seconds=self.config.duration_s)
            if self.config.duration_s
            else None
        )
        
        while self._running:
            if self._paused:
                time.sleep(0.1)
                continue
                
            self._simulate_step()
            
            self._trigger_callbacks("step_complete", step=self.simulation_steps)
            
            # Check duration
            if target_end_time and self.simulated_time >= target_end_time:
                break
                
            # Sleep for real-time mode
            if self.config.mode == SimulationMode.REAL_TIME:
                elapsed = (datetime.now() - start_time).total_seconds()
                simulated_elapsed = (self.simulated_time - start_time).total_seconds()
                sleep_time = max(0, simulated_elapsed - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
        
        self._trigger_callbacks("simulation_complete")
        self._running = False

    def start(self) -> None:
        """Start the simulation."""
        if self._running:
            logger.warning("Simulation already running")
            return
            
        self._running = True
        self._paused = False
        self.last_snapshot_time = self.simulated_time
        
        self._simulation_thread = threading.Thread(target=self._simulation_loop, daemon=True)
        self._simulation_thread.start()
        
        if self.config.mode == SimulationMode.REAL_TIME:
            self.sync_engine.start_sync()
            
        logger.info(f"Simulation started in {self.config.mode.name} mode")

    def pause(self) -> None:
        """Pause the simulation."""
        self._paused = True
        logger.info("Simulation paused")

    def resume(self) -> None:
        """Resume the simulation."""
        self._paused = False
        logger.info("Simulation resumed")

    def stop(self) -> None:
        """Stop the simulation."""
        self._running = False
        if self._simulation_thread:
            self._simulation_thread.join(timeout=5.0)
        self.sync_engine.stop_sync()
        logger.info("Simulation stopped")

    def run_scenario(
        self,
        duration_s: float,
        scenario_id: str,
        initial_state: Optional[Dict] = None,
        weather_override: Optional[Dict] = None
    ) -> list:
        """
        Run a scenario simulation.
        
        Args:
            duration_s: Scenario duration in seconds
            scenario_id: Scenario ID
            initial_state: Optional initial state override
            weather_override: Optional weather override
            
        Returns:
            List of scenario states
        """
        logger.info(f"Starting scenario: {scenario_id}")
        
        original_mode = self.config.mode
        self.config.mode = SimulationMode.SCENARIO
        self.config.duration_s = duration_s
        self.config.auto_snapshot = True
        self.config.snapshot_interval_s = 60.0
        
        if initial_state:
            self._apply_initial_state(initial_state)
            
        if weather_override:
            self._apply_weather_override(weather_override)
        
        self.start()
        while self._running:
            time.sleep(0.1)
            
        scenario_states = self.state_manager.get_scenario(scenario_id)
        self.config.mode = original_mode
        
        logger.info(f"Scenario complete: {len(scenario_states)} states recorded")
        return scenario_states

    def predict_future(
        self,
        hours_ahead: int = 24,
        steps_per_hour: int = 4
    ) -> list:
        """
        Simulate future conditions.
        
        Args:
            hours_ahead: Prediction horizon
            steps_per_hour: Steps per hour
            
        Returns:
            List of predicted states
        """
        logger.info(f"Predicting {hours_ahead} hours ahead")
        
        original_mode = self.config.mode
        self.config.mode = SimulationMode.PREDICTION
        self.config.duration_s = hours_ahead * 3600
        self.config.time_step_s = 3600 / steps_per_hour
        
        prediction_states = []
        
        for step in range(hours_ahead * steps_per_hour):
            self._simulate_step()
            state = self.state_manager.snapshot(
                field=self.field,
                soil=self.soil,
                pump=self.pump,
                crop=self.crop,
                weather=self.weather,
                timestamp=self.simulated_time,
                scenario_id="prediction"
            )
            prediction_states.append(state)
            
        self.config.mode = original_mode
        logger.info("Prediction complete")
        
        return prediction_states

    def _apply_initial_state(self, state: Dict) -> None:
        """Apply initial state override."""
        if "soil" in state:
            if "moisture_vwc" in state["soil"]:
                self.soil.state.current_vwc = state["soil"]["moisture_vwc"]
                
    def _apply_weather_override(self, weather: Dict) -> None:
        """Apply weather override."""
        pass

    def get_stats(self) -> Dict:
        """Get simulation statistics."""
        return {
            "running": self._running,
            "paused": self._paused,
            "mode": self.config.mode.name,
            "simulated_time": self.simulated_time,
            "steps": self.simulation_steps,
            "soil_moisture": self.soil.moisture_percent,
            "pump_state": self.pump.state.state.name,
            "irrigation_active": self.field.state.irrigation_active
        }
