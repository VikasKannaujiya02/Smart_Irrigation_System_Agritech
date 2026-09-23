"""Continuous Learning Module for Irrigation System.

This module provides:
- Model, data, sensor drift detectors
- Champion-challenger model framework
- Retraining trigger system
- Model validation
- Rollback capabilities
- Model registry integration
- Automatic dataset updates
"""
from .drift_detectors import (
    DriftDetector,
    ModelDriftDetector,
    DataDriftDetector,
    SensorDriftDetector
)
from .champion_challenger import ChampionChallengerManager
from .retraining_trigger import RetrainingTrigger
from .model_validator import ModelValidator
from .rollback_manager import RollbackManager
from .dataset_updater import DatasetUpdater

__all__ = [
    "DriftDetector",
    "ModelDriftDetector",
    "DataDriftDetector",
    "SensorDriftDetector",
    "ChampionChallengerManager",
    "RetrainingTrigger",
    "ModelValidator",
    "RollbackManager",
    "DatasetUpdater"
]
