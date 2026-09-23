"""Configuration Manager for AI Smart Irrigation System."""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DatabaseConfig:
    sqlite_path: str
    backup_directory: str
    pool_size: int = 4
    timeout_seconds: int = 30
    integrity_check_on_startup: bool = True
    automatic_backup_enabled: bool = True


@dataclass
class LoggingConfig:
    level: str = "INFO"
    directory: str = "logs"
    file_max_bytes: int = 104857600
    file_backup_count: int = 20


@dataclass
class WeatherConfig:
    provider: str = "openweathermap"
    api_key: str = ""
    base_url: str = "https://api.openweathermap.org/data/2.5"
    timeout_seconds: int = 10
    retries: int = 3
    latitude: float = 0.0
    longitude: float = 0.0
    cache_dir: str = "data/weather_cache"
    cache_ttl_seconds: int = 1800
    rain_threshold_probability: float = 50.0
    rain_threshold_volume: float = 2.0
    rain_time_window_hours: int = 24
    critical_soil_moisture_threshold: float = 20.0


@dataclass
class HealthConfig:
    check_interval_seconds: int = 60
    enable_diagnostics: bool = True


@dataclass
class OTAConfig:
    enabled: bool = False
    server_url: str = ""
    check_interval_hours: int = 24


@dataclass
class RemoteConfig:
    enabled: bool = False
    server_url: str = ""
    poll_interval_seconds: int = 300


@dataclass
class SystemConfig:
    project_name: str = "AI Smart Irrigation Digital Twin"
    environment: Environment = Environment.PRODUCTION
    database: DatabaseConfig = field(default_factory=lambda: DatabaseConfig(
        sqlite_path="data/sqlite/irrigation.db",
        backup_directory="data/sqlite/backups"
    ))
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    health: HealthConfig = field(default_factory=HealthConfig)
    ota: OTAConfig = field(default_factory=OTAConfig)
    remote_config: RemoteConfig = field(default_factory=RemoteConfig)


class ConfigurationManager:
    _instance: Optional['ConfigurationManager'] = None
    _config: Optional[SystemConfig] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._load_config()

    def _load_config(self):
        load_dotenv()

        env = os.getenv("ENVIRONMENT", "production").lower()
        self._config_file = Path(__file__).parent.parent.parent / "configs" / f"{env}.yaml"

        if not self._config_file.exists():
            self._config_file = Path(__file__).parent.parent.parent / "configs" / "system.yaml"

        logger.info(f"Loading configuration from {self._config_file}")

        with open(self._config_file, "r") as f:
            config_data = yaml.safe_load(f)

        self._config = self._parse_config(config_data)
        self._override_from_env()

    def _parse_config(self, data: Dict[str, Any]) -> SystemConfig:
        project_data = data.get("project", {})
        db_data = data.get("database", {})
        log_data = data.get("logging", {})
        weather_data = data.get("weather", {})
        health_data = data.get("health", {})
        ota_data = data.get("ota", {})
        remote_data = data.get("remote_config", {})

        return SystemConfig(
            project_name=project_data.get("name", "AI Smart Irrigation Digital Twin"),
            environment=Environment(project_data.get("environment", "production")),
            database=DatabaseConfig(
                sqlite_path=db_data.get("sqlite_path", "data/sqlite/irrigation.db"),
                backup_directory=db_data.get("backup_directory", "data/sqlite/backups"),
                pool_size=db_data.get("pool_size", 4),
                timeout_seconds=db_data.get("timeout_seconds", 30),
                integrity_check_on_startup=db_data.get("integrity_check_on_startup", True),
                automatic_backup_enabled=db_data.get("automatic_backup_enabled", True)
            ),
            logging=LoggingConfig(
                level=log_data.get("level", "INFO"),
                directory=log_data.get("directory", "logs"),
                file_max_bytes=log_data.get("file_max_bytes", 104857600),
                file_backup_count=log_data.get("file_backup_count", 20)
            ),
            weather=WeatherConfig(
                provider=weather_data.get("provider", "openweathermap"),
                api_key=weather_data.get("api_key", ""),
                base_url=weather_data.get("base_url", "https://api.openweathermap.org/data/2.5"),
                timeout_seconds=weather_data.get("timeout_seconds", 10),
                retries=weather_data.get("retries", 3),
                latitude=weather_data.get("latitude", 0.0),
                longitude=weather_data.get("longitude", 0.0),
                cache_dir=weather_data.get("cache_dir", "data/weather_cache"),
                cache_ttl_seconds=weather_data.get("cache_ttl_seconds", 1800),
                rain_threshold_probability=weather_data.get("rain_threshold_probability", 50.0),
                rain_threshold_volume=weather_data.get("rain_threshold_volume", 2.0),
                rain_time_window_hours=weather_data.get("rain_time_window_hours", 24),
                critical_soil_moisture_threshold=weather_data.get("critical_soil_moisture_threshold", 20.0)
            ),
            health=HealthConfig(
                check_interval_seconds=health_data.get("check_interval_seconds", 60),
                enable_diagnostics=health_data.get("enable_diagnostics", True)
            ),
            ota=OTAConfig(
                enabled=ota_data.get("enabled", False),
                server_url=ota_data.get("server_url", ""),
                check_interval_hours=ota_data.get("check_interval_hours", 24)
            ),
            remote_config=RemoteConfig(
                enabled=remote_data.get("enabled", False),
                server_url=remote_data.get("server_url", ""),
                poll_interval_seconds=remote_data.get("poll_interval_seconds", 300)
            )
        )

    def _override_from_env(self):
        if os.getenv("WEATHER_API_KEY"):
            self._config.weather.api_key = os.getenv("WEATHER_API_KEY")
        if os.getenv("WEATHER_LATITUDE"):
            self._config.weather.latitude = float(os.getenv("WEATHER_LATITUDE"))
        if os.getenv("WEATHER_LONGITUDE"):
            self._config.weather.longitude = float(os.getenv("WEATHER_LONGITUDE"))
        if os.getenv("LOG_LEVEL"):
            self._config.logging.level = os.getenv("LOG_LEVEL")
        if os.getenv("OTA_UPDATE_SERVER"):
            self._config.ota.server_url = os.getenv("OTA_UPDATE_SERVER")
            self._config.ota.enabled = True
        if os.getenv("REMOTE_CONFIG_URL"):
            self._config.remote_config.server_url = os.getenv("REMOTE_CONFIG_URL")
            self._config.remote_config.enabled = True

    def get_config(self) -> SystemConfig:
        return self._config

    def reload(self):
        logger.info("Reloading configuration")
        self._load_config()


config_manager = ConfigurationManager()
