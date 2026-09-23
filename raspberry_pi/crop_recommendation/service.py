"""Live crop recommendation service backed by the trained XGBoost model."""

from __future__ import annotations

import csv
import json
import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CropRecommendationResult:
    """Dashboard-ready crop recommendation result."""

    status: str
    message: str
    input_features: Dict[str, Optional[float]]
    top_crops: List[Dict[str, Any]]
    selected_crop: Optional[Dict[str, Any]]
    agronomic_context: Dict[str, Any]


class CropRecommendationService:
    """Loads crop recommendation artifacts without modifying production AI models."""

    DEFAULT_MODEL_DIR = (
        Path(__file__).resolve().parents[2]
        / "HYBRID TCN + LSTM MODEL"
        / "Models"
        / "Crop_recommendation"
    )

    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = Path(model_dir) if model_dir else self.DEFAULT_MODEL_DIR
        self.features = self._read_feature_order()
        self.crop_profiles = self._read_crop_profiles()
        self.water_requirements = self._read_water_requirements()
        self.system_config = self._read_system_config()
        self.model = self._load_pickle("xgboost_crop_model.pkl")
        self.label_encoder = self._load_optional_pickle("crop_label_encoder.pkl")

    def recommend(
        self,
        npk_row: Optional[Dict[str, Any]],
        weather_context: Optional[Dict[str, Any]] = None,
        top_n: int = 5,
    ) -> CropRecommendationResult:
        if not npk_row:
            return CropRecommendationResult(
                status="no_data",
                message="No live NPK sensor record is available.",
                input_features={feature: None for feature in self.features},
                top_crops=[],
                selected_crop=None,
                agronomic_context=self._context(None, weather_context),
            )

        input_features = self._build_feature_vector(npk_row)
        missing = [name for name, value in input_features.items() if value is None]
        if missing:
            return CropRecommendationResult(
                status="missing_fields",
                message=f"Missing live sensor fields: {', '.join(missing)}",
                input_features=input_features,
                top_crops=[],
                selected_crop=None,
                agronomic_context=self._context(None, weather_context),
            )

        try:
            vector = np.array([[float(input_features[name]) for name in self.features]], dtype=float)
            probabilities = self.model.predict_proba(vector)[0]
            classes = self._classes()
            ranked = sorted(
                (
                    self._crop_entry(crop, float(probabilities[index]), weather_context)
                    for index, crop in enumerate(classes)
                ),
                key=lambda item: item["probability"],
                reverse=True,
            )[:top_n]
        except Exception as exc:
            logger.exception("Crop recommendation failed")
            return CropRecommendationResult(
                status="error",
                message=str(exc),
                input_features=input_features,
                top_crops=[],
                selected_crop=None,
                agronomic_context=self._context(None, weather_context),
            )

        selected = ranked[0] if ranked else None
        return CropRecommendationResult(
            status="live",
            message="Recommendation generated from live NPK sensor data.",
            input_features=input_features,
            top_crops=ranked,
            selected_crop=selected,
            agronomic_context=self._context(selected, weather_context),
        )

    def _build_feature_vector(self, row: Dict[str, Any]) -> Dict[str, Optional[float]]:
        mapping = {
            "N": row.get("nitrogen_mg_kg"),
            "P": row.get("phosphorus_mg_kg"),
            "K": row.get("potassium_mg_kg"),
            "EC": row.get("electrical_conductivity"),
            "pH": row.get("ph"),
            "Soil_Moisture": row.get("moisture_percent"),
            "Soil_Temperature": row.get("soil_temperature_c"),
        }
        return {feature: self._float_or_none(mapping.get(feature)) for feature in self.features}

    def _crop_entry(
        self,
        crop: str,
        probability: float,
        weather_context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        water_requirement = self.water_requirements.get(crop)
        rain_7d = self._float_or_none((weather_context or {}).get("forecast_rainfall_7d_mm"))
        adjusted_water = water_requirement
        if water_requirement is not None and rain_7d is not None:
            adjusted_water = max(water_requirement - (rain_7d / 7.0), 0.0)

        return {
            "crop": crop,
            "probability": round(probability * 100.0, 2),
            "water_requirement_mm_day": water_requirement,
            "weather_adjusted_water_mm_day": round(adjusted_water, 2) if adjusted_water is not None else None,
            "ideal_profile": self.crop_profiles.get(crop, {}),
        }

    def _context(
        self,
        selected_crop: Optional[Dict[str, Any]],
        weather_context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        context = dict(weather_context or {})
        context["weather_used_for_model_input"] = False
        context["weather_used_for_downstream_scoring"] = True
        context["selected_crop_water_requirement_mm_day"] = (
            selected_crop.get("water_requirement_mm_day") if selected_crop else None
        )
        context["selected_crop_adjusted_water_mm_day"] = (
            selected_crop.get("weather_adjusted_water_mm_day") if selected_crop else None
        )
        return context

    def _classes(self) -> List[str]:
        if self.label_encoder is not None and hasattr(self.label_encoder, "classes_"):
            return [str(item) for item in self.label_encoder.classes_]
        return [str(item) for item in self.system_config.get("crop_classes", [])]

    def _read_feature_order(self) -> List[str]:
        path = self.model_dir / "model_features.csv"
        with path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            return [row["Feature"] for row in reader]

    def _read_crop_profiles(self) -> Dict[str, Dict[str, float]]:
        path = self.model_dir / "crop_sensor_profiles.csv"
        with path.open("r", newline="", encoding="utf-8") as handle:
            return {
                row["Crop"]: {key: float(value) for key, value in row.items() if key != "Crop"}
                for row in csv.DictReader(handle)
            }

    def _read_water_requirements(self) -> Dict[str, float]:
        path = self.model_dir / "crop_water_requirement.csv"
        with path.open("r", newline="", encoding="utf-8") as handle:
            return {
                row["Crop"]: float(row["Water_Requirement"])
                for row in csv.DictReader(handle)
            }

    def _read_system_config(self) -> Dict[str, Any]:
        path = self.model_dir / "system_config.json"
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _load_pickle(self, name: str):
        path = self.model_dir / name
        with path.open("rb") as handle:
            return pickle.load(handle)

    def _load_optional_pickle(self, name: str):
        try:
            return self._load_pickle(name)
        except Exception as exc:
            logger.warning("%s unavailable, using system_config crop classes: %s", name, exc)
            return None

    @staticmethod
    def _float_or_none(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
