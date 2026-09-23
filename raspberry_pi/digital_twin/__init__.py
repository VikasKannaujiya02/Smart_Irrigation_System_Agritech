"""Digital Twin module for AI Smart Irrigation System.

This module provides a complete digital twin implementation including:
- Field environment modeling
- Soil moisture and properties simulation
- Pump operation simulation
- Crop water consumption modeling
- Weather simulation and ETo calculation
- State management and persistence
- Real-time synchronization and historical replay
- Scenario testing and prediction comparison
"""

from .field_model import (
    FieldModel,
    FieldGeometry,
    FieldIrrigation,
    FieldState
)
from .soil_model import (
    SoilModel,
    SoilType,
    SoilProperties,
    SoilState
)
from .pump_model import (
    PumpModel,
    PumpState,
    PumpProperties,
    PumpStateData
)
from .crop_model import (
    CropModel,
    CropType,
    GrowthStage,
    CropProperties,
    CropState
)
from .weather_model import (
    WeatherModel,
    WeatherState,
    WeatherForecast
)
from .state_manager import (
    StateManager,
    DigitalTwinState
)
from .sync_engine import (
    SyncEngine,
    SyncConfig
)
from .simulation import (
    SimulationEngine,
    SimulationMode,
    SimulationConfig
)

__all__ = [
    "FieldModel",
    "FieldGeometry",
    "FieldIrrigation",
    "FieldState",
    "SoilModel",
    "SoilType",
    "SoilProperties",
    "SoilState",
    "PumpModel",
    "PumpState",
    "PumpProperties",
    "PumpStateData",
    "CropModel",
    "CropType",
    "GrowthStage",
    "CropProperties",
    "CropState",
    "WeatherModel",
    "WeatherState",
    "WeatherForecast",
    "StateManager",
    "DigitalTwinState",
    "SyncEngine",
    "SyncConfig",
    "SimulationEngine",
    "SimulationMode",
    "SimulationConfig"
]
