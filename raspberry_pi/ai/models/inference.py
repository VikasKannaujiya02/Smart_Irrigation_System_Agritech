"""Inference pipeline for end-to-end predictions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..data_pipeline.normalizer import Normalizer
from .predictor import IrrigationPredictor

logger = logging.getLogger(__name__)


class InferencePipeline:
    """End-to-end inference pipeline for irrigation predictions."""

    def __init__(
        self,
        registry_dir: str | Path,
        config_path: Optional[str | Path] = None,
        window_size: int = 24,
    ):
        """Initialize inference pipeline.

        Args:
            registry_dir: Model registry directory.
            config_path: Path to system config.
            window_size: Input window size.
        """
        self.config_path = config_path
        self.window_size = window_size
        self.predictor = IrrigationPredictor(registry_dir)
        self.normalizer = Normalizer()
        self._data_buffer: List[Dict[str, Any]] = []
        self._normalizer_fitted = False

    def load_normalizer(self, path: str | Path) -> None:
        """Load fitted normalizer from disk.

        Args:
            path: Path to normalizer.
        """
        import pickle
        with open(path, "rb") as f:
            norm_data = pickle.load(f)
            self.normalizer._scalers = norm_data.get("scalers")
            self.normalizer._columns = norm_data.get("columns")
            self._normalizer_fitted = True
        logger.info("Normalizer loaded")

    def add_data_point(self, data: Dict[str, Any]) -> None:
        """Add a single data point to buffer.

        Args:
            data: Data point dict.
        """
        self._data_buffer.append(data)
        if len(self._data_buffer) > self.window_size * 2:
            self._data_buffer = self._data_buffer[-self.window_size * 2 :]

    def add_data_batch(self, data: List[Dict[str, Any]]) -> None:
        """Add batch of data to buffer.

        Args:
            data: List of data points.
        """
        self._data_buffer.extend(data)
        if len(self._data_buffer) > self.window_size * 2:
            self._data_buffer = self._data_buffer[-self.window_size * 2 :]

    def _prepare_input(self) -> Optional[np.ndarray]:
        """Prepare input for model.

        Returns:
            Input array or None.
        """
        if len(self._data_buffer) < self.window_size:
            logger.warning(f"Not enough data. Need {self.window_size}, have {len(self._data_buffer)}")
            return None

        df = pd.DataFrame(self._data_buffer[-self.window_size :])

        # Select numeric features
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        df_numeric = df[numeric_cols].fillna(0)

        # Normalize if fitted
        if self._normalizer_fitted:
            df_normalized = self.normalizer.transform(df_numeric)
        else:
            df_normalized = df_numeric

        X = df_normalized.values.reshape(1, self.window_size, -1)
        return X

    def predict(self) -> Optional[Dict[str, Any]]:
        """Run full prediction pipeline.

        Returns:
            Prediction results or None.
        """
        X = self._prepare_input()
        if X is None:
            return None

        predictions = self.predictor.predict(X)
        return predictions

    def predict_soil_moisture(self, horizon_hours: int = 24) -> Optional[Dict[str, Any]]:
        """Predict soil moisture.

        Args:
            horizon_hours: Prediction horizon.

        Returns:
            Soil moisture prediction.
        """
        X = self._prepare_input()
        if X is None:
            return None

        return self.predictor.predict_soil_moisture(X, horizon_hours)

    def predict_irrigation_need(self, horizon_hours: int = 24) -> Optional[Dict[str, Any]]:
        """Predict irrigation need.

        Args:
            horizon_hours: Prediction horizon.

        Returns:
            Irrigation need prediction.
        """
        X = self._prepare_input()
        if X is None:
            return None

        return self.predictor.predict_irrigation_need(X, horizon_hours)

    def predict_water_requirement(self, horizon_hours: int = 24) -> Optional[Dict[str, Any]]:
        """Predict water requirement.

        Args:
            horizon_hours: Prediction horizon.

        Returns:
            Water requirement prediction.
        """
        X = self._prepare_input()
        if X is None:
            return None

        return self.predictor.predict_water_requirement(X, horizon_hours)

    def should_irrigate(
        self,
        threshold: float = 30.0,
        horizon_hours: int = 24,
    ) -> Optional[Dict[str, Any]]:
        """Get irrigation decision.

        Args:
            threshold: Soil moisture threshold.
            horizon_hours: Prediction horizon.

        Returns:
            Irrigation decision.
        """
        X = self._prepare_input()
        if X is None:
            return None

        return self.predictor.should_irrigate(X, threshold, horizon_hours)

    def clear_buffer(self) -> None:
        """Clear data buffer."""
        self._data_buffer = []
        logger.info("Data buffer cleared")
