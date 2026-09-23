"""Remote Configuration Manager for AI Smart Irrigation System."""

import logging
import requests
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from threading import Lock

from ..configuration_manager import config_manager

logger = logging.getLogger(__name__)


class RemoteConfigManager:
    def __init__(self):
        self.config = config_manager.get_config()
        self._lock = Lock()
        self._local_cache = Path(__file__).parent.parent.parent / "data" / "remote_config_cache.yaml"
        self._local_cache.parent.mkdir(parents=True, exist_ok=True)
        self._cached_config: Dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self):
        if self._local_cache.exists():
            try:
                with open(self._local_cache, "r") as f:
                    self._cached_config = yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"Failed to load remote config cache: {e}")
                self._cached_config = {}

    def _save_cache(self):
        try:
            with open(self._local_cache, "w") as f:
                yaml.dump(self._cached_config, f)
        except Exception as e:
            logger.error(f"Failed to save remote config cache: {e}")

    def fetch_config(self) -> Optional[Dict[str, Any]]:
        if not self.config.remote_config.enabled:
            return None

        try:
            logger.info("Fetching remote configuration")
            response = requests.get(
                self.config.remote_config.server_url,
                timeout=30
            )
            response.raise_for_status()
            remote_config = response.json()

            with self._lock:
                self._cached_config = remote_config
                self._save_cache()

            logger.info("Remote configuration fetched successfully")
            return remote_config
        except Exception as e:
            logger.error(f"Failed to fetch remote config: {e}")
            return None

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._cached_config.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return self._cached_config.copy()
