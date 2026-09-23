
"""Feature engineering for irrigation system sensor and weather data."""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class FeatureEngineer:
    """Generates features from sensor and weather data for ML models."""

    def __init__(
        self,
        rolling_windows: Optional[List[int]] = None,
        time_features: bool = True,
        weather_features: bool = True
    ):
        self.rolling_windows = rolling_windows or [3, 6, 12, 24]
        self.time_features = time_features
        self.weather_features = weather_features
        self._feature_columns: Optional[List[str]] = None

    def fit(self, data: pd.DataFrame) -> "FeatureEngineer":
        """Compute any necessary statistics from training data."""
        logger.info("Fitting feature engineer")
        transformed_data = self.transform(data)
        self._feature_columns = [
            col for col in transformed_data.columns 
            if col not in data.columns
        ]
        return self

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply feature engineering to the data."""
        logger.info("Starting feature engineering")
        data = data.copy()
        
        # Ensure timestamp column exists and is datetime type
        if "timestamp" in data.columns and not pd.api.types.is_datetime64_any_dtype(data["timestamp"]):
            data["timestamp"] = pd.to_datetime(data["timestamp"])
        
        # Step 1: Time features
        if self.time_features and "timestamp" in data.columns:
            data = self._add_time_features(data)
        
        # Step 2: Rolling window features
        data = self._add_rolling_features(data)
        
        # Step 3: Weather features (if weather data is present)
        if self.weather_features:
            data = self._add_weather_features(data)
        
        logger.info(f"Feature engineering complete. Generated {len(self._feature_columns or [])} new features")
        return data

    def fit_transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform in one step."""
        return self.fit(data).transform(data)

    def _add_time_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add time-based features."""
        data = data.copy()
        if "timestamp" not in data.columns:
            return data
        
        ts = data["timestamp"]
        data["hour_of_day"] = ts.dt.hour
        data["day_of_week"] = ts.dt.dayofweek
        data["month"] = ts.dt.month
        data["is_weekend"] = (ts.dt.dayofweek >= 5).astype(int)
        data["sin_hour"] = (2 * np.pi * data["hour_of_day"] / 24).apply(np.sin)
        data["cos_hour"] = (2 * np.pi * data["hour_of_day"] / 24).apply(np.cos)
        data["sin_day_of_week"] = (2 * np.pi * data["day_of_week"] / 7).apply(np.sin)
        data["cos_day_of_week"] = (2 * np.pi * data["day_of_week"] / 7).apply(np.cos)
        return data

    def _add_rolling_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add rolling window features (mean, std, min, max)."""
        data = data.copy()
        numeric_cols = data.select_dtypes(include=["number"]).columns
        
        for col in numeric_cols:
            for window in self.rolling_windows:
                data[f"{col}_mean_{window}"] = data[col].rolling(window=window).mean()
                data[f"{col}_std_{window}"] = data[col].rolling(window=window).std()
                data[f"{col}_min_{window}"] = data[col].rolling(window=window).min()
                data[f"{col}_max_{window}"] = data[col].rolling(window=window).max()
        
        return data

    def _add_weather_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Add weather-based features (rain probability, temperature trends)."""
        data = data.copy()
        # Rain probability features
        if "rain_probability" in data.columns:
            data["rain_high_chance"] = (data["rain_probability"] > 50).astype(int)
            data["rain_very_high_chance"] = (data["rain_probability"] > 80).astype(int)
        if "rain_volume" in data.columns:
            data["rain_expected_soon"] = (data["rain_volume"] > 1.0).astype(int)
        # Temperature features
        if "temperature" in data.columns:
            data["temp_diff"] = data["temperature"].diff()
            data["temp_change_rate"] = data["temperature"].pct_change()
        # Humidity features
        if "humidity" in data.columns:
            data["humidity_diff"] = data["humidity"].diff()
        
        return data

    def get_feature_names(self) -> Optional[List[str]]:
        """Get the list of generated feature names."""
        return self._feature_columns

    def export_dataset(
        self,
        data: pd.DataFrame,
        file_path: str,
        format: str = "parquet"
    ) -> None:
        """Export processed dataset to file."""
        if format == "parquet":
            data.to_parquet(file_path, index=False)
        elif format == "csv":
            data.to_csv(file_path, index=False)
        elif format == "json":
            data.to_json(file_path, orient="records", date_format="iso")
        logger.info(f"Exported dataset to {file_path} in {format} format")
