"""Comprehensive Backup and Restore Manager for AI Smart Irrigation System."""

import logging
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from ..configuration_manager import config_manager
from ..database.backup import DatabaseBackupManager
from ..database.connection import SQLiteConnectionPool

logger = logging.getLogger(__name__)


class BackupManager:
    def __init__(self):
        self.config = config_manager.get_config()
        self.base_dir = Path(__file__).parent.parent.parent
        self.backup_dir = self.base_dir / self.config.database.backup_directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        db_path = self.base_dir / self.config.database.sqlite_path
        self.db_pool = SQLiteConnectionPool(db_path)
        self.db_backup = DatabaseBackupManager(self.db_pool, self.backup_dir)

    def create_full_backup(self) -> Path:
        """Create full system backup: database, models, configs, logs."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = self.backup_dir / f"irrigation_full_{timestamp}.tar.gz"

        with tarfile.open(backup_path, "w:gz") as tar:
            # Add database
            db_path = self.base_dir / self.config.database.sqlite_path
            if db_path.exists():
                tar.add(db_path, arcname=f"data/sqlite/{db_path.name}")

            # Add configs
            config_dir = self.base_dir / "configs"
            if config_dir.exists():
                tar.add(config_dir, arcname="configs")

            # Add models
            models_dir = self.base_dir / "raspberry_pi" / "ai" / "models"
            if models_dir.exists():
                tar.add(models_dir, arcname="raspberry_pi/ai/models")

            # Add logs (latest)
            log_dir = self.base_dir / self.config.logging.directory
            if log_dir.exists():
                tar.add(log_dir, arcname="logs")

        logger.info(f"Full backup created at {backup_path}")
        return backup_path

    def restore_backup(self, backup_path: Path) -> bool:
        """Restore from full backup."""
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False

        try:
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(self.base_dir)
            logger.info(f"Full backup restored from {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False

    def list_backups(self) -> List[Path]:
        """List all available backups."""
        backups = []
        for file in self.backup_dir.glob("*.tar.gz"):
            backups.append(file)
        for file in self.backup_dir.glob("*.db"):
            backups.append(file)
        return sorted(backups, key=lambda p: p.stat().st_mtime, reverse=True)

    def cleanup_old_backups(self, keep_count: int = 10) -> None:
        """Cleanup old backups, keep latest N."""
        backups = self.list_backups()
        if len(backups) > keep_count:
            for backup in backups[keep_count:]:
                backup.unlink()
                logger.info(f"Removed old backup: {backup}")
