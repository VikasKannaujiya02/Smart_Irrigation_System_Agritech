"""Schema migration support for the SQLite database."""

from __future__ import annotations

import logging

from .connection import SQLiteConnectionPool
from .schema import SCHEMA_SQL, SCHEMA_VERSION


class MigrationError(RuntimeError):
    """Raised when database migration fails."""


class MigrationManager:
    """Applies versioned schema migrations."""

    def __init__(self, connection_pool: SQLiteConnectionPool, logger: logging.Logger | None = None) -> None:
        self.connection_pool = connection_pool
        self.logger = logger or logging.getLogger(__name__)

    def migrate(self) -> None:
        """Create or upgrade the database schema to the current version."""
        with self.connection_pool.transaction() as connection:
            current_version = self.current_version(connection)
            if current_version > SCHEMA_VERSION:
                raise MigrationError(
                    f"Database version {current_version} is newer than supported {SCHEMA_VERSION}"
                )
            if current_version < 1:
                connection.executescript(SCHEMA_SQL)
                connection.execute(
                    """
                    INSERT OR IGNORE INTO SchemaMigrations(version, description)
                    VALUES (?, ?)
                    """,
                    (SCHEMA_VERSION, "Initial production SQLite schema"),
                )
                self.logger.info("Database migrated to version %s", SCHEMA_VERSION)

    def current_version(self, connection) -> int:
        """Return current schema version, or zero for an empty database."""
        table_exists = connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'SchemaMigrations'
            """
        ).fetchone()
        if table_exists is None:
            return 0
        row = connection.execute("SELECT MAX(version) AS version FROM SchemaMigrations").fetchone()
        return int(row["version"] or 0)

