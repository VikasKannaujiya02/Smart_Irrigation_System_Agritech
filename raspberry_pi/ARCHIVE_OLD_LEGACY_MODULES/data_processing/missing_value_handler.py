
"""Missing value handler for sensor and NPK data."""

from __future__ import annotations

import logging
from typing import Literal, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class MissingValueHandler:
    """Handles missing values in irrigation system data."""

    def __init__(
        self,
        strategy: Literal["mean", "median", "mode", "ffill", "bfill", "drop"] = "mean"
    ):
        self.strategy = strategy
        self._stat_values: Optional[pd.Series] = None

    def fit(self, data: pd.DataFrame) -> "MissingValueHandler":
        """Compute statistics for missing value imputation."""
        if self.strategy in ["mean", "median", "mode"]:
            numeric_cols = data.select_dtypes(include=["number"]).columns
            if self.strategy == "mean":
                self._stat_values = data[numeric_cols].mean()
            elif self.strategy == "median":
                self._stat_values = data[numeric_cols].median()
            elif self.strategy == "mode":
                self._stat_values = data[numeric_cols].mode().iloc[0]
        return self

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply missing value handling to the data."""
        data = data.copy()
        if self.strategy == "drop":
            initial_count = len(data)
            data = data.dropna()
            logger.info(f"Dropped {initial_count - len(data)} rows with missing values")
        elif self.strategy == "ffill":
            data = data.ffill()
        elif self.strategy == "bfill":
            data = data.bfill()
        elif self._stat_values is not None:
            data = data.fillna(self._stat_values)
        return data

    def fit_transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform in one step."""
        return self.fit(data).transform(data)

    def get_missing_summary(self, data: pd.DataFrame) -> pd.DataFrame:
        """Get a summary of missing values in the data."""
        missing = data.isnull().sum()
        missing_percent = (data.isnull().sum() / len(data)) * 100
        summary = pd.DataFrame({
            "missing_count": missing,
            "missing_percent": missing_percent
        })
        summary = summary[summary["missing_count"] > 0].sort_values(
            "missing_percent", ascending=False
        )
        return summary
