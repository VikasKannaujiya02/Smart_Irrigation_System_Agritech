"""XGBoost fallback model for irrigation prediction."""

from __future__ import annotations

import logging
import os
import pickle
from typing import Any, Dict, List, Optional

import numpy as np
import xgboost as xgb
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class XGBoostFallbackModel:
    """XGBoost fallback model for irrigation prediction."""

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 6,
        learning_rate: float = 0.1,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        random_state: int = 42,
        target_names: Optional[List[str]] = None,
        horizon: int = 1,
    ):
        """Initialize XGBoost model.

        Args:
            n_estimators: Number of boosting trees.
            max_depth: Maximum depth of trees.
            learning_rate: Learning rate.
            subsample: Subsample ratio.
            colsample_bytree: Feature subsample ratio.
            random_state: Random state.
            target_names: Names of target features.
            horizon: Prediction horizon.
        """
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.random_state = random_state
        self.target_names = target_names
        self.horizon = horizon
        self._model: Optional[MultiOutputRegressor] = None
        self._scaler: Optional[StandardScaler] = None
        self._feature_names: Optional[List[str]] = None

    def _flatten_input(self, X: np.ndarray) -> np.ndarray:
        """Flatten 3D input (n_samples, window, features) to 2D.

        Args:
            X: Input array with shape (n_samples, window, features).

        Returns:
            Flattened array with shape (n_samples, window * features).
        """
        if len(X.shape) == 3:
            return X.reshape(X.shape[0], -1)
        return X

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Train the model.

        Args:
            X_train: Training features.
            y_train: Training targets.
            X_val: Validation features (optional).
            y_val: Validation targets (optional).
            feature_names: Optional list of feature names.

        Returns:
            Training metrics.
        """
        self._feature_names = feature_names

        # Flatten input
        X_train_flat = self._flatten_input(X_train)

        # Scale features
        self._scaler = StandardScaler()
        X_train_scaled = self._scaler.fit_transform(X_train_flat)

        # Handle multi-output
        if len(y_train.shape) > 2:
            y_train_reshaped = y_train.reshape(y_train.shape[0], -1)
        else:
            y_train_reshaped = y_train

        # Build model
        xgb_reg = xgb.XGBRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            random_state=self.random_state,
            verbosity=0,
            n_jobs=-1,
        )

        self._model = MultiOutputRegressor(xgb_reg)
        logger.info("Training XGBoost fallback model...")

        self._model.fit(X_train_scaled, y_train_reshaped)

        metrics = {}
        if X_val is not None and y_val is not None:
            X_val_flat = self._flatten_input(X_val)
            X_val_scaled = self._scaler.transform(X_val_flat)
            val_pred = self._model.predict(X_val_scaled)
            metrics["val_r2"] = float(self._model.score(X_val_scaled, y_val_reshaped))
            logger.info(f"XGBoost validation R²: {metrics['val_r2']:.4f}")

        return metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions.

        Args:
            X: Input features.

        Returns:
            Predictions.
        """
        if self._model is None or self._scaler is None:
            raise ValueError("Model not trained")

        X_flat = self._flatten_input(X)
        X_scaled = self._scaler.transform(X_flat)
        y_pred = self._model.predict(X_scaled)

        # Reshape back to original target shape
        if self.horizon > 1 and len(y_pred.shape) == 2:
            n_targets = y_pred.shape[1] // self.horizon
            y_pred = y_pred.reshape(y_pred.shape[0], self.horizon, n_targets)

        return y_pred

    def save(self, path: str) -> None:
        """Save model to disk.

        Args:
            path: Path to save model.
        """
        if self._model is None:
            raise ValueError("Model not trained")

        model_data = {
            "model": self._model,
            "scaler": self._scaler,
            "feature_names": self._feature_names,
            "config": {
                "n_estimators": self.n_estimators,
                "max_depth": self.max_depth,
                "learning_rate": self.learning_rate,
                "subsample": self.subsample,
                "colsample_bytree": self.colsample_bytree,
                "random_state": self.random_state,
                "target_names": self.target_names,
                "horizon": self.horizon,
            },
        }

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(model_data, f)
        logger.info(f"XGBoost model saved to {path}")

    def load(self, path: str) -> None:
        """Load model from disk.

        Args:
            path: Path to model file.
        """
        with open(path, "rb") as f:
            model_data = pickle.load(f)

        self._model = model_data["model"]
        self._scaler = model_data["scaler"]
        self._feature_names = model_data["feature_names"]

        config = model_data["config"]
        self.n_estimators = config["n_estimators"]
        self.max_depth = config["max_depth"]
        self.learning_rate = config["learning_rate"]
        self.subsample = config["subsample"]
        self.colsample_bytree = config["colsample_bytree"]
        self.random_state = config["random_state"]
        self.target_names = config["target_names"]
        self.horizon = config["horizon"]

        logger.info(f"XGBoost model loaded from {path}")

    def get_config(self) -> Dict[str, Any]:
        """Get model configuration.

        Returns:
            Configuration dictionary.
        """
        return {
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "learning_rate": self.learning_rate,
            "subsample": self.subsample,
            "colsample_bytree": self.colsample_bytree,
            "random_state": self.random_state,
            "target_names": self.target_names,
            "horizon": self.horizon,
        }
