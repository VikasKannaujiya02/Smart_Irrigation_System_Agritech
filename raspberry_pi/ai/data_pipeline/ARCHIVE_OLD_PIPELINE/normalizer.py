"""Normalizer for scaling features."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Literal, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class Normalizer:
    """Normalizes and scales features."""

    def __init__(
        self,
        method: Literal["minmax", "standard", "robust"] = "standard",
    ) -> None:
        """
        Initialize the normalizer.

        Args:
            method: Normalization method.
        """
        self.method = method
        self._scalers: Dict[str, Any] = {}
        self._columns: Optional[List[str]] = None

    def fit(self, data: pd.DataFrame, columns: Optional[List[str]] = None) -> "Normalizer":
        """
        Fit the normalizer to the data.

        Args:
            data: Input DataFrame.
            columns: Columns to normalize (all numeric if None).

        Returns:
            Self.
        """
        df = data.copy()

        if columns:
            self._columns = columns
        else:
            self._columns = df.select_dtypes(include=[np.number]).columns.tolist()

        for col in self._columns:
            if col not in df.columns:
                continue

            series = df[col].dropna()
            if len(series) == 0:
                continue

            if self.method == "minmax":
                self._scalers[col] = {
                    "min": series.min(),
                    "max": series.max(),
                }
            elif self.method == "standard":
                self._scalers[col] = {
                    "mean": series.mean(),
                    "std": series.std(),
                }
            elif self.method == "robust":
                self._scalers[col] = {
                    "median": series.median(),
                    "iqr": series.quantile(0.75) - series.quantile(0.25),
                }

        logger.info(f"Fitted normalizer on {len(self._columns)} columns")
        return self

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Transform the data.

        Args:
            data: Input DataFrame.

        Returns:
            Normalized DataFrame.
        """
        df = data.copy()

        if not self._columns:
            raise ValueError("Normalizer not fitted. Call fit() first.")

        for col in self._columns:
            if col not in df.columns:
                continue

            scaler = self._scalers.get(col)
            if not scaler:
                continue

            if self.method == "minmax":
                min_val = scaler["min"]
                max_val = scaler["max"]
                if max_val != min_val:
                    df[col] = (df[col] - min_val) / (max_val - min_val)
            elif self.method == "standard":
                mean = scaler["mean"]
                std = scaler["std"]
                if std != 0:
                    df[col] = (df[col] - mean) / std
            elif self.method == "robust":
                median = scaler["median"]
                iqr = scaler["iqr"]
                if iqr != 0:
                    df[col] = (df[col] - median) / iqr

        return df

    def fit_transform(self, data: pd.DataFrame, columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Fit and transform in one step.

        Args:
            data: Input DataFrame.
            columns: Columns to normalize.

        Returns:
            Normalized DataFrame.
        """
        return self.fit(data, columns).transform(data)

    def inverse_transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Inverse transform the data.

        Args:
            data: Normalized DataFrame.

        Returns:
            Original scale DataFrame.
        """
        df = data.copy()

        if not self._columns:
            raise ValueError("Normalizer not fitted. Call fit() first.")

        for col in self._columns:
            if col not in df.columns:
                continue

            scaler = self._scalers.get(col)
            if not scaler:
                continue

            if self.method == "minmax":
                min_val = scaler["min"]
                max_val = scaler["max"]
                df[col] = df[col] * (max_val - min_val) + min_val
            elif self.method == "standard":
                mean = scaler["mean"]
                std = scaler["std"]
                df[col] = df[col] * std + mean
            elif self.method == "robust":
                median = scaler["median"]
                iqr = scaler["iqr"]
                df[col] = df[col] * iqr + median

        return df

    def get_scalers(self) -> Dict[str, Any]:
        """Get the fitted scaler parameters."""
        return self._scalers
