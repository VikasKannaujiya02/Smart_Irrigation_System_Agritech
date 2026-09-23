"""Recovery services for database backup and restore."""

from __future__ import annotations

from pathlib import Path


class RecoveryManager:
    """Coordinates database backup/restore through DatabaseManager."""

    def __init__(self, database_manager):
        self.database_manager = database_manager

    def create_restore_point(self) -> Path:
        return self.database_manager.backup_now()

    def restore(self, backup_path: str | Path) -> None:
        self.database_manager.restore(backup_path)
