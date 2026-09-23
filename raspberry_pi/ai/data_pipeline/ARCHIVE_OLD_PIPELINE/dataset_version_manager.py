"""Dataset version manager for saving and loading datasets with metadata."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class DatasetVersionManager:
    """Manages dataset versions, including saving and loading."""

    def __init__(
        self,
        storage_dir: str | Path,
    ) -> None:
        """
        Initialize the version manager.

        Args:
            storage_dir: Directory to store datasets.
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._current_version: Optional[str] = None

    def save(
        self,
        train: pd.DataFrame,
        val: Optional[pd.DataFrame] = None,
        test: Optional[pd.DataFrame] = None,
        metadata: Optional[Dict[str, Any]] = None,
        version: Optional[str] = None,
    ) -> str:
        """
        Save dataset with versioning.

        Args:
            train: Training DataFrame.
            val: Validation DataFrame.
            test: Test DataFrame.
            metadata: Additional metadata.
            version: Optional version string (auto-generated if None).

        Returns:
            Version string.
        """
        if version is None:
            version = datetime.now().strftime("%Y%m%d_%H%M%S")

        version_dir = self.storage_dir / version
        version_dir.mkdir(parents=True, exist_ok=True)

        # Save data
        train.to_parquet(version_dir / "train.parquet", index=False)
        if val is not None:
            val.to_parquet(version_dir / "val.parquet", index=False)
        if test is not None:
            test.to_parquet(version_dir / "test.parquet", index=False)

        # Save metadata
        full_metadata = {
            "version": version,
            "created_at": datetime.now().isoformat(),
            "train_shape": train.shape,
            "val_shape": val.shape if val is not None else None,
            "test_shape": test.shape if test is not None else None,
            "columns": list(train.columns),
            "metadata": metadata or {},
        }

        with open(version_dir / "metadata.json", "w") as f:
            json.dump(full_metadata, f, indent=2, default=str)

        self._current_version = version
        logger.info(f"Saved dataset version {version}")
        return version

    def load(
        self,
        version: Optional[str] = None,
    ) -> tuple[pd.DataFrame, Optional[pd.DataFrame], Optional[pd.DataFrame], Dict[str, Any]]:
        """
        Load a dataset version.

        Args:
            version: Version to load (latest if None).

        Returns:
            Tuple of (train, val, test, metadata).
        """
        if version is None:
            version = self._get_latest_version()
            if version is None:
                raise ValueError("No dataset versions found")

        version_dir = self.storage_dir / version
        if not version_dir.exists():
            raise ValueError(f"Version {version} not found")

        train = pd.read_parquet(version_dir / "train.parquet")

        val = None
        if (version_dir / "val.parquet").exists():
            val = pd.read_parquet(version_dir / "val.parquet")

        test = None
        if (version_dir / "test.parquet").exists():
            test = pd.read_parquet(version_dir / "test.parquet")

        with open(version_dir / "metadata.json", "r") as f:
            metadata = json.load(f)

        self._current_version = version
        logger.info(f"Loaded dataset version {version}")
        return train, val, test, metadata

    def _get_latest_version(self) -> Optional[str]:
        """Get the latest version string."""
        versions = []
        for path in self.storage_dir.iterdir():
            if path.is_dir():
                versions.append(path.name)

        if not versions:
            return None

        return sorted(versions, reverse=True)[0]

    def list_versions(self) -> list[Dict[str, Any]]:
        """List all available versions with metadata."""
        versions = []
        for path in self.storage_dir.iterdir():
            if path.is_dir():
                metadata_path = path / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, "r") as f:
                        versions.append(json.load(f))
        return sorted(versions, key=lambda x: x["created_at"], reverse=True)

    def get_current_version(self) -> Optional[str]:
        """Get the current version."""
        return self._current_version
