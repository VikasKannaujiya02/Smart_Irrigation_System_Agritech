"""Metrics for evaluating irrigation prediction models."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    mean_absolute_percentage_error,
    r2_score,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)

logger = logging.getLogger(__name__)


def calculate_regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate regression metrics.

    Args:
        y_true: True target values.
        y_pred: Predicted target values.

    Returns:
        Dictionary of metrics.
    """
    y_true_flat = y_true.flatten()
    y_pred_flat = y_pred.flatten()

    # Filter out NaN values
    mask = ~np.isnan(y_true_flat) & ~np.isnan(y_pred_flat)
    y_true_clean = y_true_flat[mask]
    y_pred_clean = y_pred_flat[mask]

    if len(y_true_clean) < 2:
        logger.warning("Not enough valid samples for metrics calculation")
        return {}

    metrics = {
        "mae": float(mean_absolute_error(y_true_clean, y_pred_clean)),
        "mse": float(mean_squared_error(y_true_clean, y_pred_clean)),
        "rmse": float(np.sqrt(mean_squared_error(y_true_clean, y_pred_clean))),
        "mape": float(mean_absolute_percentage_error(y_true_clean + 1e-8, y_pred_clean + 1e-8)),  # Avoid division by zero
        "r2": float(r2_score(y_true_clean, y_pred_clean)),
        "max_error": float(np.max(np.abs(y_true_clean - y_pred_clean))),
    }

    return metrics


def calculate_classification_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: Optional[np.ndarray] = None) -> Dict[str, float]:
    """Calculate classification metrics.

    Args:
        y_true: True class labels.
        y_pred: Predicted class labels.
        y_prob: Predicted probabilities (optional).

    Returns:
        Dictionary of metrics.
    """
    y_true_flat = y_true.flatten().astype(int)
    y_pred_flat = y_pred.flatten().astype(int)

    metrics = {
        "accuracy": float(accuracy_score(y_true_flat, y_pred_flat)),
        "precision": float(precision_score(y_true_flat, y_pred_flat, zero_division=0)),
        "recall": float(recall_score(y_true_flat, y_pred_flat, zero_division=0)),
        "f1": float(f1_score(y_true_flat, y_pred_flat, zero_division=0)),
    }

    if y_prob is not None:
        try:
            metrics["roc_auc"] = float(roc_auc_score(y_true_flat, y_prob.flatten()))
        except Exception:
            pass

    return metrics


def calculate_horizon_metrics(y_true: np.ndarray, y_pred: np.ndarray, horizon_names: Optional[List[str]] = None) -> Dict[str, Dict[str, float]]:
    """Calculate metrics per prediction horizon.

    Args:
        y_true: True values with shape (n_samples, n_horizons).
        y_pred: Predicted values with shape (n_samples, n_horizons).
        horizon_names: Optional names for each horizon.

    Returns:
        Dictionary with horizon names as keys and metrics as values.
    """
    n_horizons = y_true.shape[1] if len(y_true.shape) > 1 else 1

    if horizon_names is None:
        horizon_names = [f"horizon_{i+1}" for i in range(n_horizons)]

    horizon_metrics = {}

    for i, name in enumerate(horizon_names):
        if len(y_true.shape) > 1:
            y_t = y_true[:, i]
            y_p = y_pred[:, i]
        else:
            y_t = y_true
            y_p = y_pred
            name = "single_horizon"

        horizon_metrics[name] = calculate_regression_metrics(y_t, y_p)

    return horizon_metrics


def summarize_metrics(metrics_list: List[Dict[str, float]]) -> Dict[str, float]:
    """Summarize a list of metrics dictionaries.

    Args:
        metrics_list: List of metrics dictionaries.

    Returns:
        Summary with mean, std, min, max of each metric.
    """
    if not metrics_list:
        return {}

    summary = {}
    keys = metrics_list[0].keys()

    for key in keys:
        values = [m[key] for m in metrics_list if key in m]
        summary[f"{key}_mean"] = float(np.mean(values))
        summary[f"{key}_std"] = float(np.std(values))
        summary[f"{key}_min"] = float(np.min(values))
        summary[f"{key}_max"] = float(np.max(values))

    return summary
