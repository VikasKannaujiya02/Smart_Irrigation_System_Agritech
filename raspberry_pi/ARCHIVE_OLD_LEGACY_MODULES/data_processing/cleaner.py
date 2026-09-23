
"""Data cleaner for irrigation system sensor and NPK data."""

from __future__ import annotations

import logging

import pandas as pd

from .missing_value_handler import MissingValueHandler
from .outlier_detection import OutlierDetector

logger = logging.getLogger(__name__)


class DataCleaner:
    """Cleans and preprocesses raw sensor data."""

    def __init__(
        self,
        missing_handler: MissingValueHandler | None = None,
        outlier_detector: OutlierDetector | None = None,
        remove_duplicates: bool = True,
        sort_by_time: bool = True
    ):
        self.missing_handler = missing_handler or MissingValueHandler()
        self.outlier_detector = outlier_detector or OutlierDetector()
        self.remove_duplicates = remove_duplicates
        self.sort_by_time = sort_by_time
        self._is_fitted = False

    def fit(self, data: pd.DataFrame) -> "DataCleaner":
        """Fit cleaners to training data."""
        logger.info("Fitting data cleaner")
        if self.missing_handler:
            self.missing_handler.fit(data)
        if self.outlier_detector:
            self.outlier_detector.fit(data)
        self._is_fitted = True
        return self

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply full cleaning pipeline to the data."""
        if not self._is_fitted:
            raise ValueError("DataCleaner not fitted")
        
        logger.info("Starting data cleaning")
        data = data.copy()
        
        # Step 1: Remove duplicates
        if self.remove_duplicates:
            initial_len = len(data)
            if "timestamp" in data.columns:
                data = data.drop_duplicates(subset=["timestamp"], keep="last")
            else:
                data = data.drop_duplicates()
            logger.info(f"Removed {initial_len - len(data)} duplicate rows")
        
        # Step 2: Sort by time
        if self.sort_by_time and "timestamp" in data.columns:
            data = data.sort_values("timestamp").reset_index(drop=True)
        
        # Step 3: Handle missing values
        if self.missing_handler:
            data = self.missing_handler.transform(data)
        
        # Step 4: Handle outliers
        if self.outlier_detector:
            data = self.outlier_detector.transform(data)
        
        logger.info(f"Data cleaning complete. Final shape: {data.shape}")
        return data

    def fit_transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform in one step."""
        return self.fit(data).transform(data)

    def reset(self) -> "DataCleaner":
        """Reset the cleaner to unfitted state."""
        self._is_fitted = False
        return self
