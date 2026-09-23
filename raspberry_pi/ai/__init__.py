"""AI module for Smart Irrigation Digital Twin."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "DatasetBuilder": ".data_pipeline",
    "DatasetValidator": ".data_pipeline",
    "DatasetCleaner": ".data_pipeline",
    "DatasetMerger": ".data_pipeline",
    "FeatureExtractor": ".data_pipeline",
    "FeatureSelector": ".data_pipeline",
    "SlidingWindow": ".data_pipeline",
    "Normalizer": ".data_pipeline",
    "TrainTestSplit": ".data_pipeline",
    "DatasetVersionManager": ".data_pipeline",
    "TCNModel": ".models",
    "LSTMModel": ".models",
    "HybridTCNLSTMModel": ".models",
    "XGBoostFallbackModel": ".models",
    "ModelTrainer": ".models",
    "IrrigationPredictor": ".models",
    "InferencePipeline": ".models",
    "ModelRegistry": ".models",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(_EXPORTS[name], __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
