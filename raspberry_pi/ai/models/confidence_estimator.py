"""Confidence estimation for model predictions."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class ConfidenceEstimator:
    """Estimates confidence in model predictions."""

    def __init__(
        self,
        method: str = "ensemble_variance",
        confidence_threshold: float = 0.7,
        calibration_factor: float = 1.0,
    ):
        """Initialize confidence estimator.

        Args:
            method: Confidence estimation method ('ensemble_variance', 'mc_dropout', 'error_model').
            confidence_threshold: Threshold for low confidence.
            calibration_factor: Calibration factor for confidence scores.
        """
        self.method = method
        self.confidence_threshold = confidence_threshold
        self.calibration_factor = calibration_factor
        self._calibration_data: Optional[Tuple[np.ndarray, np.ndarray]] = None
        self._error_stats: Optional[Dict[str, float]] = None

    def fit(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_pred_std: Optional[np.ndarray] = None,
    ) -> ConfidenceEstimator:
        """Fit confidence estimator using validation data.

        Args:
            y_true: True values.
            y_pred: Predicted values.
            y_pred_std: Optional prediction standard deviations.

        Returns:
            Self.
        """
        errors = np.abs(y_true - y_pred)
        self._error_stats = {
            "mean_abs_error": float(np.mean(errors)),
            "std_abs_error": float(np.std(errors)),
            "max_abs_error": float(np.max(errors)),
        }

        if y_pred_std is not None:
            self._calibration_data = (y_pred_std.flatten(), errors.flatten())

        logger.info(f"Confidence estimator fitted with error stats: {self._error_stats}")
        return self

    def estimate(
        self,
        y_pred: np.ndarray,
        y_pred_std: Optional[np.ndarray] = None,
        ensemble_predictions: Optional[List[np.ndarray]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Estimate confidence for predictions.

        Args:
            y_pred: Mean predictions.
            y_pred_std: Optional prediction standard deviations.
            ensemble_predictions: Optional list of predictions from ensemble.

        Returns:
            Tuple of (confidence_scores, is_low_confidence).
        """
        if self.method == "ensemble_variance" and ensemble_predictions is not None:
            confidence = self._ensemble_variance(ensemble_predictions)
        elif self.method == "mc_dropout" and y_pred_std is not None:
            confidence = self._mc_dropout(y_pred_std)
        else:
            confidence = self._error_based(y_pred)

        confidence = np.clip(confidence * self.calibration_factor, 0, 1)
        is_low_confidence = confidence < self.confidence_threshold

        return confidence, is_low_confidence

    def _ensemble_variance(self, ensemble_predictions: List[np.ndarray]) -> np.ndarray:
        """Estimate confidence using ensemble variance.

        Args:
            ensemble_predictions: List of predictions from ensemble members.

        Returns:
            Confidence scores.
        """
        pred_array = np.array(ensemble_predictions)
        pred_std = np.std(pred_array, axis=0)

        if self._error_stats:
            normalized_std = pred_std / (self._error_stats["std_abs_error"] + 1e-8)
            confidence = np.exp(-normalized_std)
        else:
            max_std = np.max(pred_std) + 1e-8
            confidence = 1 - (pred_std / max_std)

        return confidence

    def _mc_dropout(self, y_pred_std: np.ndarray) -> np.ndarray:
        """Estimate confidence using MC dropout standard deviation.

        Args:
            y_pred_std: Prediction standard deviations.

        Returns:
            Confidence scores.
        """
        if self._error_stats:
            normalized_std = y_pred_std / (self._error_stats["std_abs_error"] + 1e-8)
            confidence = np.exp(-normalized_std)
        else:
            max_std = np.max(y_pred_std) + 1e-8
            confidence = 1 - (y_pred_std / max_std)

        return confidence

    def _error_based(self, y_pred: np.ndarray) -> np.ndarray:
        """Estimate confidence based on prediction magnitude.

        Args:
            y_pred: Predictions.

        Returns:
            Confidence scores.
        """
        confidence = np.ones_like(y_pred, dtype=np.float32)
        if self._error_stats:
            mean_pred = np.mean(np.abs(y_pred))
            normalized_pred = mean_pred / (self._error_stats["mean_abs_error"] + 1e-8)
            confidence = confidence * (1 - np.exp(-normalized_pred))

        return confidence

    def should_fallback(self, confidence: np.ndarray) -> bool:
        """Check if we should fall back to XGBoost.

        Args:
            confidence: Confidence scores.

        Returns:
            True if we should fall back.
        """
        mean_confidence = float(np.mean(confidence))
        return mean_confidence < self.confidence_threshold

    def get_config(self) -> Dict[str, Any]:
        """Get configuration.

        Returns:
            Config dictionary.
        """
        return {
            "method": self.method,
            "confidence_threshold": self.confidence_threshold,
            "calibration_factor": self.calibration_factor,
            "error_stats": self._error_stats,
        }
