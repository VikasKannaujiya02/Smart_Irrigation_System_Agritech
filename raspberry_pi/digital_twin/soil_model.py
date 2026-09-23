"""Soil moisture and properties model for Digital Twin."""

import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum, auto

logger = logging.getLogger(__name__)


class SoilType(Enum):
    """Soil type classification."""
    SAND = auto()
    LOAMY_SAND = auto()
    SANDY_LOAM = auto()
    LOAM = auto()
    SILT_LOAM = auto()
    CLAY_LOAM = auto()
    CLAY = auto()


@dataclass
class SoilProperties:
    """Physical properties of the soil."""
    soil_type: SoilType = SoilType.LOAM
    field_capacity_vwc: float = 0.35  # Volumetric Water Content at field capacity
    wilting_point_vwc: float = 0.15  # Volumetric Water Content at wilting point
    saturation_vwc: float = 0.45  # Volumetric Water Content at saturation
    saturated_hydraulic_conductivity_cm_s: float = 0.01
    bulk_density_g_cm3: float = 1.4
    organic_matter_percent: float = 2.0
    root_depth_m: float = 0.6


@dataclass
class SoilState:
    """Current state of the soil."""
    current_vwc: float = 0.25  # Current volumetric water content
    temperature_c: float = 20.0
    salinity_ds_m: float = 1.0
    last_updated: Optional[float] = None  # timestamp


