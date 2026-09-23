"""Train/test/validation splitter for time series data."""

from __future__ import annotations

import logging
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class TrainTestSplit:
    """Splits time series data into train/validation/test sets."""

    def __init__(
        self,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        shuffle: bool = False,
    ) -> None:
        """
        Initialize the splitter.

        Args:
            train_ratio: Ratio of training data.
            val_ratio: Ratio of validation data.
            test_ratio: Ratio of test data.
            shuffle: Whether to shuffle (not recommended for time series).
        """
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.shuffle = shuffle
        self._split_stats: Dict[str, Any] = {}

        # Verify ratios sum to 1
        total = train_ratio + val_ratio + test_ratio
        if not np.isclose(total, 1.0):
            raise ValueError(f"Ratios must sum to 1, got {total}")

    def split(
        self,
        data: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split the data into train/val/test.

        Args:
            data: Input DataFrame.

        Returns:
            Tuple of (train, val, test) DataFrames.
        """
        logger.info("Starting train/val/test split")
        df = data.copy()

        n = len(df)
        train_end = int(n * self.train_ratio)
        val_end = train_end + int(n * self.val_ratio)

        if self.shuffle:
            df = df.sample(frac=1, random_state=42)

        train = df.iloc[:train_end]
        val = df.iloc[train_end:val_end]
        test = df.iloc[val_end:]

        self._split_stats = {
            "total_samples": n,
            "train_samples": len(train),
            "val_samples": len(val),
            "test_samples": len(test),
        }

        logger.info(
            f"Split complete: train={len(train)}, val={len(val)}, test={len(test)}"
        )
        return train, val, test

    def split_arrays(
        self,
        X: np.ndarray,
        y: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Split numpy arrays into train/val/test.

        Args:
            X: Input features.
            y: Targets.

        Returns:
            Tuple of (X_train, y_train, X_val, y_val, X_test, y_test).
        """
        n = len(X)
        train_end = int(n * self.train_ratio)
        val_end = train_end + int(n * self.val_ratio)

        if self.shuffle:
            indices = np.random.permutation(n)
            X = X[indices]
            y = y[indices]

        X_train = X[:train_end]
        y_train = y[:train_end]
        X_val = X[train_end:val_end]
        y_val = y[train_end:val_end]
        X_test = X[val_end:]
        y_test = y[val_end:]

        self._split_stats = {
            "total_samples": n,
            "train_samples": len(X_train),
            "val_samples": len(X_val),
            "test_samples": len(X_test),
        }

        return X_train, y_train, X_val, y_val, X_test, y_test

    def get_split_statistics(self) -> Dict[str, Any]:
        """Get statistics about the split."""
        return self._split_stats
