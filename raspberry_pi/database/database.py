"""Database facade for the irrigation gateway SQLite store."""

from __future__ import annotations

import logging
from pathlib import Path

from .backup import DatabaseBackupManager
from .connection import SQLiteConnectionPool
from .migration import MigrationManager
from .repository import RepositoryRegistry


class Database:
    """Owns the connection pool, migrations, repositories, and backups."""

    def __init__(
        self,
        database_path: str | Path,
        backup_directory: str | Path,
        pool_size: int = 4,
        logger: logging.Logger | None = None,
    ) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.database_path = Path(database_path)
        self.backup_directory = Path(backup_directory)
        self.pool_size = pool_size
        self.connection_pool = SQLiteConnectionPool(
            database_path=self.database_path,
            pool_size=pool_size,
            logger=self.logger,
        )
        self.migrations = MigrationManager(self.connection_pool, logger=self.logger)
        self.repositories = RepositoryRegistry(self.connection_pool)
        self.backups = DatabaseBackupManager(
            self.connection_pool,
            backup_directory=self.backup_directory,
            logger=self.logger,
        )

    def initialize(self) -> None:
        """Create or migrate the database and verify integrity."""
        self.recover_if_needed()
        self.migrations.migrate()
        if not self.backups.integrity_check():
            raise RuntimeError("Database integrity check failed after initialization")
        self.logger.info("Database initialized")

    def recover_if_needed(self) -> None:
        """Restore latest backup if an existing database fails integrity check."""
        if not self.database_path.exists():
            return
        if self.backups.integrity_check():
            return
        latest_backup = self.backups.latest_backup()
        if latest_backup is None:
            raise RuntimeError("Database integrity check failed and no backup is available")
        self.logger.error("Database integrity failed; restoring latest backup")
        self.backups.restore_backup(latest_backup)
        self.connection_pool = SQLiteConnectionPool(
            database_path=self.database_path,
            pool_size=self.pool_size,
            logger=self.logger,
        )
        self.migrations = MigrationManager(self.connection_pool, logger=self.logger)
        self.repositories = RepositoryRegistry(self.connection_pool)
        self.backups = DatabaseBackupManager(
            self.connection_pool,
            backup_directory=self.backup_directory,
            logger=self.logger,
        )

    def close(self) -> None:
        """Close database resources."""
        self.connection_pool.close()