"""Field environment model for Digital Twin."""

import logging
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FieldGeometry:
    """Field geometry properties."""
    area_m2: float = 1000.0  # 10x100m as default
    width_m: float = 10.0
    length_m: float = 100.0
    slope_deg: float = 0.0
    elevation_m: float = 100.0


@dataclass
class FieldIrrigation:
    """Irrigation system properties for the field."""
    irrigation_type: str = "drip"  # drip, sprinkler, flood
    efficiency: float = 0.85  # 0-1
    flow_rate_lps: float = 1.0  # liters per second
    sprinkler_spacing_m: float = 5.0
    emitter_count: int = 200


@dataclass
class FieldState:
    """Current state of the field."""
    last_irrigation_time: Optional[datetime] = None
    total_irrigation_today_l: float = 0.0
    irrigation_active: bool = False
    current_irrigation_duration_s: int = 0


class FieldModel:
    """
    Model representing the agricultural field environment.
    
    Combines geometry, irrigation system properties, and current state.
    """

    def __init__(
        self,
        geometry: Optional[FieldGeometry] = None,
        irrigation: Optional[FieldIrrigation] = None
    ):
        self.geometry = geometry or FieldGeometry()
        self.irrigation = irrigation or FieldIrrigation()
        self.state = FieldState()
        
        logger.info("FieldModel initialized")

    def calculate_area(self) -> float:
        """Calculate field area in square meters."""
        return self.geometry.width_m * self.geometry.length_m

    def calculate_irrigation_rate_mm_h(self) -> float:
        """
        Calculate irrigation application rate in mm per hour.
        
        Returns:
            Irrigation rate (mm/hour)
        """
        # Convert L/s to m³/hour
        flow_m3_hour = self.irrigation.flow_rate_lps * 3.6
        # Convert m³ to mm (1 m³ = 1 mm over 1000 m²)
        area_m2 = self.calculate_area()
        if area_m2 == 0:
            return 0.0
        mm_hour = (flow_m3_hour / area_m2) * 1000 * self.irrigation.efficiency
        return mm_hour

    def start_irrigation(self) -> None:
        """Start irrigation simulation."""
        self.state.irrigation_active = True
        self.state.last_irrigation_time = datetime.now()
        self.state.current_irrigation_duration_s = 0
        logger.info("Field irrigation started")

    def stop_irrigation(self) -> float:
        """
        Stop irrigation simulation and return total water applied.
        
        Returns:
            Total water applied (liters)
        """
        if not self.state.irrigation_active:
            return 0.0

        water_applied = self.irrigation.flow_rate_lps * self.state.current_irrigation_duration_s
        self.state.total_irrigation_today_l += water_applied
        self.state.irrigation_active = False
        self.state.current_irrigation_duration_s = 0
        logger.info(f"Field irrigation stopped, applied {water_applied:.2f} L")
        return water_applied

    def update(self, time_step_s: float) -> None:
        """
        Update field state for a time step.
        
        Args:
            time_step_s: Time step in seconds
        """
        if self.state.irrigation_active:
            self.state.current_irrigation_duration_s += int(time_step_s)

    def get_state(self) -> dict:
        """Get complete field state as dictionary."""
        return {
            "geometry": {
                "area_m2": self.geometry.area_m2,
                "width_m": self.geometry.width_m,
                "length_m": self.geometry.length_m
            },
            "irrigation_system": {
                "type": self.irrigation.irrigation_type,
                "efficiency": self.irrigation.efficiency,
                "flow_rate_lps": self.irrigation.flow_rate_lps
            },
            "state": {
                "irrigation_active": self.state.irrigation_active,
                "last_irrigation_time": self.state.last_irrigation_time,
                "total_irrigation_today_l": self.state.total_irrigation_today_l
            }
        }
