"""OTA Update Manager for AI Smart Irrigation System."""

import logging
import requests
import hashlib
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from ..configuration_manager import config_manager

logger = logging.getLogger(__name__)


class UpdateStatus(Enum):
    IDLE = "idle"
    CHECKING = "checking"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    APPLYING = "applying"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class UpdateInfo:
    version: str
    download_url: str
    checksum: str
    changelog: str
    release_notes: str
    size_bytes: int


class OTAUpdateManager:
    def __init__(self):
        self.config = config_manager.get_config()
        self.current_version = "1.0.0"
        self.status = UpdateStatus.IDLE
        self.last_check: Optional[str] = None
        self.pending_update: Optional[UpdateInfo] = None
        self.update_dir = Path(__file__).parent.parent.parent / "data" / "updates"
        self.update_dir.mkdir(parents=True, exist_ok=True)

    def check_for_updates(self) -> Optional[UpdateInfo]:
        """Check OTA server for updates."""
        if not self.config.ota.enabled:
            logger.info("OTA updates are disabled")
            return None

        self.status = UpdateStatus.CHECKING
        logger.info("Checking for OTA updates")

        try:
            response = requests.get(
                f"{self.config.ota.server_url}/api/v1/updates/latest",
                params={"current_version": self.current_version},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if data.get("update_available", False):
                self.pending_update = UpdateInfo(
                    version=data["version"],
                    download_url=data["download_url"],
                    checksum=data["checksum"],
                    changelog=data.get("changelog", ""),
                    release_notes=data.get("release_notes", ""),
                    size_bytes=data.get("size_bytes", 0)
                )
                logger.info(f"Update available: {self.pending_update.version}")
                self.last_check = self.pending_update.version
                self.status = UpdateStatus.IDLE
                return self.pending_update
            else:
                logger.info("No updates available")
                self.status = UpdateStatus.IDLE
                return None
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")
            self.status = UpdateStatus.FAILED
            return None

    def download_update(self, update: UpdateInfo) -> Optional[Path]:
        """Download update file."""
        self.status = UpdateStatus.DOWNLOADING
        logger.info(f"Downloading update {update.version}")

        try:
            response = requests.get(update.download_url, stream=True, timeout=300)
            response.raise_for_status()

            file_path = self.update_dir / f"update_{update.version}.tar.gz"
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Verify checksum
            if not self._verify_checksum(file_path, update.checksum):
                logger.error("Update checksum verification failed")
                file_path.unlink()
                self.status = UpdateStatus.FAILED
                return None

            self.status = UpdateStatus.VERIFYING
            logger.info(f"Update downloaded and verified: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to download update: {e}")
            self.status = UpdateStatus.FAILED
            return None

    def _verify_checksum(self, file_path: Path, expected_sha256: str) -> bool:
        """Verify SHA256 checksum of file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest() == expected_sha256

    def apply_update(self, file_path: Path) -> bool:
        """Apply the update.

        Note: this project does not yet implement extraction/installation of the
        downloaded update package. Rather than falsely reporting success, this
        method fails loudly so callers (and the dashboard) never believe an
        update was applied when nothing changed.
        """
        self.status = UpdateStatus.APPLYING
        logger.info(f"Applying update from {file_path}")

        if self.pending_update is None:
            logger.error("apply_update() called with no pending update")
            self.status = UpdateStatus.FAILED
            return False

        try:
            raise NotImplementedError(
                "OTA update application (extract/install/restart) is not implemented"
            )
        except Exception as e:
            logger.error(f"Failed to apply update: {e}")
            self.status = UpdateStatus.FAILED
            return False
