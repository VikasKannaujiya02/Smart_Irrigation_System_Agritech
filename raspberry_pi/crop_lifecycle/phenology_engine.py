"""Crop phenology / growth-stage engine.

Each crop has its own configurable stage thresholds.  Stage boundaries are
expressed as *fraction of the crop's total growing-season length* so that the
same engine works for both short-cycle (60-day) and long-cycle (180-day) crops.

Sources for default values
──────────────────────────
These defaults are *configuration placeholders* derived from FAO-56 general
crop tables.  They MUST be validated against actual local agronomic data before
being treated as authoritative.  They are clearly marked with:
    SOURCE = phenology_config (requires agronomic validation)

GDD (Growing Degree Days) support is architecture-ready:

    daily_gdd = max(0, T_mean - T_base)
    accumulated_gdd → compared against crop-specific GDD thresholds per stage

When no reliable temperature data or validated GDD thresholds are available the
engine falls back to the day-fraction method.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Growth stage definitions
# ─────────────────────────────────────────────

LIFECYCLE_STATUSES = [
    "PLANNED",
    "PLANTED",
    "GROWING",
    "HARVEST_READY",
    "HARVESTED",
    "COMPLETED",
]


@dataclass
class GrowthStageDefinition:
    """One stage in a crop's phenological sequence.

    Attributes
    ----------
    name:
        Human-readable stage name (e.g. ``"Germination"``).
    day_fraction_start:
        Fraction of total growing season at which this stage begins
        (0.0 = planting day).
    day_fraction_end:
        Fraction at which this stage ends (1.0 = harvest day).
    gdd_threshold_start:
        Accumulated GDD required to *enter* this stage.
        ``None`` means GDD-based detection not yet configured.
    gdd_threshold_end:
        Accumulated GDD at which the stage ends.
        ``None`` if not yet configured.
    description:
        Optional agronomic notes.
    """

    name: str
    day_fraction_start: float
    day_fraction_end: float
    gdd_threshold_start: Optional[float] = None  # GDD-ready, not yet validated
    gdd_threshold_end: Optional[float] = None
    description: str = ""


@dataclass
class CropPhenologyConfig:
    """Full phenological configuration for one crop type.

    Attributes
    ----------
    crop_name:
        Canonical crop name (matches XGBoost model class name where possible).
    growing_season_days:
        Typical growing-season length in days.
        SOURCE = phenology_config (requires agronomic validation)
    base_temperature_c:
        Base temperature for GDD calculation.
        SOURCE = phenology_config (requires agronomic validation)
    stages:
        Ordered list of growth stages from planting to harvest.
    notes:
        Free-text agronomic notes / caveats.
    """

    crop_name: str
    growing_season_days: int
    base_temperature_c: float = 10.0  # placeholder — validate per crop
    stages: List[GrowthStageDefinition] = field(default_factory=list)
    notes: str = ""


# ─────────────────────────────────────────────
#  Default crop phenology library
# ─────────────────────────────────────────────
#
#  All values below are CONFIGURABLE DEFAULTS.
#  SOURCE = phenology_config (requires agronomic validation)
#  Do NOT use these values as authoritative agronomic science without review.
# ─────────────────────────────────────────────

def _build_generic_stages(season: int) -> List[GrowthStageDefinition]:
    """Fallback for crops without their own stage library."""
    return [
        GrowthStageDefinition("Germination",   0.00, 0.10, description="Seed germination phase"),
        GrowthStageDefinition("Seedling",      0.10, 0.25, description="Early plant establishment"),
        GrowthStageDefinition("Vegetative",    0.25, 0.55, description="Leaf and stem growth"),
        GrowthStageDefinition("Flowering",     0.55, 0.70, description="Floral initiation"),
        GrowthStageDefinition("Grain/Fruit Fill", 0.70, 0.85, description="Fruit / grain development"),
        GrowthStageDefinition("Maturity",      0.85, 0.95, description="Physiological maturity"),
        GrowthStageDefinition("Harvest Ready", 0.95, 1.00, description="Ready for harvest"),
    ]


DEFAULT_CROP_CONFIGS: Dict[str, CropPhenologyConfig] = {
    # ── Rice ──────────────────────────────────────────────────────────────────
    "rice": CropPhenologyConfig(
        crop_name="Rice",
        growing_season_days=130,
        base_temperature_c=10.0,
        notes="SOURCE=phenology_config. Validate with local rice variety data.",
        stages=[
            GrowthStageDefinition("Germination",    0.00, 0.05, description="Seed germination"),
            GrowthStageDefinition("Seedling",       0.05, 0.20, description="Seedling / transplant"),
            GrowthStageDefinition("Tillering",      0.20, 0.45, description="Active tiller production"),
            GrowthStageDefinition("Heading",        0.45, 0.65, description="Panicle initiation & heading"),
            GrowthStageDefinition("Flowering",      0.65, 0.75, description="Anthesis / pollination"),
            GrowthStageDefinition("Grain Filling",  0.75, 0.90, description="Grain development"),
            GrowthStageDefinition("Maturity",       0.90, 0.96, description="Physiological maturity"),
            GrowthStageDefinition("Harvest Ready",  0.96, 1.00, description="Ready for harvest"),
        ],
    ),
    # ── Maize / Corn ──────────────────────────────────────────────────────────
    "maize": CropPhenologyConfig(
        crop_name="Maize",
        growing_season_days=110,
        base_temperature_c=10.0,
        notes="SOURCE=phenology_config. Validate with local hybrid maturity class.",
        stages=[
            GrowthStageDefinition("Germination",   0.00, 0.07, description="VE stage"),
            GrowthStageDefinition("Seedling",      0.07, 0.20, description="V1-V6"),
            GrowthStageDefinition("Vegetative",    0.20, 0.50, description="V7-V10 rapid growth"),
            GrowthStageDefinition("Tasseling",     0.50, 0.60, description="VT pollination"),
            GrowthStageDefinition("Silking",       0.60, 0.70, description="R1 silk emergence"),
            GrowthStageDefinition("Grain Filling", 0.70, 0.88, description="R3-R5 blister/dough/dent"),
            GrowthStageDefinition("Maturity",      0.88, 0.95, description="R6 physiological maturity"),
            GrowthStageDefinition("Harvest Ready", 0.95, 1.00, description="Ready for harvest"),
        ],
    ),
    # ── Wheat ─────────────────────────────────────────────────────────────────
    "wheat": CropPhenologyConfig(
        crop_name="Wheat",
        growing_season_days=120,
        base_temperature_c=0.0,
        notes="SOURCE=phenology_config. Validate with local variety / climate zone.",
        stages=[
            GrowthStageDefinition("Germination",   0.00, 0.06, description="Seed germination"),
            GrowthStageDefinition("Seedling",      0.06, 0.18, description="Tillering begins"),
            GrowthStageDefinition("Vegetative",    0.18, 0.45, description="Stem elongation"),
            GrowthStageDefinition("Heading",       0.45, 0.62, description="Heading / ear emergence"),
            GrowthStageDefinition("Flowering",     0.62, 0.72, description="Anthesis"),
            GrowthStageDefinition("Grain Filling", 0.72, 0.88, description="Grain development"),
            GrowthStageDefinition("Maturity",      0.88, 0.95, description="Ripening"),
            GrowthStageDefinition("Harvest Ready", 0.95, 1.00, description="Ready for harvest"),
        ],
    ),
    # ── Tomato ────────────────────────────────────────────────────────────────
    "tomato": CropPhenologyConfig(
        crop_name="Tomato",
        growing_season_days=120,
        base_temperature_c=10.0,
        notes="SOURCE=phenology_config. Validate with local variety / season.",
        stages=[
            GrowthStageDefinition("Germination",      0.00, 0.07),
            GrowthStageDefinition("Seedling",         0.07, 0.20),
            GrowthStageDefinition("Vegetative",       0.20, 0.42),
            GrowthStageDefinition("Flowering",        0.42, 0.60),
            GrowthStageDefinition("Fruit Set",        0.60, 0.75),
            GrowthStageDefinition("Fruit Development",0.75, 0.88),
            GrowthStageDefinition("Maturity",         0.88, 0.95),
            GrowthStageDefinition("Harvest Ready",    0.95, 1.00),
        ],
    ),
    # ── Potato ────────────────────────────────────────────────────────────────
    "potato": CropPhenologyConfig(
        crop_name="Potato",
        growing_season_days=100,
        base_temperature_c=7.0,
        notes="SOURCE=phenology_config. Validate with local variety / seed type.",
        stages=[
            GrowthStageDefinition("Sprouting",         0.00, 0.12),
            GrowthStageDefinition("Vegetative",        0.12, 0.35),
            GrowthStageDefinition("Tuber Initiation",  0.35, 0.55),
            GrowthStageDefinition("Tuber Bulking",     0.55, 0.80),
            GrowthStageDefinition("Maturation",        0.80, 0.93),
            GrowthStageDefinition("Harvest Ready",     0.93, 1.00),
        ],
    ),
    # ── Soybean ───────────────────────────────────────────────────────────────
    "soybean": CropPhenologyConfig(
        crop_name="Soybean",
        growing_season_days=100,
        base_temperature_c=10.0,
        notes="SOURCE=phenology_config. Validate with local maturity group.",
        stages=[
            GrowthStageDefinition("Germination",   0.00, 0.08),
            GrowthStageDefinition("Seedling",      0.08, 0.22),
            GrowthStageDefinition("Vegetative",    0.22, 0.48),
            GrowthStageDefinition("Flowering",     0.48, 0.65),
            GrowthStageDefinition("Pod Fill",      0.65, 0.82),
            GrowthStageDefinition("Seed Fill",     0.82, 0.92),
            GrowthStageDefinition("Maturity",      0.92, 0.96),
            GrowthStageDefinition("Harvest Ready", 0.96, 1.00),
        ],
    ),
    # ── Cotton ────────────────────────────────────────────────────────────────
    "cotton": CropPhenologyConfig(
        crop_name="Cotton",
        growing_season_days=160,
        base_temperature_c=15.0,
        notes="SOURCE=phenology_config. Validate with local cultivar / region.",
        stages=[
            GrowthStageDefinition("Germination",   0.00, 0.06),
            GrowthStageDefinition("Seedling",      0.06, 0.18),
            GrowthStageDefinition("Squaring",      0.18, 0.38),
            GrowthStageDefinition("Flowering",     0.38, 0.58),
            GrowthStageDefinition("Boll Set",      0.58, 0.74),
            GrowthStageDefinition("Boll Opening",  0.74, 0.90),
            GrowthStageDefinition("Harvest Ready", 0.90, 1.00),
        ],
    ),
    # ── Sugarcane ─────────────────────────────────────────────────────────────
    "sugarcane": CropPhenologyConfig(
        crop_name="Sugarcane",
        growing_season_days=360,
        base_temperature_c=18.0,
        notes="SOURCE=phenology_config. Long crop; validate with local cycle.",
        stages=[
            GrowthStageDefinition("Germination",   0.00, 0.06),
            GrowthStageDefinition("Tillering",     0.06, 0.25),
            GrowthStageDefinition("Grand Growth",  0.25, 0.65),
            GrowthStageDefinition("Ripening",      0.65, 0.88),
            GrowthStageDefinition("Maturity",      0.88, 0.95),
            GrowthStageDefinition("Harvest Ready", 0.95, 1.00),
        ],
    ),
    # ── Coffee ────────────────────────────────────────────────────────────────
    "coffee": CropPhenologyConfig(
        crop_name="Coffee",
        growing_season_days=300,
        base_temperature_c=15.0,
        notes="SOURCE=phenology_config. Perennial; cycle restart after each harvest.",
        stages=[
            GrowthStageDefinition("Flowering",     0.00, 0.12),
            GrowthStageDefinition("Fruit Set",     0.12, 0.30),
            GrowthStageDefinition("Fruit Growth",  0.30, 0.65),
            GrowthStageDefinition("Ripening",      0.65, 0.88),
            GrowthStageDefinition("Maturity",      0.88, 0.95),
            GrowthStageDefinition("Harvest Ready", 0.95, 1.00),
        ],
    ),
    # ── Banana ────────────────────────────────────────────────────────────────
    "banana": CropPhenologyConfig(
        crop_name="Banana",
        growing_season_days=330,
        base_temperature_c=15.0,
        notes="SOURCE=phenology_config. Validate per cultivar and altitude.",
        stages=[
            GrowthStageDefinition("Establishment",  0.00, 0.12),
            GrowthStageDefinition("Vegetative",     0.12, 0.50),
            GrowthStageDefinition("Flowering",      0.50, 0.65),
            GrowthStageDefinition("Fruit Fill",     0.65, 0.85),
            GrowthStageDefinition("Maturity",       0.85, 0.94),
            GrowthStageDefinition("Harvest Ready",  0.94, 1.00),
        ],
    ),
    # ── Mango ─────────────────────────────────────────────────────────────────
    "mango": CropPhenologyConfig(
        crop_name="Mango",
        growing_season_days=120,
        base_temperature_c=15.0,
        notes="SOURCE=phenology_config. Season from flowering to harvest only.",
        stages=[
            GrowthStageDefinition("Flowering",     0.00, 0.15),
            GrowthStageDefinition("Fruit Set",     0.15, 0.35),
            GrowthStageDefinition("Fruit Growth",  0.35, 0.72),
            GrowthStageDefinition("Ripening",      0.72, 0.90),
            GrowthStageDefinition("Harvest Ready", 0.90, 1.00),
        ],
    ),
    # ── Generic fallback ──────────────────────────────────────────────────────
    "generic": CropPhenologyConfig(
        crop_name="Generic",
        growing_season_days=90,
        base_temperature_c=10.0,
        notes="SOURCE=phenology_config. Generic fallback — replace with crop-specific config.",
        stages=_build_generic_stages(90),
    ),
}


# ─────────────────────────────────────────────
#  Phenology Engine
# ─────────────────────────────────────────────

class PhenologyEngine:
    """Determines the current growth stage and GDD metrics for a crop cycle.

    Design rules
    ────────────
    1. Source of truth for ``days_since_planting``:
       ``current_date - planting_date`` — never a stored/static counter.
    2. Stage detection method A (default): day-fraction of season length.
    3. Stage detection method B (future): accumulated GDD vs. crop GDD thresholds.
       Activates automatically when ``accumulated_gdd`` is provided.
    4. Neither source fabricates data — if inputs are unavailable the engine
       returns explicit ``"Unknown"`` / ``None`` values.
    """

    def __init__(self, custom_configs: Optional[Dict[str, CropPhenologyConfig]] = None) -> None:
        self._configs: Dict[str, CropPhenologyConfig] = {**DEFAULT_CROP_CONFIGS}
        if custom_configs:
            self._configs.update({k.lower(): v for k, v in custom_configs.items()})

    # ── Public API ────────────────────────────────────────────────────────────

    def get_config(self, crop_name: str) -> CropPhenologyConfig:
        """Return phenology config for *crop_name* (falls back to generic)."""
        key = crop_name.lower().strip()
        return self._configs.get(key, self._configs["generic"])

    def register_config(self, config: CropPhenologyConfig) -> None:
        """Register a custom / overriding phenology config at runtime."""
        self._configs[config.crop_name.lower()] = config
        logger.info("Phenology config registered for %s", config.crop_name)

    def current_stage(
        self,
        crop_name: str,
        days_since_planting: int,
        accumulated_gdd: Optional[float] = None,
    ) -> Dict:
        """Compute the current growth stage.

        Parameters
        ----------
        crop_name:
            Crop type string (matched case-insensitively to config library).
        days_since_planting:
            Real calculated days — ``(today - planting_date).days``.
        accumulated_gdd:
            Accumulated GDD if weather data is available; ``None`` otherwise.

        Returns
        -------
        dict with keys:
            stage_name, stage_index, stage_description,
            stage_fraction, detection_method,
            season_days, days_since_planting,
            accumulated_gdd (or None),
            source (always = "phenology_engine / calculated")
        """
        config = self.get_config(crop_name)
        stage, idx, method = self._detect_stage(config, days_since_planting, accumulated_gdd)
        fraction = days_since_planting / config.growing_season_days if config.growing_season_days > 0 else 0.0

        return {
            "stage_name": stage.name if stage else "Unknown",
            "stage_index": idx,
            "stage_description": stage.description if stage else "",
            "stage_fraction": round(min(fraction, 1.0), 4),
            "detection_method": method,
            "season_days": config.growing_season_days,
            "days_since_planting": days_since_planting,
            "accumulated_gdd": round(accumulated_gdd, 2) if accumulated_gdd is not None else None,
            "source": "phenology_engine / calculated",
            "source_note": (
                "Stage determined from days-since-planting using crop-specific phenology config. "
                "GDD-based detection is architecture-ready but requires validated thresholds. "
                "SOURCE = phenology_config (requires agronomic validation)"
            ),
        }

    def compute_daily_gdd(self, t_min_c: float, t_max_c: float, base_temp_c: float) -> float:
        """Compute daily GDD from min/max temperature.

        Formula: GDD = max(0, ((T_max + T_min) / 2) - T_base)

        SOURCE = weather/sensor data + calculation
        """
        t_mean = (t_min_c + t_max_c) / 2.0
        return max(0.0, t_mean - base_temp_c)

    def list_stages(self, crop_name: str) -> List[Dict]:
        """Return ordered stage list for *crop_name*."""
        config = self.get_config(crop_name)
        return [
            {
                "index": i,
                "name": s.name,
                "day_fraction_start": s.day_fraction_start,
                "day_fraction_end": s.day_fraction_end,
                "day_start": int(s.day_fraction_start * config.growing_season_days),
                "day_end": int(s.day_fraction_end * config.growing_season_days),
                "description": s.description,
            }
            for i, s in enumerate(config.stages)
        ]

    def supported_crops(self) -> List[str]:
        """Return list of crops with dedicated phenology configs."""
        return sorted(k for k in self._configs.keys() if k != "generic")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _detect_stage(
        self,
        config: CropPhenologyConfig,
        days: int,
        accumulated_gdd: Optional[float],
    ):
        """Return (stage_definition, stage_index, detection_method)."""

        # Prefer GDD detection when thresholds are configured AND GDD is available
        if accumulated_gdd is not None:
            gdd_stage, gdd_idx = self._detect_by_gdd(config, accumulated_gdd)
            if gdd_stage is not None:
                return gdd_stage, gdd_idx, "accumulated_gdd"

        # Fall back to day-fraction detection
        stage, idx = self._detect_by_days(config, days)
        return stage, idx, "day_fraction"

    def _detect_by_days(self, config: CropPhenologyConfig, days: int):
        if not config.stages:
            return None, -1
        fraction = days / config.growing_season_days if config.growing_season_days > 0 else 0.0
        fraction = max(0.0, fraction)
        for i, stage in enumerate(config.stages):
            if stage.day_fraction_start <= fraction < stage.day_fraction_end:
                return stage, i
        # Past the last stage boundary → return last stage
        return config.stages[-1], len(config.stages) - 1

    def _detect_by_gdd(self, config: CropPhenologyConfig, accumulated_gdd: float):
        """Return (stage, index) if GDD thresholds are configured; else (None, -1)."""
        for i, stage in enumerate(config.stages):
            if stage.gdd_threshold_start is None:
                return None, -1  # thresholds not configured → skip GDD method
            if stage.gdd_threshold_end is None:
                continue
            if stage.gdd_threshold_start <= accumulated_gdd < stage.gdd_threshold_end:
                return stage, i
        return None, -1
