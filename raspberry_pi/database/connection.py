"""SQLite connection and connection-pool management."""

from __future__ import annotations

import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from queue import Empty, Queue
from typing import Iterator


class DatabaseConnectionError(RuntimeError):
    """Raised when a database connection cannot be provided."""


class SQLiteConnectionPool:
    """Small thread-safe SQLite connection pool for Raspberry Pi services."""

    def __init__(
        self,
        database_path: str | Path,
        pool_size: int = 4,
        timeout_seconds: float = 30.0,
        logger: logging.Logger | None = None,
    ) -> None:
        if pool_size <= 0:
            raise ValueError("pool_size must be greater than zero")
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.pool_size = pool_size
        self.timeout_seconds = timeout_seconds
        self.logger = logger or logging.getLogger(__name__)
        self._pool: Queue[sqlite3.Connection] = Queue(maxsize=pool_size)
        self._closed = False
        self._lock = threading.Lock()
        for _ in range(pool_size):
            self._pool.put(self._create_connection())

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Borrow a connection from the pool and return it automatically."""
        if self._closed:
            raise DatabaseConnectionError("Connection pool is closed")
        try:
            connection = self._pool.get(timeout=self.timeout_seconds)
        except Empty as exc:
            raise DatabaseConnectionError("Timed out waiting for database connection") from exc
        try:
            yield connection
        except sqlite3.Error:
            connection.rollback()
            self.logger.exception("Database operation failed and was rolled back")
            raise
        finally:
            if not self._closed:
                self._pool.put(connection)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run operations inside a transaction."""
        with self.connection() as connection:
            try:
                connection.execute("BEGIN")
                yield connection
                connection.commit()
            except sqlite3.Error:
                connection.rollback()
                self.logger.exception("Database transaction failed")
                raise

    def close(self) -> None:
        """Close every pooled connection."""
        with self._lock:
            self._closed = True
            while not self._pool.empty():
                connection = self._pool.get_nowait()
                connection.close()

    def _create_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=self.timeout_seconds,
            isolation_level=None,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = NORMAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

