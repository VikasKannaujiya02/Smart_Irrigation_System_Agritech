"""Feature selector for irrigation system data."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Literal, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FeatureSelector:
    """Selects important features for model training."""

    def __init__(
        self,
        method: Literal["correlation", "variance", "none"] = "correlation",
        correlation_threshold: float = 0.95,
        variance_threshold: float = 0.0,
        drop_missing_threshold: float = 0.5,
    ) -> None:
        """
        Initialize the feature selector.

        Args:
            method: Feature selection method.
            correlation_threshold: Threshold for removing highly correlated features.
            variance_threshold: Threshold for removing low-variance features.
            drop_missing_threshold: Drop columns with more than this fraction missing.
        """
        self.method = method
        self.correlation_threshold = correlation_threshold
        self.variance_threshold = variance_threshold
        self.drop_missing_threshold = drop_missing_threshold
        self._selected_features: Optional[List[str]] = None
        self._selection_stats: Dict[str, Any] = {}

    def select(
        self,
        data: pd.DataFrame,
        target_column: Optional[str] = None,
        exclude_columns: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Select features from the dataset.

        Args:
            data: Input DataFrame.
            target_column: Optional target column (not dropped).
            exclude_columns: Columns to always keep.

        Returns:
            DataFrame with selected features.
        """
        logger.info("Starting feature selection")
        df = data.copy()

        exclude = exclude_columns or []
        if target_column and target_column in df.columns:
            exclude.append(target_column)

        self._selection_stats = {
            "initial_features": len(df.columns),
        }

        # Step 1: Drop columns with too many missing values
        df = self._drop_missing_columns(df, exclude)

        # Step 2: Drop low variance features
        if self.method in ["variance", "correlation"]:
            df = self._drop_low_variance(df, exclude)

        # Step 3: Drop highly correlated features
        if self.method == "correlation":
            df = self._drop_correlated(df, exclude)

        self._selected_features = list(df.columns)
        self._selection_stats["final_features"] = len(df.columns)
        self._selection_stats["dropped_features"] = int(
            self._selection_stats["initial_features"] - self._selection_stats["final_features"]
        )

        logger.info(f"Selected {len(df.columns)} features")
        return df

    def _drop_missing_columns(
        self,
        df: pd.DataFrame,
        exclude: List[str],
    ) -> pd.DataFrame:
        """Drop columns with too many missing values."""
        cols_to_check = [col for col in df.columns if col not in exclude]
        missing_frac = df[cols_to_check].isnull().mean()
        cols_to_drop = missing_frac[missing_frac > self.drop_missing_threshold].index.tolist()

        if cols_to_drop:
            logger.debug(f"Dropping {len(cols_to_drop)} columns with >{self.drop_missing_threshold} missing values")
            df = df.drop(columns=cols_to_drop)

        self._selection_stats["dropped_missing"] = len(cols_to_drop)
        return df

    def _drop_low_variance(
        self,
        df: pd.DataFrame,
        exclude: List[str],
    ) -> pd.DataFrame:
        """Drop low variance features."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cols_to_check = [col for col in numeric_cols if col not in exclude]

        variances = df[cols_to_check].var()
        cols_to_drop = variances[variances <= self.variance_threshold].index.tolist()

        if cols_to_drop:
            logger.debug(f"Dropping {len(cols_to_drop)} low variance features")
            df = df.drop(columns=cols_to_drop)

        self._selection_stats["dropped_variance"] = len(cols_to_drop)
        return df

    def _drop_correlated(
        self,
        df: pd.DataFrame,
        exclude: List[str],
    ) -> pd.DataFrame:
        """Drop highly correlated features."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cols_to_check = [col for col in numeric_cols if col not in exclude]

        if len(cols_to_check) < 2:
            self._selection_stats["dropped_correlated"] = 0
            return df

        corr_matrix = df[cols_to_check].corr().abs()
        upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
        cols_to_drop = [col for col in upper.columns if any(upper[col] > self.correlation_threshold)]

        if cols_to_drop:
            logger.debug(f"Dropping {len(cols_to_drop)} highly correlated features")
            df = df.drop(columns=cols_to_drop)

        self._selection_stats["dropped_correlated"] = len(cols_to_drop)
        return df

    def get_selected_features(self) -> Optional[List[str]]:
        """Get the list of selected feature names."""
        return self._selected_features

    def get_selection_statistics(self) -> Dict[str, Any]:
        """Get statistics about the feature selection process."""
        return self._selection_stats
