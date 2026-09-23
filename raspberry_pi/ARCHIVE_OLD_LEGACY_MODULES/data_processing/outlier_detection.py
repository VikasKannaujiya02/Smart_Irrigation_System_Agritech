
"""Outlier detection for irrigation system sensor data."""

from __future__ import annotations

import logging
from typing import Literal, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class OutlierDetector:
    """Detects and handles outliers in sensor and NPK data."""

    def __init__(
        self,
        method: Literal["iqr", "zscore"] = "iqr",
        iqr_factor: float = 1.5,
        zscore_threshold: float = 3.0,
        action: Literal["remove", "cap", "flag"] = "remove"
    ):
        self.method = method
        self.iqr_factor = iqr_factor
        self.zscore_threshold = zscore_threshold
        self.action = action
        self._bounds: Optional[dict[str, tuple[float, float]]] = None

    def fit(self, data: pd.DataFrame) -> "OutlierDetector":
        """Compute outlier bounds using training data."""
        numeric_cols = data.select_dtypes(include=["number"]).columns
        self._bounds = {}
        for col in numeric_cols:
            if self.method == "iqr":
                Q1 = data[col].quantile(0.25)
                Q3 = data[col].quantile(0.75)
                IQR = Q3 - Q1
                lower = Q1 - self.iqr_factor * IQR
                upper = Q3 + self.iqr_factor * IQR
            elif self.method == "zscore":
                mean = data[col].mean()
                std = data[col].std()
                lower = mean - self.zscore_threshold * std
                upper = mean + self.zscore_threshold * std
            self._bounds[col] = (lower, upper)
        return self

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply outlier handling to the data."""
        if self._bounds is None:
            raise ValueError("OutlierDetector not fitted")
        
        data = data.copy()
        for col, (lower, upper) in self._bounds.items():
            if col not in data.columns:
                continue
            mask = (data[col] < lower) | (data[col] > upper)
            if mask.any():
                logger.info(f"Detected {mask.sum()} outliers in column {col}")
                if self.action == "remove":
                    data = data[~mask]
                elif self.action == "cap":
                    data[col] = data[col].clip(lower, upper)
                elif self.action == "flag":
                    data[f"{col}_is_outlier"] = mask
        return data

    def fit_transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform in one step."""
        return self.fit(data).transform(data)

    def get_outlier_counts(self, data: pd.DataFrame) -> pd.DataFrame:
        """Get count of outliers per column."""
        if self._bounds is None:
            raise ValueError("OutlierDetector not fitted")
        
        counts = {}
        numeric_cols = data.select_dtypes(include=["number"]).columns
        for col in numeric_cols:
            if col not in self._bounds:
                continue
            lower, upper = self._bounds[col]
            mask = (data[col] < lower) | (data[col] > upper)
            counts[col] = mask.sum()
        return pd.DataFrame.from_dict(counts, orient="index", columns=["outlier_count"])
