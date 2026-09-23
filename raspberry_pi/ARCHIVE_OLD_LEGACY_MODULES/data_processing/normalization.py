
"""Feature normalization for irrigation system data."""

from __future__ import annotations

import logging
from typing import Literal, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class Normalizer:
    """Normalizes numerical features for ML models."""

    def __init__(
        self,
        method: Literal["minmax", "standard", "robust"] = "standard"
    ):
        self.method = method
        self._stats: Optional[dict[str, dict[str, float]]] = None

    def fit(self, data: pd.DataFrame) -> "Normalizer":
        """Compute normalization statistics from training data."""
        numeric_cols = data.select_dtypes(include=["number"]).columns
        self._stats = {}
        for col in numeric_cols:
            if self.method == "minmax":
                self._stats[col] = {
                    "min": data[col].min(),
                    "max": data[col].max()
                }
            elif self.method == "standard":
                self._stats[col] = {
                    "mean": data[col].mean(),
                    "std": data[col].std()
                }
            elif self.method == "robust":
                self._stats[col] = {
                    "median": data[col].median(),
                    "iqr": data[col].quantile(0.75) - data[col].quantile(0.25)
                }
        return self

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply normalization to the data."""
        if self._stats is None:
            raise ValueError("Normalizer not fitted")
        
        data = data.copy()
        for col, stats in self._stats.items():
            if col not in data.columns:
                continue
            if self.method == "minmax":
                min_val = stats["min"]
                max_val = stats["max"]
                if max_val - min_val != 0:
                    data[col] = (data[col] - min_val) / (max_val - min_val)
            elif self.method == "standard":
                mean_val = stats["mean"]
                std_val = stats["std"]
                if std_val != 0:
                    data[col] = (data[col] - mean_val) / std_val
            elif self.method == "robust":
                median_val = stats["median"]
                iqr_val = stats["iqr"]
                if iqr_val != 0:
                    data[col] = (data[col] - median_val) / iqr_val
        return data

    def fit_transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform in one step."""
        return self.fit(data).transform(data)

    def inverse_transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Inverse transform normalized data back to original scale."""
        if self._stats is None:
            raise ValueError("Normalizer not fitted")
        
        data = data.copy()
        for col, stats in self._stats.items():
            if col not in data.columns:
                continue
            if self.method == "minmax":
                min_val = stats["min"]
                max_val = stats["max"]
                data[col] = data[col] * (max_val - min_val) + min_val
            elif self.method == "standard":
                mean_val = stats["mean"]
                std_val = stats["std"]
                data[col] = data[col] * std_val + mean_val
            elif self.method == "robust":
                median_val = stats["median"]
                iqr_val = stats["iqr"]
                data[col] = data[col] * iqr_val + median_val
        return data
