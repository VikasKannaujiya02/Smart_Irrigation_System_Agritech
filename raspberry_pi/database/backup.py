"""SQLite backup, restore, and integrity utilities."""

from __future__ import annotations

import logging
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .connection import SQLiteConnectionPool


class DatabaseBackupError(RuntimeError):
    """Raised when backup or restore cannot complete."""


class DatabaseBackupManager:
    """Creates backups, restores backups, and checks database integrity."""

    def __init__(
        self,
        connection_pool: SQLiteConnectionPool,
        backup_directory: str | Path,
        logger: logging.Logger | None = None,
    ) -> None:
        self.connection_pool = connection_pool
        self.backup_directory = Path(backup_directory)
        self.backup_directory.mkdir(parents=True, exist_ok=True)
        self.logger = logger or logging.getLogger(__name__)

    def create_backup(self) -> Path:
        """Create a consistent SQLite backup using the SQLite backup API."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = self.backup_directory / f"irrigation_{timestamp}.db"
        with self.connection_pool.connection() as source_connection:
            destination = sqlite3.connect(backup_path)
            try:
                source_connection.backup(destination)
            finally:
                destination.close()
        self.logger.info("Database backup created at %s", backup_path)
        return backup_path

    def restore_backup(self, backup_path: str | Path) -> None:
        """Restore the database from a backup file."""
        source = Path(backup_path)
        if not source.exists():
            raise DatabaseBackupError(f"Backup file does not exist: {source}")
        self.connection_pool.close()
        shutil.copy2(source, self.connection_pool.database_path)
        self.logger.warning("Database restored from backup %s", source)

    def latest_backup(self) -> Path | None:
        """Return the newest backup file if one exists."""
        backups = sorted(
            self.backup_directory.glob("irrigation_*.db"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        return backups[0] if backups else None

    def integrity_check(self) -> bool:
        """Run SQLite PRAGMA integrity_check."""
        with self.connection_pool.connection() as connection:
            rows = connection.execute("PRAGMA integrity_check").fetchall()
        return all(row[0] == "ok" for row in rows)
