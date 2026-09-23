"""Dataset merger for combining all irrigation data sources."""

from __future__ import annotations

import logging
from typing import Any, Dict

import pandas as pd

logger = logging.getLogger(__name__)


class DatasetMerger:
    """Merges sensor, NPK, pump, and weather data into a single dataset."""

    def __init__(
        self,
        resample_freq: str = "1H",
        aggregation: str = "mean",
    ) -> None:
        """
        Initialize the dataset merger.

        Args:
            resample_freq: Frequency to resample data to (e.g., '1H', '15T').
            aggregation: Aggregation method for resampling.
        """
        self.resample_freq = resample_freq
        self.aggregation = aggregation
        self._merge_stats: Dict[str, Any] = {}

    def merge(
        self,
        sensor_data: pd.DataFrame,
        npk_data: pd.DataFrame,
        pump_data: pd.DataFrame,
        weather_data: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Merge all data sources into a single dataset.

        Args:
            sensor_data: Sensor node data.
            npk_data: NPK node data.
            pump_data: Pump status data.
            weather_data: Weather history data.

        Returns:
            Merged DataFrame.
        """
        logger.info("Starting dataset merge")
        self._merge_stats = {
            "sensor_rows": len(sensor_data),
            "npk_rows": len(npk_data),
            "pump_rows": len(pump_data),
            "weather_rows": len(weather_data),
        }

        # Process each data source
        dfs = []

        if not sensor_data.empty:
            sensor_processed = self._process_sensor_data(sensor_data)
            dfs.append(sensor_processed)

        if not npk_data.empty:
            npk_processed = self._process_npk_data(npk_data)
            dfs.append(npk_processed)

        if not pump_data.empty:
            pump_processed = self._process_pump_data(pump_data)
            dfs.append(pump_processed)

        if not weather_data.empty:
            weather_processed = self._process_weather_data(weather_data)
            dfs.append(weather_processed)

        if not dfs:
            logger.warning("No data to merge")
            return pd.DataFrame()

        # Merge all on timestamp
        merged = dfs[0]
        for df in dfs[1:]:
            merged = merged.merge(df, on="timestamp", how="outer")

        # Sort and fill gaps
        merged = merged.sort_values("timestamp").reset_index(drop=True)

        self._merge_stats["merged_rows"] = len(merged)
        self._merge_stats["merged_columns"] = len(merged.columns)
        logger.info(f"Merge complete: {len(merged)} rows, {len(merged.columns)} columns")

        return merged

    def _process_sensor_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Process and resample sensor data."""
        df = data.copy()

        if "recorded_at" in df.columns:
            df["timestamp"] = pd.to_datetime(df["recorded_at"])
            df = df.set_index("timestamp")

        # Select relevant columns
        keep_cols = [
            "soil_moisture_percent",
            "temperature_c",
            "humidity_percent",
            "battery_voltage",
            "battery_percent",
        ]
        df = df[[col for col in keep_cols if col in df.columns]]

        # Resample
        if self.resample_freq:
            df = df.resample(self.resample_freq).agg(self.aggregation)

        df = df.reset_index()
        return df

    def _process_npk_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Process and resample NPK data."""
        df = data.copy()

        if "recorded_at" in df.columns:
            df["timestamp"] = pd.to_datetime(df["recorded_at"])
            df = df.set_index("timestamp")

        # Select relevant columns
        keep_cols = [
            "nitrogen_mg_kg",
            "phosphorus_mg_kg",
            "potassium_mg_kg",
            "ph",
            "electrical_conductivity",
            "soil_temperature_c",
            "moisture_percent",
            "battery_voltage",
            "battery_percent",
        ]
        df = df[[col for col in keep_cols if col in df.columns]]

        # Resample
        if self.resample_freq:
            df = df.resample(self.resample_freq).agg(self.aggregation)

        df = df.reset_index()
        return df

    def _process_pump_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Process and resample pump data."""
        df = data.copy()

        if "recorded_at" in df.columns:
            df["timestamp"] = pd.to_datetime(df["recorded_at"])
            df = df.set_index("timestamp")

        # Convert categorical columns
        if "relay_state" in df.columns:
            df["pump_on"] = (df["relay_state"] == "ON").astype(int)

        if "pump_feedback_state" in df.columns:
            df["pump_running"] = (df["pump_feedback_state"] == "RUNNING").astype(int)

        # Select relevant columns
        keep_cols = [
            "pump_on",
            "pump_running",
            "runtime_seconds",
        ]
        df = df[[col for col in keep_cols if col in df.columns]]

        # Resample
        if self.resample_freq:
            # For runtime, use sum or max
            agg_dict = {col: self.aggregation for col in df.columns}
            if "runtime_seconds" in agg_dict:
                agg_dict["runtime_seconds"] = "sum"
            df = df.resample(self.resample_freq).agg(agg_dict)

        df = df.reset_index()
        return df

    def _process_weather_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Process and resample weather data."""
        df = data.copy()

        if "recorded_at" in df.columns:
            df["timestamp"] = pd.to_datetime(df["recorded_at"])
            df = df.set_index("timestamp")

        # Select relevant columns
        keep_cols = [
            "temperature_c",
            "humidity_percent",
            "rainfall_mm",
            "wind_speed_mps",
            "pressure_hpa",
            "forecast_horizon_hours",
        ]
        df = df[[col for col in keep_cols if col in df.columns]]

        # Resample
        if self.resample_freq:
            # For rainfall, use sum
            agg_dict = {col: self.aggregation for col in df.columns}
            if "rainfall_mm" in agg_dict:
                agg_dict["rainfall_mm"] = "sum"
            df = df.resample(self.resample_freq).agg(agg_dict)

        df = df.reset_index()

        # Rename to avoid conflict with sensor data
        rename_map = {
            "temperature_c": "weather_temperature_c",
            "humidity_percent": "weather_humidity_percent",
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        return df

    def get_merge_statistics(self) -> Dict[str, Any]:
        """Get statistics about the merge process."""
        return self._merge_stats
