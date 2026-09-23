"""Central logging setup for Raspberry Pi services."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(level: str = "INFO", directory: str = "logs", file_name: str = "system.log") -> None:
    """Configure console and rotating file logging."""
    Path(directory).mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    if not any(isinstance(handler, logging.StreamHandler) for handler in root_logger.handlers):
        stream = logging.StreamHandler()
        stream.setFormatter(formatter)
        root_logger.addHandler(stream)
    log_path = Path(directory) / file_name
    if not any(isinstance(handler, RotatingFileHandler) and Path(handler.baseFilename) == log_path for handler in root_logger.handlers):
        file_handler = RotatingFileHandler(log_path, maxBytes=10_000_000, backupCount=5)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
