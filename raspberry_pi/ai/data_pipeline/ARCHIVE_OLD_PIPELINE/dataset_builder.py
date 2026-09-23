"""Dataset builder for the irrigation system that pulls data from SQLite."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import yaml

logger = logging.getLogger(__name__)


class DatasetBuilder:
    """Builds training datasets from the irrigation system SQLite database."""

    def __init__(
        self,
        database_path: Optional[str | Path] = None,
        config_path: Optional[str | Path] = None,
    ) -> None:
        """
        Initialize the dataset builder.

        Args:
            database_path: Path to the SQLite database file.
            config_path: Path to the system configuration file.
        """
        self.database_path = self._resolve_database_path(database_path, config_path)
        self._raw_data: Dict[str, pd.DataFrame] = {}
        logger.info(f"DatasetBuilder initialized with database: {self.database_path}")

    def _resolve_database_path(
        self,
        database_path: Optional[str | Path],
        config_path: Optional[str | Path],
    ) -> Path:
        """Resolve database path from config or direct input."""
        if database_path:
            return Path(database_path).resolve()

        if config_path:
            config_path = Path(config_path).resolve()
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            db_rel_path = config.get("database", {}).get("sqlite_path")
            if db_rel_path:
                return config_path.parent.parent / db_rel_path

        # Default path
        return Path(__file__).parent.parent.parent.parent / "data" / "sqlite" / "irrigation.db"

    def load_all_tables(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Load all relevant tables from the database.

        Args:
            start_time: Optional start time filter.
            end_time: Optional end time filter.

        Returns:
            Dictionary of table names to DataFrames.
        """
        logger.info("Loading all tables from database")
        tables = [
            "SensorData",
            "NPKData",
            "PumpStatus",
            "WeatherHistory",
            "Alerts",
        ]

        for table in tables:
            self._raw_data[table] = self._load_table(table, start_time, end_time)

        return self._raw_data

    def _load_table(
        self,
        table_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Load a single table from the database."""
        import sqlite3

        conn = sqlite3.connect(str(self.database_path))
        try:
            query = f"SELECT * FROM {table_name}"
            params = []

            # Apply time filter if possible
            time_column = self._get_time_column(table_name)
            if time_column and (start_time or end_time):
                conditions = []
                if start_time:
                    conditions.append(f"{time_column} >= ?")
                    params.append(start_time.isoformat())
                if end_time:
                    conditions.append(f"{time_column} <= ?")
                    params.append(end_time.isoformat())
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

            df = pd.read_sql_query(query, conn, params=params)

            # Convert time columns to datetime
            if time_column and time_column in df.columns:
                df[time_column] = pd.to_datetime(df[time_column])

            logger.info(f"Loaded {len(df)} rows from {table_name}")
            return df

        finally:
            conn.close()

    def _get_time_column(self, table_name: str) -> Optional[str]:
        """Get the appropriate time column for a table."""
        time_columns = {
            "SensorData": "recorded_at",
            "NPKData": "recorded_at",
            "PumpStatus": "recorded_at",
            "WeatherHistory": "recorded_at",
            "Alerts": "created_at",
        }
        return time_columns.get(table_name)

    def get_sensor_data(self) -> pd.DataFrame:
        """Get sensor data."""
        return self._raw_data.get("SensorData", pd.DataFrame())

    def get_npk_data(self) -> pd.DataFrame:
        """Get NPK data."""
        return self._raw_data.get("NPKData", pd.DataFrame())

    def get_pump_data(self) -> pd.DataFrame:
        """Get pump status data."""
        return self._raw_data.get("PumpStatus", pd.DataFrame())

    def get_weather_data(self) -> pd.DataFrame:
        """Get weather history data."""
        return self._raw_data.get("WeatherHistory", pd.DataFrame())

    def get_alerts_data(self) -> pd.DataFrame:
        """Get alerts data."""
        return self._raw_data.get("Alerts", pd.DataFrame())

    def get_raw_data(self) -> Dict[str, pd.DataFrame]:
        """Get all raw loaded data."""
        return self._raw_data

    def export_raw_data(self, output_dir: str | Path, format: str = "parquet") -> None:
        """
        Export raw data to files.

        Args:
            output_dir: Directory to save files.
            format: Output format (parquet, csv).
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        for name, df in self._raw_data.items():
            file_path = output_dir / f"{name}.{format}"
            if format == "parquet":
                df.to_parquet(file_path, index=False)
            elif format == "csv":
                df.to_csv(file_path, index=False)
            logger.info(f"Exported {name} to {file_path}")