class SoilModel:
    """
    Model for soil moisture dynamics and properties.
    
    Simulates:
    - Moisture changes from irrigation
    - Moisture changes from evaporation/transpiration
    - Moisture changes from rainfall
    - Drainage below root zone
    """

    # Default soil properties by soil type
    SOIL_PROPERTIES = {
        SoilType.SAND: SoilProperties(
            soil_type=SoilType.SAND,
            field_capacity_vwc=0.10,
            wilting_point_vwc=0.03,
            saturation_vwc=0.40,
            saturated_hydraulic_conductivity_cm_s=0.1
        ),
        SoilType.LOAMY_SAND: SoilProperties(
            soil_type=SoilType.LOAMY_SAND,
            field_capacity_vwc=0.18,
            wilting_point_vwc=0.06,
            saturation_vwc=0.42,
            saturated_hydraulic_conductivity_cm_s=0.05
        ),
        SoilType.SANDY_LOAM: SoilProperties(
            soil_type=SoilType.SANDY_LOAM,
            field_capacity_vwc=0.23,
            wilting_point_vwc=0.10,
            saturation_vwc=0.43,
            saturated_hydraulic_conductivity_cm_s=0.02
        ),
        SoilType.LOAM: SoilProperties(
            soil_type=SoilType.LOAM,
            field_capacity_vwc=0.35,
            wilting_point_vwc=0.15,
            saturation_vwc=0.45,
            saturated_hydraulic_conductivity_cm_s=0.01
        ),
        SoilType.SILT_LOAM: SoilProperties(
            soil_type=SoilType.SILT_LOAM,
            field_capacity_vwc=0.38,
            wilting_point_vwc=0.18,
            saturation_vwc=0.48,
            saturated_hydraulic_conductivity_cm_s=0.005
        ),
        SoilType.CLAY_LOAM: SoilProperties(
            soil_type=SoilType.CLAY_LOAM,
            field_capacity_vwc=0.40,
            wilting_point_vwc=0.22,
            saturation_vwc=0.50,
            saturated_hydraulic_conductivity_cm_s=0.002
        ),
        SoilType.CLAY: SoilProperties(
            soil_type=SoilType.CLAY,
            field_capacity_vwc=0.42,
            wilting_point_vwc=0.25,
            saturation_vwc=0.52,
            saturated_hydraulic_conductivity_cm_s=0.001
        )
    }

    def __init__(
        self,
        properties: Optional[SoilProperties] = None,
        soil_type: SoilType = SoilType.LOAM
    ):
        if properties:
            self.properties = properties
        else:
            self.properties = self.SOIL_PROPERTIES.get(soil_type, SoilProperties())
        
        self.state = SoilState()
        # Initialize current_vwc to midpoint between wilting point and field capacity
        self.state.current_vwc = (
            self.properties.wilting_point_vwc + self.properties.field_capacity_vwc
        ) / 2
        
        logger.info(f"SoilModel initialized with type: {self.properties.soil_type.name}")

    @property
    def moisture_percent(self) -> float:
        """Get current moisture as percentage of field capacity."""
        vwc_range = self.properties.field_capacity_vwc - self.properties.wilting_point_vwc
        if vwc_range <= 0:
            return 50.0
        relative_vwc = (self.state.current_vwc - self.properties.wilting_point_vwc) / vwc_range
        return max(0.0, min(100.0, relative_vwc * 100))

    def apply_irrigation(self, mm: float) -> float:
        """
        Apply irrigation water to the soil.
        
        Args:
            mm: Irrigation amount in millimeters
            
        Returns:
            Actual water absorbed (mm)
        """
        # Convert mm to VWC (1 mm = 0.001 m over 1 m² = 0.001 m³ = 1 liter)
        # VWC = volume_water / volume_soil
        root_depth_m = self.properties.root_depth_m
        if root_depth_m <= 0:
            return 0.0
            
        vwc_add = mm / (1000 * root_depth_m)
        new_vwc = self.state.current_vwc + vwc_add
        
        # Cap at saturation
        if new_vwc > self.properties.saturation_vwc:
            absorbed_mm = (self.properties.saturation_vwc - self.state.current_vwc) * 1000 * root_depth_m
            self.state.current_vwc = self.properties.saturation_vwc
        else:
            absorbed_mm = mm
            self.state.current_vwc = new_vwc
            
        logger.debug(f"Applied {mm:.2f} mm irrigation, absorbed {absorbed_mm:.2f} mm")
        return absorbed_mm

    def apply_rainfall(self, mm: float) -> float:
        """
        Apply rainfall water to the soil.
        
        Args:
            mm: Rainfall amount in millimeters
            
        Returns:
            Actual water absorbed (mm)
        """
        # Similar to irrigation but may have different initial conditions
        return self.apply_irrigation(mm)

    def apply_et(self, et_mm: float) -> float:
        """
        Apply evapotranspiration (water loss).
        
        Args:
            et_mm: Evapotranspiration in millimeters
            
        Returns:
            Actual water lost (mm)
        """
        root_depth_m = self.properties.root_depth_m
        if root_depth_m <= 0:
            return 0.0
            
        vwc_remove = et_mm / (1000 * root_depth_m)
        new_vwc = self.state.current_vwc - vwc_remove
        
        # Floor at wilting point
        if new_vwc < self.properties.wilting_point_vwc:
            lost_mm = (self.state.current_vwc - self.properties.wilting_point_vwc) * 1000 * root_depth_m
            self.state.current_vwc = self.properties.wilting_point_vwc
        else:
            lost_mm = et_mm
            self.state.current_vwc = new_vwc
            
        logger.debug(f"Applied {et_mm:.2f} mm ET, lost {lost_mm:.2f} mm")
        return lost_mm

    def calculate_drainage(self, time_step_s: float) -> float:
        """
        Calculate drainage below root zone.
        
        Args:
            time_step_s: Time step in seconds
            
        Returns:
            Drainage in mm
        """
        # Simple drainage model: drain when above field capacity
        if self.state.current_vwc <= self.properties.field_capacity_vwc:
            return 0.0
            
        excess_vwc = self.state.current_vwc - self.properties.field_capacity_vwc
        # Drain 10% of excess per hour (adjust based on conductivity)
        k_sat = self.properties.saturated_hydraulic_conductivity_cm_s
        drain_rate_per_s = (k_sat / 100) * 3600  # m/hour
        drain_rate_per_s /= 3600  # m/second
        
        root_depth_m = self.properties.root_depth_m
        max_drain_vwc = drain_rate_per_s * time_step_s / root_depth_m
        
        drain_vwc = min(excess_vwc, max_drain_vwc)
        self.state.current_vwc -= drain_vwc
        
        drain_mm = drain_vwc * 1000 * root_depth_m
        logger.debug(f"Drained {drain_mm:.4f} mm")
        return drain_mm

    def update(
        self,
        time_step_s: float,
        irrigation_mm: float = 0.0,
        rainfall_mm: float = 0.0,
        et_mm: float = 0.0
    ) -> None:
        """
        Update soil state for a time step.
        
        Args:
            time_step_s: Time step in seconds
            irrigation_mm: Irrigation applied during this step
            rainfall_mm: Rainfall during this step
            et_mm: Evapotranspiration during this step
        """
        self.apply_irrigation(irrigation_mm)
        self.apply_rainfall(rainfall_mm)
        self.apply_et(et_mm)
        self.calculate_drainage(time_step_s)

    def get_state(self) -> dict:
        """Get complete soil state as dictionary."""
        return {
            "properties": {
                "soil_type": self.properties.soil_type.name,
                "field_capacity_vwc": self.properties.field_capacity_vwc,
                "wilting_point_vwc": self.properties.wilting_point_vwc,
                "saturation_vwc": self.properties.saturation_vwc,
                "root_depth_m": self.properties.root_depth_m
            },
            "state": {
                "current_vwc": self.state.current_vwc,
                "moisture_percent": self.moisture_percent,
                "temperature_c": self.state.temperature_c,
                "salinity_ds_m": self.state.salinity_ds_m
            }
        }
