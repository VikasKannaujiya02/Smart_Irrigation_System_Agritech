"""Automatic model validation."""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum, auto
import numpy as np

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    PASSED = auto()
    FAILED = auto()
    WARNING = auto()
    SKIPPED = auto()


@dataclass
class ValidationResult:
    """Result of a model validation."""
    model_id: str
    status: ValidationStatus
    timestamp: datetime
    metrics: Dict[str, float] = field(default_factory=dict)
    checks: Dict[str, bool] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ModelValidator:
    """Validates models before and after deployment."""

    def __init__(
        self,
        required_metrics: Optional[List[str]] = None,
        metric_thresholds: Optional[Dict[str, Dict[str, float]]] = None,
        min_inference_samples: int = 100
    ):
        self.required_metrics = required_metrics or ["mae", "rmse", "r2"]
        self.metric_thresholds = metric_thresholds or {}
        self.min_inference_samples = min_inference_samples
        self.validation_history: List[ValidationResult] = []

    def validate(
        self,
        model_id: str,
        metrics: Dict[str, float],
        baseline_metrics: Optional[Dict[str, float]] = None
    ) -> ValidationResult:
        """Validate a model."""
        result = ValidationResult(
            model_id=model_id,
            status=ValidationStatus.PASSED,
            timestamp=datetime.now(),
            metrics=metrics.copy()
        )

        # Check required metrics exist
        for metric in self.required_metrics:
            if metric not in metrics:
                result.errors.append(f"Missing required metric: {metric}")
                result.checks[f"metric_exists_{metric}"] = False
                result.status = ValidationStatus.FAILED
            else:
                result.checks[f"metric_exists_{metric}"] = True

        # Check metric thresholds
        for metric, thresholds in self.metric_thresholds.items():
            if metric in metrics:
                value = metrics[metric]
                if "min" in thresholds and value < thresholds["min"]:
                    result.errors.append(f"Metric {metric} below minimum: {value} < {thresholds['min']}")
                    result.checks[f"metric_threshold_{metric}"] = False
                    result.status = ValidationStatus.FAILED
                elif "max" in thresholds and value > thresholds["max"]:
                    result.errors.append(f"Metric {metric} above maximum: {value} > {thresholds['max']}")
                    result.checks[f"metric_threshold_{metric}"] = False
                    result.status = ValidationStatus.FAILED
                else:
                    result.checks[f"metric_threshold_{metric}"] = True

        # Compare against baseline
        if baseline_metrics:
            for metric in self.required_metrics:
                if metric in metrics and metric in baseline_metrics:
                    base_val = baseline_metrics[metric]
                    curr_val = metrics[metric]
                    if metric in ["mae", "rmse", "mse"]:
                        # Lower is better
                        if curr_val > base_val * 1.2:
                            result.warnings.append(f"Metric {metric} degraded: {curr_val:.3f} > {base_val:.3f}")
                            if result.status == ValidationStatus.PASSED:
                                result.status = ValidationStatus.WARNING
                    else:
                        # Higher is better
                        if curr_val < base_val * 0.8:
                            result.warnings.append(f"Metric {metric} degraded: {curr_val:.3f} < {base_val:.3f}")
                            if result.status == ValidationStatus.PASSED:
                                result.status = ValidationStatus.WARNING

        self.validation_history.append(result)
        logger.info(f"Model {model_id} validation: {result.status.name}")
        return result

    def validate_inference(
        self,
        model_id: str,
        predictions: np.ndarray,
        ground_truth: np.ndarray
    ) -> ValidationResult:
        """Validate model on inference data."""
        if len(predictions) < self.min_inference_samples:
            result = ValidationResult(
                model_id=model_id,
                status=ValidationStatus.SKIPPED,
                timestamp=datetime.now(),
                warnings=[f"Insufficient samples: {len(predictions)} < {self.min_inference_samples}"]
            )
            self.validation_history.append(result)
            return result

        # Calculate metrics
        mae = float(np.mean(np.abs(predictions - ground_truth)))
        rmse = float(np.sqrt(np.mean((predictions - ground_truth) ** 2)))
        y_mean = np.mean(ground_truth)
        ss_total = np.sum((ground_truth - y_mean) ** 2)
        ss_res = np.sum((ground_truth - predictions) ** 2)
        r2 = float(1 - (ss_res / ss_total)) if ss_total != 0 else 0.0

        return self.validate(
            model_id=model_id,
            metrics={"mae": mae, "rmse": rmse, "r2": r2}
        )

    def get_history(self, model_id: Optional[str] = None) -> List[ValidationResult]:
        """Get validation history."""
        if model_id:
            return [r for r in self.validation_history if r.model_id == model_id]
        return self.validation_history
