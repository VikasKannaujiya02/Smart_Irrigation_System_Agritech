"""AI Smart Irrigation Digital Twin - Raspberry Pi Backend."""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

from .configuration_manager import config_manager


def setup_logging():
    """Setup application logging."""
    config = config_manager.get_config()
    log_level = getattr(logging, config.logging.level.upper(), logging.INFO)

    logger = logging.getLogger()
    logger.setLevel(log_level)

    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

    log_dir = Path(config.logging.directory)
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "irrigation.log",
        maxBytes=config.logging.file_max_bytes,
        backupCount=config.logging.file_backup_count
    )
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)

    return logger


# Initialize logging when module is imported
setup_logging()
