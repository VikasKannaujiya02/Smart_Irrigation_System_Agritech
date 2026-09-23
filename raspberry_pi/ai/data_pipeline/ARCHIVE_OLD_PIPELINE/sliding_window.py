"""Sliding window transformer for time series data."""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class SlidingWindow:
    """Creates sliding window sequences from time series data."""

    def __init__(
        self,
        window_size: int = 24,
        horizon: int = 1,
        target_columns: Optional[List[str]] = None,
        drop_na: bool = True,
    ) -> None:
        """
        Initialize the sliding window transformer.

        Args:
            window_size: Number of time steps in the input window.
            horizon: Number of time steps to predict ahead.
            target_columns: Columns to use as targets (if None, all columns).
            drop_na: Whether to drop windows with NaN values.
        """
        self.window_size = window_size
        self.horizon = horizon
        self.target_columns = target_columns
        self.drop_na = drop_na
        self._feature_columns: Optional[List[str]] = None

    def transform(
        self,
        data: pd.DataFrame,
        feature_columns: Optional[List[str]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Transform data into sliding window sequences.

        Args:
            data: Input DataFrame.
            feature_columns: Columns to use as features (if None, all numeric columns).

        Returns:
            Tuple of (X, y) where X is input sequences and y is target sequences.
        """
        logger.info(f"Creating sliding windows: window={self.window_size}, horizon={self.horizon}")
        df = data.copy()

        # Determine feature columns
        if feature_columns:
            self._feature_columns = feature_columns
        else:
            self._feature_columns = df.select_dtypes(include=[np.number]).columns.tolist()

        df_features = df[self._feature_columns].values

        # Create sequences
        X, y = [], []
        n_samples = len(df_features) - self.window_size - self.horizon + 1

        for i in range(n_samples):
            end_idx = i + self.window_size
            target_end_idx = end_idx + self.horizon

            X.append(df_features[i:end_idx])

            if self.target_columns:
                target_indices = [self._feature_columns.index(col) for col in self.target_columns]
                y.append(df_features[end_idx:target_end_idx, target_indices])
            else:
                y.append(df_features[end_idx:target_end_idx])

        X = np.array(X)
        y = np.array(y)

        # Drop NaN
        if self.drop_na:
            mask = ~np.isnan(X).any(axis=(1, 2)) & ~np.isnan(y).any(axis=(1, 2))
            X = X[mask]
            y = y[mask]
            logger.info(f"Dropped {np.sum(~mask)} windows with NaN values")

        logger.info(f"Created {len(X)} sequences")
        return X, y

    def transform_single(
        self,
        data: pd.DataFrame,
    ) -> np.ndarray:
        """
        Transform a single window for prediction.

        Args:
            data: Input DataFrame with at least window_size rows.

        Returns:
            Single input sequence (1, window_size, n_features).
        """
        if len(data) < self.window_size:
            raise ValueError(f"Need at least {self.window_size} rows, got {len(data)}")

        df = data.tail(self.window_size)
        if self._feature_columns:
            df = df[self._feature_columns]

        X = df.values.reshape(1, self.window_size, -1)
        return X

    def get_feature_columns(self) -> Optional[List[str]]:
        """Get the feature column names."""
        return self._feature_columns
