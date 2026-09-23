"""Dataset cleaner for irrigation system data."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Literal, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DatasetCleaner:
    """Cleans and preprocesses the irrigation dataset."""

    def __init__(
        self,
        remove_duplicates: bool = True,
        outlier_method: Literal["iqr", "zscore", "none"] = "iqr",
        missing_method: Literal["interpolate", "ffill", "bfill", "drop", "mean", "median"] = "interpolate",
        iqr_multiplier: float = 1.5,
        zscore_threshold: float = 3.0,
    ) -> None:
        """
        Initialize the dataset cleaner.

        Args:
            remove_duplicates: Whether to remove duplicate rows.
            outlier_method: Method for outlier detection.
            missing_method: Method for handling missing values.
            iqr_multiplier: Multiplier for IQR method.
            zscore_threshold: Threshold for z-score method.
        """
        self.remove_duplicates = remove_duplicates
        self.outlier_method = outlier_method
        self.missing_method = missing_method
        self.iqr_multiplier = iqr_multiplier
        self.zscore_threshold = zscore_threshold
        self._cleaning_stats: Dict[str, Any] = {}

    def clean(
        self,
        data: pd.DataFrame,
        columns_to_clean: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Clean the dataset.

        Args:
            data: DataFrame to clean.
            columns_to_clean: Specific columns to clean (all if None).

        Returns:
            Cleaned DataFrame.
        """
        logger.info("Starting dataset cleaning")
        data = data.copy()

        self._cleaning_stats = {
            "initial_rows": len(data),
            "initial_columns": len(data.columns),
        }

        # Step 1: Remove duplicates
        if self.remove_duplicates:
            initial_duplicates = data.duplicated().sum()
            data = data.drop_duplicates()
            self._cleaning_stats["duplicates_removed"] = int(initial_duplicates)
            logger.info(f"Removed {initial_duplicates} duplicate rows")

        # Step 2: Handle outliers
        if self.outlier_method != "none":
            data, outlier_stats = self._handle_outliers(data, columns_to_clean)
            self._cleaning_stats["outliers"] = outlier_stats

        # Step 3: Handle missing values
        data, missing_stats = self._handle_missing_values(data, columns_to_clean)
        self._cleaning_stats["missing_values"] = missing_stats

        # Step 4: Sort by timestamp if present
        if "timestamp" in data.columns:
            data = data.sort_values("timestamp").reset_index(drop=True)

        self._cleaning_stats["final_rows"] = len(data)
        self._cleaning_stats["final_columns"] = len(data.columns)
        self._cleaning_stats["rows_removed"] = int(
            self._cleaning_stats["initial_rows"] - self._cleaning_stats["final_rows"]
        )

        logger.info(f"Cleaning complete. Removed {self._cleaning_stats['rows_removed']} rows")
        return data

    def _handle_outliers(
        self,
        data: pd.DataFrame,
        columns_to_clean: Optional[List[str]],
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Detect and handle outliers."""
        stats: Dict[str, Any] = {}
        cols = columns_to_clean or data.select_dtypes(include=[np.number]).columns

        for col in cols:
            if col not in data.columns or not pd.api.types.is_numeric_dtype(data[col]):
                continue

            series = data[col].copy()
            initial_count = len(series.dropna())

            if self.outlier_method == "iqr":
                mask = self._iqr_mask(series)
            elif self.outlier_method == "zscore":
                mask = self._zscore_mask(series)
            else:
                mask = pd.Series([True] * len(series), index=series.index)

            outlier_count = int((~mask).sum())
            if outlier_count > 0:
                data.loc[~mask, col] = np.nan
                logger.debug(f"Marked {outlier_count} outliers in {col} as NaN")

            stats[col] = {
                "initial_count": initial_count,
                "outlier_count": outlier_count,
                "method": self.outlier_method,
            }

        return data, stats

    def _iqr_mask(self, series: pd.Series) -> pd.Series:
        """Create mask using IQR method."""
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - self.iqr_multiplier * iqr
        upper_bound = q3 + self.iqr_multiplier * iqr
        return series.between(lower_bound, upper_bound, inclusive="both") | series.isnull()

    def _zscore_mask(self, series: pd.Series) -> pd.Series:
        """Create mask using z-score method."""
        z_scores = np.abs((series - series.mean()) / series.std())
        return (z_scores <= self.zscore_threshold) | series.isnull()

    def _handle_missing_values(
        self,
        data: pd.DataFrame,
        columns_to_clean: Optional[List[str]],
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Handle missing values."""
        stats: Dict[str, Any] = {}
        cols = columns_to_clean or data.columns

        for col in cols:
            if col not in data.columns:
                continue

            initial_missing = int(data[col].isnull().sum())
            if initial_missing == 0:
                stats[col] = {"initial_missing": 0, "final_missing": 0}
                continue

            if self.missing_method == "drop":
                data = data.dropna(subset=[col])
            elif self.missing_method == "interpolate":
                if "timestamp" in data.columns:
                    data = data.sort_values("timestamp")
                    data[col] = data[col].interpolate(method="time")
                else:
                    data[col] = data[col].interpolate()
            elif self.missing_method == "ffill":
                data[col] = data[col].ffill()
            elif self.missing_method == "bfill":
                data[col] = data[col].bfill()
            elif self.missing_method == "mean":
                data[col] = data[col].fillna(data[col].mean())
            elif self.missing_method == "median":
                data[col] = data[col].fillna(data[col].median())

            final_missing = int(data[col].isnull().sum())
            stats[col] = {
                "initial_missing": initial_missing,
                "final_missing": final_missing,
                "method": self.missing_method,
            }

        return data, stats

    def get_cleaning_statistics(self) -> Dict[str, Any]:
        """Get statistics about the cleaning process."""
        return self._cleaning_stats
