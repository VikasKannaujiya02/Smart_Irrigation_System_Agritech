"""AI Prediction Engine for Irrigation System."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "TCNBlock": ".tcn_model",
    "TCNModel": ".tcn_model",
    "LSTMModel": ".lstm_model",
    "HybridTCNLSTMModel": ".hybrid_model",
    "calculate_regression_metrics": ".metrics",
    "calculate_classification_metrics": ".metrics",
    "calculate_horizon_metrics": ".metrics",
    "summarize_metrics": ".metrics",
    "ConfidenceEstimator": ".confidence_estimator",
    "ModelRegistry": ".model_registry",
    "ModelVersion": ".model_registry",
    "ModelTrainer": ".trainer",
    "IrrigationPredictor": ".predictor",
    "InferencePipeline": ".inference",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(_EXPORTS[name], __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value