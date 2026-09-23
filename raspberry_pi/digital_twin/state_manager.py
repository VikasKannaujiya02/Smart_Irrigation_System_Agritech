"""Digital Twin state management for Digital Twin."""

import logging
import pickle
from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime
from pathlib import Path

from .field_model import FieldModel
from .soil_model import SoilModel
from .pump_model import PumpModel
from .crop_model import CropModel
from .weather_model import WeatherModel

logger = logging.getLogger(__name__)


@dataclass
class DigitalTwinState:
    """Complete state of the Digital Twin at a point in time."""
    timestamp: datetime
    field_state: dict
    soil_state: dict
    pump_state: dict
    crop_state: dict
    weather_state: dict
    ai_prediction: Optional[dict] = None
    irrigation_decision: Optional[dict] = None
    scenario_id: Optional[str] = None


class StateManager:
    """
    Manages the state of the Digital Twin.
    
    Features:
    - State snapshotting
    - State persistence
    - State history
    - AI prediction storage
    - Scenario comparison
    """

    def __init__(
        self,
        data_dir: Optional[str] = None,
        max_history: int = 10000
    ):
        self.data_dir = Path(data_dir) if data_dir else Path("data/digital_twin")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_state: Optional[DigitalTwinState] = None
        self.state_history: list[DigitalTwinState] = []
        self.max_history = max_history
        
        self.scenarios: dict[str, list[DigitalTwinState]] = {}
        self.predictions: list[dict] = []
        self.live_state: dict[str, Any] = {}
        
        logger.info("StateManager initialized")

    def update_state(self, data: dict[str, Any]) -> None:
        """Update lightweight live state from orchestrator sync data."""
        now = datetime.now()
        sensor_records = data.get("sensor_data") or []
        if isinstance(sensor_records, list) and sensor_records:
            latest = sensor_records[-1]
            soil_moisture = latest.get("soil_moisture_percent", latest.get("soil_moisture"))
            temperature = latest.get("temperature_c", latest.get("temperature"))
            humidity = latest.get("humidity_percent", latest.get("humidity"))
            if soil_moisture is not None:
                self.live_state["soil_moisture_pct"] = float(soil_moisture)
                self.live_state["soil_moisture_vwc"] = float(soil_moisture) / 100.0
            if temperature is not None:
                self.live_state["temperature_c"] = float(temperature)
            if humidity is not None:
                self.live_state["humidity_percent"] = float(humidity)

        decision = data.get("decision")
        if decision is not None:
            pump_command = getattr(getattr(decision, "pump_command", None), "name", None)
            if pump_command:
                self.live_state["pump_state"] = "on" if pump_command == "ON" else "off"
            self.live_state["irrigation_decision"] = getattr(getattr(decision, "decision", None), "name", None)

        self.live_state["timestamp"] = now
        self.live_state.setdefault("crop_stage", "unknown")
        self.live_state.setdefault("eto_mm_day", 0.0)
        self.live_state.setdefault("field_area_m2", 0.0)

    def get_current_state(self) -> dict[str, Any]:
        """Return the current lightweight live state for the dashboard API."""
        return dict(self.live_state)

    def snapshot(
        self,
        field: FieldModel,
        soil: SoilModel,
        pump: PumpModel,
        crop: CropModel,
        weather: WeatherModel,
        timestamp: Optional[datetime] = None,
        ai_prediction: Optional[dict] = None,
        irrigation_decision: Optional[dict] = None,
        scenario_id: Optional[str] = None
    ) -> DigitalTwinState:
        """
        Take a snapshot of the current Digital Twin state.
        
        Args:
            field: Field model
            soil: Soil model
            pump: Pump model
            crop: Crop model
            weather: Weather model
            timestamp: Snapshot timestamp (defaults to now)
            ai_prediction: AI prediction data
            irrigation_decision: Irrigation decision data
            scenario_id: Scenario ID
            
        Returns:
            Digital Twin state snapshot
        """
        ts = timestamp or datetime.now()
        
        state = DigitalTwinState(
            timestamp=ts,
            field_state=field.get_state(),
            soil_state=soil.get_state(),
            pump_state=pump.get_state(),
            crop_state=crop.get_state(),
            weather_state=weather.get_state(),
            ai_prediction=ai_prediction,
            irrigation_decision=irrigation_decision,
            scenario_id=scenario_id
        )
        
        self.current_state = state
        
        # Add to main history
        self.state_history.append(state)
        if len(self.state_history) > self.max_history:
            self.state_history.pop(0)
            
        # Add to scenario if specified
        if scenario_id:
            if scenario_id not in self.scenarios:
                self.scenarios[scenario_id] = []
            self.scenarios[scenario_id].append(state)
        
        logger.debug(f"State snapshot taken at {ts}")
        return state

    def save_state(
        self,
        state: Optional[DigitalTwinState] = None,
        filename: Optional[str] = None
    ) -> Path:
        """
        Save a state to disk.
        
        Args:
            state: State to save (defaults to current state)
            filename: Output filename
            
        Returns:
            Path to saved file
        """
        state_to_save = state or self.current_state
        if not state_to_save:
            raise ValueError("No state available to save")
            
        if not filename:
            filename = f"state_{state_to_save.timestamp.strftime('%Y%m%d_%H%M%S')}.pkl"
            
        filepath = self.data_dir / filename
        
        with open(filepath, 'wb') as f:
            pickle.dump(state_to_save, f)
            
        logger.info(f"State saved to {filepath}")
        return filepath

    def load_state(self, filepath: str) -> DigitalTwinState:
        """
        Load a state from disk.
        
        Args:
            filepath: Path to state file
            
        Returns:
            Loaded state
        """
        with open(filepath, 'rb') as f:
            state = pickle.load(f)
            
        self.current_state = state
        logger.info(f"State loaded from {filepath}")
        return state

    def get_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> list[DigitalTwinState]:
        """
        Get state history filtered by time.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum number of states to return
            
        Returns:
            List of states
        """
        states = self.state_history
        
        if start_time:
            states = [s for s in states if s.timestamp >= start_time]
        if end_time:
            states = [s for s in states if s.timestamp <= end_time]
            
        if limit:
            states = states[-limit:]
            
        return states

    def get_scenario(self, scenario_id: str) -> list[DigitalTwinState]:
        """
        Get all states for a scenario.
        
        Args:
            scenario_id: Scenario ID
            
        Returns:
            List of scenario states
        """
        return self.scenarios.get(scenario_id, [])

    def compare_states(
        self,
        state1: DigitalTwinState,
        state2: DigitalTwinState
    ) -> dict[str, Any]:
        """
        Compare two Digital Twin states.
        
        Args:
            state1: First state
            state2: Second state
            
        Returns:
            Comparison results
        """
        comparison = {
            "timestamp_diff": state2.timestamp - state1.timestamp,
            "soil_moisture_diff": (
                state2.soil_state["state"]["moisture_percent"] -
                state1.soil_state["state"]["moisture_percent"]
            ),
            "pump_runtime_diff": (
                state2.pump_state["state"]["total_runtime_today_s"] -
                state1.pump_state["state"]["total_runtime_today_s"]
            ),
            "cumulative_water_use_diff": (
                state2.crop_state["state"]["cumulative_water_use_mm"] -
                state1.crop_state["state"]["cumulative_water_use_mm"]
            )
        }
        return comparison

    def store_prediction(
        self,
        prediction: dict,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Store an AI prediction.
        
        Args:
            prediction: Prediction data
            timestamp: Prediction timestamp
        """
        pred_data = {
            "timestamp": timestamp or datetime.now(),
            "prediction": prediction
        }
        self.predictions.append(pred_data)

    def get_prediction_history(
        self,
        limit: Optional[int] = None
    ) -> list[dict]:
        """
        Get stored AI prediction history.
        
        Args:
            limit: Maximum number of predictions to return
            
        Returns:
            List of predictions
        """
        if limit:
            return self.predictions[-limit:]
        return self.predictions

    def clear_history(self) -> None:
        """Clear all state history."""
        self.state_history = []
        self.scenarios = {}
        self.predictions = []
        logger.info("State history cleared")
