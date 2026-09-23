"""Application-level database manager for gateway services."""

from __future__ import annotations

import logging
from pathlib import Path

from .database import Database


class DatabaseManager:
    """Provides lifecycle operations for the SQLite database layer."""

    def __init__(
        self,
        database_path: str | Path = "data/sqlite/irrigation.db",
        backup_directory: str | Path = "data/sqlite/backups",
        pool_size: int = 4,
        logger: logging.Logger | None = None,
    ) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.database = Database(
            database_path=database_path,
            backup_directory=backup_directory,
            pool_size=pool_size,
            logger=self.logger,
        )

    def start(self) -> None:
        """Initialize database layer for service use."""
        self.database.initialize()

    def stop(self) -> None:
        """Close database resources."""
        self.database.close()

    def backup_now(self) -> Path:
        """Create an immediate backup."""
        return self.database.backups.create_backup()

    def restore(self, backup_path: str | Path) -> None:
        """Restore a database backup."""
        self.database.backups.restore_backup(backup_path)
        self.database = Database(
            database_path=self.database.database_path,
            backup_directory=self.database.backup_directory,
            pool_size=self.database.pool_size,
            logger=self.logger,
        )
        self.database.initialize()

    def health_check(self) -> bool:
        """Return True when SQLite integrity check passes."""
        return self.database.backups.integrity_check()
