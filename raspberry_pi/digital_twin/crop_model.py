"""Crop water consumption model for Digital Twin."""

import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum, auto
from datetime import date

logger = logging.getLogger(__name__)


class CropType(Enum):
    """Crop type classification."""
    TOMATO = auto()
    CORN = auto()
    WHEAT = auto()
    COTTON = auto()
    SOYBEAN = auto()
    GRAPE = auto()
    POTATO = auto()
    LETTUCE = auto()
    GRASS = auto()


class GrowthStage(Enum):
    """Crop growth stage."""
    SEEDLING = auto()
    VEGETATIVE = auto()
    FLOWERING = auto()
    FRUITING = auto()
    RIPENING = auto()
    HARVEST = auto()


@dataclass
class CropProperties:
    """Crop properties for water consumption modeling."""
    crop_type: CropType = CropType.TOMATO
    planting_date: Optional[date] = None
    growing_season_days: int = 90
    kc_initial: float = 0.3  # Crop coefficient - initial stage
    kc_mid: float = 1.15  # Crop coefficient - mid-season
    kc_late: float = 0.6  # Crop coefficient - late season
    rooting_depth_initial_m: float = 0.3
    rooting_depth_max_m: float = 0.8
    critical_moisture_depletion_pct: float = 0.5  # Allowable depletion before irrigation
    plant_count: int = 1000


@dataclass
class CropState:
    """Current state of the crop."""
    growth_stage: GrowthStage = GrowthStage.SEEDLING
    days_since_planting: int = 0
    current_kc: float = 0.3
    current_root_depth_m: float = 0.3
    water_requirement_mm_day: float = 0.0
    cumulative_water_use_mm: float = 0.0
    stress_index: float = 0.0  # 0 = no stress, 1 = severe stress


