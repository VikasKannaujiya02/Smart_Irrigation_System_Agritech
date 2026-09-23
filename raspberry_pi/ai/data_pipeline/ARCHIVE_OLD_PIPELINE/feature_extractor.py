"""Feature extractor for irrigation system data."""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Extracts and engineers features from the merged irrigation dataset."""

    def __init__(
        self,
        rolling_windows: Optional[List[int]] = None,
        add_time_features: bool = True,
        add_rolling_features: bool = True,
        add_weather_features: bool = True,
    ) -> None:
        """
        Initialize the feature extractor.

        Args:
            rolling_windows: List of window sizes for rolling features (hours).
            add_time_features: Whether to add time-based features.
            add_rolling_features: Whether to add rolling window features.
            add_weather_features: Whether to add weather-derived features.
        """
        self.rolling_windows = rolling_windows or [3, 6, 12, 24, 48]
        self.add_time_features = add_time_features
        self.add_rolling_features = add_rolling_features
        self.add_weather_features = add_weather_features
        self._feature_names: Optional[List[str]] = None

    def extract(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Extract features from the dataset.

        Args:
            data: Input DataFrame with timestamp column.

        Returns:
            DataFrame with extracted features.
        """
        logger.info("Starting feature extraction")
        df = data.copy()

        # Ensure timestamp is present and sorted
        if "timestamp" not in df.columns:
            raise ValueError("DataFrame must have 'timestamp' column")

        df = df.sort_values("timestamp").reset_index(drop=True)

        if self.add_time_features:
            df = self._add_time_features(df)

        if self.add_rolling_features:
            df = self._add_rolling_features(df)

        if self.add_weather_features:
            df = self._add_weather_features(df)

        # Store feature names (excluding original columns)
        original_cols = set(data.columns)
        self._feature_names = [col for col in df.columns if col not in original_cols]

        logger.info(f"Extracted {len(self._feature_names)} features")
        return df

    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add time-based features."""
        ts = df["timestamp"]

        # Basic time components
        df["hour"] = ts.dt.hour
        df["day_of_week"] = ts.dt.dayofweek
        df["day_of_month"] = ts.dt.day
        df["month"] = ts.dt.month
        df["year"] = ts.dt.year
        df["is_weekend"] = (ts.dt.dayofweek >= 5).astype(int)

        # Cyclical encoding
        df["sin_hour"] = np.sin(2 * np.pi * df["hour"] / 24)
        df["cos_hour"] = np.cos(2 * np.pi * df["hour"] / 24)
        df["sin_day_of_week"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
        df["cos_day_of_week"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
        df["sin_month"] = np.sin(2 * np.pi * df["month"] / 12)
        df["cos_month"] = np.cos(2 * np.pi * df["month"] / 12)

        # Season (simplified)
        df["season"] = pd.cut(
            df["month"],
            bins=[0, 3, 6, 9, 12],
            labels=[0, 1, 2, 3],  # winter, spring, summer, fall
            include_lowest=True,
        ).astype(int)

        return df

    def _add_rolling_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add rolling window features."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        # Exclude time features we just added and id columns
        exclude_cols = [
            "hour", "day_of_week", "day_of_month", "month", "year",
            "is_weekend", "sin_hour", "cos_hour", "sin_day_of_week",
            "cos_day_of_week", "sin_month", "cos_month", "season",
        ]
        numeric_cols = [col for col in numeric_cols if col not in exclude_cols]

        for col in numeric_cols:
            for window in self.rolling_windows:
                # Rolling mean
                df[f"{col}_mean_{window}h"] = df[col].rolling(window=window, min_periods=1).mean()
                # Rolling std
                df[f"{col}_std_{window}h"] = df[col].rolling(window=window, min_periods=1).std()
                # Rolling min/max
                df[f"{col}_min_{window}h"] = df[col].rolling(window=window, min_periods=1).min()
                df[f"{col}_max_{window}h"] = df[col].rolling(window=window, min_periods=1).max()
                # Rate of change
                df[f"{col}_diff_{window}h"] = df[col].diff(periods=window)

        return df

    def _add_weather_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add weather-derived features."""
        # Cumulative rainfall
        if "rainfall_mm" in df.columns:
            df["rainfall_24h"] = df["rainfall_mm"].rolling(window=24, min_periods=1).sum()
            df["rainfall_72h"] = df["rainfall_mm"].rolling(window=72, min_periods=1).sum()

        # Temperature delta
        if "temperature_c" in df.columns:
            df["temp_diff_1h"] = df["temperature_c"].diff(1)
            df["temp_diff_24h"] = df["temperature_c"].diff(24)

        # Weather-based irrigation indicators
        if "rainfall_mm" in df.columns and "soil_moisture_percent" in df.columns:
            df["rain_indicates_delay"] = (
                (df["rainfall_24h"] > 2.0) |
                (df["soil_moisture_percent"] > 70)
            ).astype(int)

        return df

    def get_feature_names(self) -> Optional[List[str]]:
        """Get the list of extracted feature names."""
        return self._feature_names
