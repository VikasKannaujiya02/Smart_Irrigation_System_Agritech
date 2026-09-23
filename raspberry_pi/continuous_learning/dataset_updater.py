"""Automatic dataset updater."""

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DatasetUpdateResult:
    """Result of a dataset update."""
    success: bool
    timestamp: datetime
    new_samples: int = 0
    total_samples: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


class DatasetUpdater:
    """Automatically updates datasets with new data."""

    def __init__(
        self,
        dataset_dir: str | Path,
        update_interval_hours: int = 24,
        max_history_days: int = 365
    ):
        self.dataset_dir = Path(dataset_dir)
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self.update_interval = timedelta(hours=update_interval_hours)
        self.max_history = timedelta(days=max_history_days)
        self.last_update: Optional[datetime] = None
        self._load_last_update()

    def _load_last_update(self) -> None:
        """Load last update time from metadata."""
        meta_path = self.dataset_dir / "update_metadata.json"
        if meta_path.exists():
            import json
            with open(meta_path, "r") as f:
                data = json.load(f)
                if "last_update" in data:
                    self.last_update = datetime.fromisoformat(data["last_update"])

    def _save_last_update(self) -> None:
        """Save last update time to metadata."""
        meta_path = self.dataset_dir / "update_metadata.json"
        import json
        with open(meta_path, "w") as f:
            json.dump({"last_update": self.last_update.isoformat()}, f, indent=2)

    def update_from_dataframe(
        self,
        dataframe: pd.DataFrame,
        time_column: str = "recorded_at",
        dataset_name: str = "sensor_data"
    ) -> DatasetUpdateResult:
        """Update dataset with new data from a DataFrame."""
        result = DatasetUpdateResult(
            success=False,
            timestamp=datetime.now()
        )

        try:
            # Ensure time column is datetime
            df = dataframe.copy()
            if time_column in df.columns:
                df[time_column] = pd.to_datetime(df[time_column])

            # Load existing dataset
            existing_path = self.dataset_dir / f"{dataset_name}.parquet"
            existing_df = pd.DataFrame()
            if existing_path.exists():
                existing_df = pd.read_parquet(existing_path)
                if time_column in existing_df.columns:
                    existing_df[time_column] = pd.to_datetime(existing_df[time_column])

            # Combine datasets and remove duplicates
            if not existing_df.empty:
                combined = pd.concat([existing_df, df], ignore_index=True)
                combined = combined.drop_duplicates(subset=[time_column] if time_column in combined.columns else None, keep="last")
            else:
                combined = df

            # Remove old data
            if time_column in combined.columns:
                cutoff = datetime.now() - self.max_history
                combined = combined[combined[time_column] >= cutoff]

            # Save updated dataset
            combined.to_parquet(existing_path, index=False)

            result.success = True
            result.new_samples = len(df)
            result.total_samples = len(combined)
            result.details = {
                "dataset_name": dataset_name,
                "existing_samples": len(existing_df)
            }

            self.last_update = datetime.now()
            self._save_last_update()

            logger.info(f"Dataset {dataset_name} updated: {result.new_samples} new samples, total {result.total_samples}")

        except Exception as e:
            logger.error(f"Failed to update dataset {dataset_name}: {e}")
            result.details["error"] = str(e)

        return result

    def is_update_due(self) -> bool:
        """Check if an update is due."""
        if not self.last_update:
            return True
        return (datetime.now() - self.last_update) > self.update_interval

    def get_dataset_info(self, dataset_name: str = "sensor_data") -> Optional[Dict[str, Any]]:
        """Get info about a dataset."""
        dataset_path = self.dataset_dir / f"{dataset_name}.parquet"
        if not dataset_path.exists():
            return None

        df = pd.read_parquet(dataset_path)
        return {
            "name": dataset_name,
            "rows": len(df),
            "columns": list(df.columns),
            "last_update": self.last_update.isoformat() if self.last_update else None
        }