class CropModel:
    """
    Model for crop water consumption and growth.
    
    Uses FAO Penman-Monteith simplified approach for ET calculation:
    ETc = Kc * ETo
    
    where:
    - ETc = Crop evapotranspiration
    - Kc = Crop coefficient (varies by growth stage)
    - ETo = Reference evapotranspiration
    """

    # Default crop properties
    CROP_PROPERTIES = {
        CropType.TOMATO: CropProperties(
            crop_type=CropType.TOMATO,
            growing_season_days=120,
            kc_initial=0.4,
            kc_mid=1.15,
            kc_late=0.7,
            rooting_depth_initial_m=0.2,
            rooting_depth_max_m=0.7,
            critical_moisture_depletion_pct=0.4
        ),
        CropType.CORN: CropProperties(
            crop_type=CropType.CORN,
            growing_season_days=110,
            kc_initial=0.3,
            kc_mid=1.2,
            kc_late=0.35,
            rooting_depth_initial_m=0.3,
            rooting_depth_max_m=1.2,
            critical_moisture_depletion_pct=0.55
        ),
        CropType.WHEAT: CropProperties(
            crop_type=CropType.WHEAT,
            growing_season_days=120,
            kc_initial=0.3,
            kc_mid=1.15,
            kc_late=0.25,
            rooting_depth_initial_m=0.2,
            rooting_depth_max_m=1.0,
            critical_moisture_depletion_pct=0.5
        ),
        CropType.SOYBEAN: CropProperties(
            crop_type=CropType.SOYBEAN,
            growing_season_days=100,
            kc_initial=0.4,
            kc_mid=1.1,
            kc_late=0.5,
            rooting_depth_initial_m=0.2,
            rooting_depth_max_m=0.9,
            critical_moisture_depletion_pct=0.5
        ),
        CropType.GRASS: CropProperties(
            crop_type=CropType.GRASS,
            growing_season_days=365,
            kc_initial=0.8,
            kc_mid=0.85,
            kc_late=0.8,
            rooting_depth_initial_m=0.3,
            rooting_depth_max_m=0.6,
            critical_moisture_depletion_pct=0.5
        )
    }

    def __init__(
        self,
        properties: Optional[CropProperties] = None, crop_type: CropType = CropType.TOMATO
    ):
        if properties:
            self.properties = properties
        else:
            self.properties = self.CROP_PROPERTIES.get(crop_type, CropProperties())

        if not self.properties.planting_date:
            self.properties.planting_date = date.today()
        self.state = CropState()
        self.state.current_kc = self.properties.kc_initial
        self.state.current_root_depth_m = self.properties.rooting_depth_initial_m
        logger.info(f"CropModel initialized for {self.properties.crop_type.name}")

    def calculate_growth_stage(self) -> GrowthStage:
        """
        Determine current growth stage based on days since planting.
        
        Returns:
            Current growth stage
        """
        days = self.state.days_since_planting
        season = self.properties.growing_season_days
        
        if days < season * 0.1:
            return GrowthStage.SEEDLING
        elif days < season * 0.3:
            return GrowthStage.VEGETATIVE
        elif days < season * 0.6:
            return GrowthStage.FLOWERING
        elif days < season * 0.8:
            return GrowthStage.FRUITING
        elif days < season:
            return GrowthStage.RIPENING
        else:
            return GrowthStage.HARVEST

    def calculate_crop_coefficient(self) -> float:
        """
        Calculate current crop coefficient (Kc).
        
        Returns:
            Crop coefficient Kc
        """
        days = self.state.days_since_planting
        season = self.properties.growing_season_days
        stage = self.calculate_growth_stage()
        
        if stage == GrowthStage.SEEDLING:
            return self.properties.kc_initial
        elif stage in (GrowthStage.VEGETATIVE, GrowthStage.FLOWERING):
            # Linear interpolation from kc_initial to kc_mid
            t_mid_start = season * 0.3
            t_mid_end = season * 0.6
            if days < t_mid_start:
                return self.properties.kc_initial
            elif days < t_mid_end:
                progress = (days - t_mid_start) / (t_mid_end - t_mid_start)
                return self.properties.kc_initial + progress * (self.properties.kc_mid - self.properties.kc_initial)
            else:
                return self.properties.kc_mid
        elif stage in (GrowthStage.FRUITING, GrowthStage.RIPENING, GrowthStage.HARVEST):
            # Linear interpolation from kc_mid to kc_late
            t_late_start = season * 0.6
            if days < t_late_start:
                return self.properties.kc_mid
            elif days < season:
                progress = (days - t_late_start) / (season * 0.2)
                return self.properties.kc_mid - progress * (self.properties.kc_mid - self.properties.kc_late)
            else:
                return self.properties.kc_late
        
        return self.properties.kc_mid

    def calculate_root_depth(self) -> float:
        """
        Calculate current root depth.
        
        Returns:
            Root depth in meters
        """
        days = self.state.days_since_planting
        season = self.properties.growing_season_days
        
        # Sigmoidal growth curve for root depth
        if days <= 0:
            return self.properties.rooting_depth_initial_m
            
        progress = min(days / (season * 0.6), 1.0)
        # Logistic growth
        k = 5  # growth rate
        depth = (
            self.properties.rooting_depth_initial_m +
            (self.properties.rooting_depth_max_m - self.properties.rooting_depth_initial_m) /
            (1 + (1 / progress - 1) ** k)
        )
        return depth

    def calculate_etc(self, eto_mm_day: float) -> float:
        """
        Calculate crop evapotranspiration (ETc).
        
        Args:
            eto_mm_day: Reference evapotranspiration in mm/day
            
        Returns:
            ETc in mm/day
        """
        kc = self.calculate_crop_coefficient()
        etc = kc * eto_mm_day
        return etc

    def calculate_water_requirement(
        self,
        eto_mm_day: float,
        soil_moisture_pct: float
    ) -> tuple[float, float]:
        """
        Calculate net irrigation requirement.
        
        Args:
            eto_mm_day: Reference evapotranspiration mm/day
            soil_moisture_pct: Current soil moisture % field capacity
            
        Returns:
            (irrigation_requirement_mm, stress_index)
        """
        etc = self.calculate_etc(eto_mm_day)
        
        # Calculate stress index
        critical_depletion = self.properties.critical_moisture_depletion_pct
        current_depletion = 1.0 - (soil_moisture_pct / 100.0)
        
        if current_depletion <= critical_depletion:
            stress = 0.0
        else:
            stress = min((current_depletion - critical_depletion) / (1 - critical_depletion), 1.0)
            
        # If stress = depletion beyond critical, requirement is etc (1.0 + stress*0.5)
        irrigation_req = etc * (1.0 + stress * 0.5)
        
        return irrigation_req, stress

    def update(self, time_step_s: float, eto_mm: float) -> None:
        """
        Update crop model for a time step.
        
        Args:
            time_step_s: Time step in seconds
            eto_mm: ETo during this time step (mm)
        """
        # Update days since planting (simplified)
        self.state.days_since_planting += time_step_s / 86400
        
        # Update growth stage
        self.state.growth_stage = self.calculate_growth_stage()
        
        # Update crop coefficient
        self.state.current_kc = self.calculate_crop_coefficient()
        
        # Update root depth
        self.state.current_root_depth_m = self.calculate_root_depth()
        
        # Update water use
        etc = self.state.current_kc * eto_mm
        self.state.water_requirement_mm_day = etc * (86400 / time_step_s) if time_step_s >0 else 0
        self.state.cumulative_water_use_mm += etc

    def get_state(self) -> dict:
        """Get complete crop state as dictionary."""
        return {
            "properties": {
                "crop_type": self.properties.crop_type.name,
                "growing_season_days": self.properties.growing_season_days,
                "kc_initial": self.properties.kc_initial,
                "kc_mid": self.properties.kc_mid,
                "kc_late": self.properties.kc_late,
                "root_depth_max_m": self.properties.rooting_depth_max_m
            },
            "state": {
                "growth_stage": self.state.growth_stage.name,
                "days_since_planting": self.state.days_since_planting,
                "current_kc": self.state.current_kc,
                "current_root_depth_m": self.state.current_root_depth_m,
                "water_requirement_mm_day": self.state.water_requirement_mm_day,
                "cumulative_water_use_mm": self.state.cumulative_water_use_mm
            }
        }
