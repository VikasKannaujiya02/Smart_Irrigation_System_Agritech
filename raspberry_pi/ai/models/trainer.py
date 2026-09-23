"""Trainer for training and evaluating irrigation prediction models."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .hybrid_model import HybridTCNLSTMModel
from .confidence_estimator import ConfidenceEstimator
from .model_registry import ModelRegistry
from .metrics import calculate_regression_metrics

logger = logging.getLogger(__name__)


class ModelTrainer:
    """Trainer for irrigation prediction models."""

    def __init__(
        self,
        registry_dir: str | Path,
        target_names: Optional[List[str]] = None,
        horizon_hours: Optional[List[int]] = None,
        hyperparameters: Optional[Dict[str, Any]] = None,
    ):
        """Initialize trainer.

        Args:
            registry_dir: Directory for model registry.
            target_names: Names of prediction targets.
            horizon_hours: List of prediction horizons in hours.
            hyperparameters: Optional hyperparameters for models.
        """
        self.registry = ModelRegistry(registry_dir)
        self.target_names = target_names or ["soil_moisture", "irrigation_need", "water_requirement"]
        self.horizon_hours = horizon_hours or [1, 6, 12, 24, 168]  # 1h,6h,12h,24h,7d
        self.hyperparameters = hyperparameters or self._get_default_hyperparams()
        self._confidence_estimators: Dict[str, ConfidenceEstimator] = {}

    def _get_default_hyperparams(self) -> Dict[str, Any]:
        """Get default hyperparameters.

        Returns:
            Default hyperparameters dict.
        """
        return {
            "hybrid": {
                "num_tcn_blocks": 3,
                "tcn_filters": 64,
                "kernel_size": 3,
                "dilation_base": 2,
                "lstm_units": [64],
                "dropout_rate": 0.2,
                "recurrent_dropout": 0.1,
                "learning_rate": 0.001,
                "epochs": 100,
                "batch_size": 32,
            },
        }

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Train all models for all targets and horizons.

        Args:
            X_train: Training features.
            y_train: Training targets.
            X_val: Validation features.
            y_val: Validation targets.
            feature_names: Optional feature names.

        Returns:
            Training results.
        """
        results = {}
        input_shape = (X_train.shape[1], X_train.shape[2])
        output_shape = y_train.shape[2] if len(y_train.shape) > 2 else y_train.shape[1]

        # Train for each horizon
        for horizon_idx, horizon_hours in enumerate(self.horizon_hours):
            logger.info(f"Training for horizon {horizon_hours}h")

            # Extract horizon-specific targets
            y_train_h = y_train[:, horizon_idx, :] if len(y_train.shape) > 2 else y_train
            y_val_h = y_val[:, horizon_idx, :] if len(y_val.shape) > 2 else y_val

            # Train hybrid model
            hybrid_metrics = self._train_hybrid(
                X_train, y_train_h, X_val, y_val_h,
                input_shape, output_shape, horizon_hours, feature_names
            )

            results[horizon_hours] = {
                "hybrid": hybrid_metrics,
            }

        return results

    def _train_hybrid(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        input_shape: Tuple[int, int],
        output_shape: int,
        horizon_hours: int,
        feature_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Train hybrid TCN+LSTM model.

        Args:
            X_train: Training features.
            y_train: Training targets.
            X_val: Validation features.
            y_val: Validation targets.
            input_shape: Input shape.
            output_shape: Output shape.
            horizon_hours: Prediction horizon.
            feature_names: Feature names.

        Returns:
            Training metrics.
        """
        logger.info("Training Hybrid TCN+LSTM model")

        hp = self.hyperparameters["hybrid"]
        model = HybridTCNLSTMModel(
            input_shape=input_shape,
            output_shape=output_shape,
            num_tcn_blocks=hp["num_tcn_blocks"],
            tcn_filters=hp["tcn_filters"],
            kernel_size=hp["kernel_size"],
            dilation_base=hp["dilation_base"],
            lstm_units=hp["lstm_units"],
            dropout_rate=hp["dropout_rate"],
            recurrent_dropout=hp["recurrent_dropout"],
            learning_rate=hp["learning_rate"],
            target_names=self.target_names,
            horizon=1,
        )
        model.build()

        checkpoint_dir = Path(self.registry.registry_dir) / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)
        checkpoint_path = str(checkpoint_dir / f"hybrid_horizon_{horizon_hours}.h5")

        history = model.train(
            X_train, y_train, X_val, y_val,
            epochs=hp["epochs"],
            batch_size=hp["batch_size"],
            checkpoint_path=checkpoint_path,
        )

        # Evaluate
        y_pred = model.predict(X_val)
        metrics = calculate_regression_metrics(y_val, y_pred)
        metrics["history"] = history

        # Register model
        self.registry.register_model(
            model, "hybrid", "all_targets", horizon_hours, metrics,
            config=model.get_config(), set_active=True
        )

        # Fit confidence estimator
        conf_est = ConfidenceEstimator()
        conf_est.fit(y_val, y_pred)
        self._confidence_estimators[f"hybrid_{horizon_hours}"] = conf_est

        logger.info(f"Hybrid model trained. Val MAE: {metrics['mae']:.4f}")
        return metrics

    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
        target: str = "all_targets",
    ) -> Dict[str, Any]:
        """Evaluate models on test set.

        Args:
            X_test: Test features.
            y_test: Test targets.
            target: Target name.

        Returns:
            Evaluation metrics.
        """
        results = {}

        for horizon_hours in self.horizon_hours:
            horizon_results = {}

            # Evaluate hybrid model
            hybrid_model = self.registry.get_model(target, horizon_hours)
            if hybrid_model:
                y_pred = hybrid_model.predict(X_test)
                y_test_h = y_test[:, self.horizon_hours.index(horizon_hours), :] if len(y_test.shape) > 2 else y_test
                horizon_results["hybrid"] = calculate_regression_metrics(y_test_h, y_pred)

            results[horizon_hours] = horizon_results

        return results