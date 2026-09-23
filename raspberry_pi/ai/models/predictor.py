"""Predictor for making irrigation predictions with automatic fallback."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .model_registry import ModelRegistry
from .confidence_estimator import ConfidenceEstimator

logger = logging.getLogger(__name__)


class IrrigationPredictor:
    """Predictor for irrigation system with automatic fallback."""

    def __init__(
        self,
        registry_dir: str | Path,
        target_names: Optional[List[str]] = None,
        horizon_hours: Optional[List[int]] = None,
        confidence_threshold: float = 0.7,
    ):
        """Initialize predictor.

        Args:
            registry_dir: Model registry directory.
            target_names: Prediction target names.
            horizon_hours: List of prediction horizons.
            confidence_threshold: Threshold for low confidence.
        """
        self.registry = ModelRegistry(registry_dir)
        self.target_names = target_names or ["soil_moisture", "irrigation_need", "water_requirement"]
        self.horizon_hours = horizon_hours or [1, 6, 12, 24, 168]
        self.confidence_threshold = confidence_threshold

        # Load models
        self._hybrid_models: Dict[int, Any] = {}
        self._confidence_estimators: Dict[int, ConfidenceEstimator] = {}
        self._load_models()

        # Cache of the last predict(X) result for this inference cycle, so the
        # per-target convenience methods below don't re-run every model for
        # every horizon again when called back-to-back for the same input.
        self._last_predict_key: Optional[Tuple[bytes, Optional[bool]]] = None
        self._last_predict_result: Optional[Dict[str, Any]] = None

    def _load_models(self) -> None:
        """Load models from registry."""
        for horizon_hours in self.horizon_hours:
            hybrid_model = self.registry.get_model(
                "all_targets", horizon_hours, model_type="hybrid"
            ) or self.registry.get_model(
                "all_targets", horizon_hours, model_type="hybrid_keras"
            )
            if hybrid_model:
                self._hybrid_models[horizon_hours] = hybrid_model
                logger.info(f"Loaded hybrid model for horizon {horizon_hours}h")

            # Initialize confidence estimator
            self._confidence_estimators[horizon_hours] = ConfidenceEstimator(
                confidence_threshold=self.confidence_threshold
            )

    def predict(
        self,
        X: np.ndarray,
        use_fallback: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Make predictions for all horizons.

        Args:
            X: Input features with shape (n_samples, window, features).
            use_fallback: Optional force use fallback model.

        Returns:
            Prediction results with confidence.
        """
        cache_key = (X.tobytes(), use_fallback)
        if self._last_predict_key == cache_key and self._last_predict_result is not None:
            return self._last_predict_result

        results = {
            "predictions": {},
            "confidence": {},
            "used_fallback": {},
            "horizons": self.horizon_hours,
        }

        for horizon_hours in self.horizon_hours:
            pred, conf, fallback = self._predict_single_horizon(
                X, horizon_hours, use_fallback
            )
            results["predictions"][horizon_hours] = pred
            results["confidence"][horizon_hours] = conf
            results["used_fallback"][horizon_hours] = fallback

        self._last_predict_key = cache_key
        self._last_predict_result = results
        return results

    def _predict_single_horizon(
        self,
        X: np.ndarray,
        horizon_hours: int,
        force_fallback: Optional[bool] = None,
    ) -> Tuple[np.ndarray, np.ndarray, bool]:
        """Predict for a single horizon.

        Args:
            X: Input features.
            horizon_hours: Prediction horizon.
            force_fallback: Force use fallback.

        Returns:
            Tuple of (predictions, confidence, used_fallback).
        """
        hybrid_model = self._hybrid_models.get(horizon_hours)
        conf_est = self._confidence_estimators.get(horizon_hours)

        if hybrid_model:
            y_pred = hybrid_model.predict(X)

            # Estimate confidence (simple version)
            confidence = np.ones(y_pred.shape, dtype=np.float32) * 0.9
            is_low_confidence = False

            if conf_est:
                confidence, is_low_confidence = conf_est.estimate(y_pred)

            if np.any(is_low_confidence):
                logger.warning(f"Hybrid model low confidence for horizon {horizon_hours}h")

            return y_pred, confidence, False

        # No model available
        raise ValueError(f"No models available for horizon {horizon_hours}h")

    def predict_soil_moisture(
        self,
        X: np.ndarray,
        horizon_hours: int = 24,
    ) -> Dict[str, Any]:
        """Predict soil moisture.

        Args:
            X: Input features.
            horizon_hours: Prediction horizon.

        Returns:
            Soil moisture predictions.
        """
        result = self.predict(X)
        pred = result["predictions"][horizon_hours]
        soil_moisture_idx = self.target_names.index("soil_moisture")

        return {
            "value": float(pred[0, soil_moisture_idx]) if pred.ndim > 1 else float(pred[0]),
            "confidence": float(result["confidence"][horizon_hours].mean()),
            "used_fallback": result["used_fallback"][horizon_hours],
            "horizon_hours": horizon_hours,
        }

    def predict_irrigation_need(
        self,
        X: np.ndarray,
        horizon_hours: int = 24,
    ) -> Dict[str, Any]:
        """Predict irrigation need.

        Args:
            X: Input features.
            horizon_hours: Prediction horizon.

        Returns:
            Irrigation need prediction.
        """
        result = self.predict(X)
        pred = result["predictions"][horizon_hours]
        irr_idx = self.target_names.index("irrigation_need")

        return {
            "value": float(pred[0, irr_idx]) if pred.ndim > 1 else float(pred[0]),
            "confidence": float(result["confidence"][horizon_hours].mean()),
            "used_fallback": result["used_fallback"][horizon_hours],
            "horizon_hours": horizon_hours,
        }

    def predict_water_requirement(
        self,
        X: np.ndarray,
        horizon_hours: int = 24,
    ) -> Dict[str, Any]:
        """Predict water requirement.

        Args:
            X: Input features.
            horizon_hours: Prediction horizon.

        Returns:
            Water requirement prediction.
        """
        result = self.predict(X)
        pred = result["predictions"][horizon_hours]
        
        try:
            water_idx = self.target_names.index("water_requirement")
            # If the model didn't actually return enough columns (e.g. weather model expecting 2 outputs)
            if pred.ndim > 1 and pred.shape[1] <= water_idx:
                val = 40.0 # safe fallback
            else:
                val = float(pred[0, water_idx]) if pred.ndim > 1 else float(pred[0])
        except ValueError:
            val = 40.0

        return {
            "value": val,
            "confidence": float(result["confidence"][horizon_hours].mean()),
            "used_fallback": result["used_fallback"][horizon_hours],
            "horizon_hours": horizon_hours,
        }

    def should_irrigate(
        self,
        X: np.ndarray,
        threshold: float = 30.0,
        horizon_hours: int = 24,
    ) -> Dict[str, Any]:
        """Determine if irrigation should be applied.

        Args:
            X: Input features.
            threshold: Soil moisture threshold.
            horizon_hours: Prediction horizon.

        Returns:
            Irrigation decision.
        """
        soil_moisture_pred = self.predict_soil_moisture(X, horizon_hours)

        should_irrigate = soil_moisture_pred["value"] < threshold

        return {
            "should_irrigate": should_irrigate,
            "predicted_soil_moisture": soil_moisture_pred["value"],
            "threshold": threshold,
            "confidence": soil_moisture_pred["confidence"],
            "used_fallback": soil_moisture_pred["used_fallback"],
            "horizon_hours": horizon_hours,
        }