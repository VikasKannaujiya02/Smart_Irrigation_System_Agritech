"""Serial transport wrapper used by the LoRa gateway interface."""

from __future__ import annotations

import logging
from typing import Protocol


class SerialPort(Protocol):
    """Minimal serial port protocol required by the gateway."""

    def read(self, size: int = 1) -> bytes:
        """Read bytes from the serial port."""

    def write(self, data: bytes) -> int:
        """Write bytes to the serial port."""

    def close(self) -> None:
        """Close the serial port."""


class HardwareSerialPort:
    """PySerial-backed hardware port for the SX1278 LoRa adapter."""

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 2.0) -> None:
        if not port:
            raise RuntimeError("Hardware Validation Required: SX1278 serial port is not configured")
        try:
            import serial  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Hardware Validation Required: pyserial is required for SX1278 LoRa communication") from exc
        self._serial = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)

    def read(self, size: int = 1) -> bytes:
        return self._serial.read(size)

    def write(self, data: bytes) -> int:
        return int(self._serial.write(data))

    def close(self) -> None:
        self._serial.close()


class SerialInterface:
    """Provides safe read/write operations around a serial port object."""

    def __init__(self, serial_port: SerialPort, logger: logging.Logger | None = None) -> None:
        self._serial_port = serial_port
        self._logger = logger or logging.getLogger(__name__)

    def read(self, size: int) -> bytes:
        """Read up to size bytes from the serial transport."""
        if size <= 0:
            raise ValueError("size must be greater than zero")
        data = self._serial_port.read(size)
        self._logger.debug("Read %s bytes from serial transport", len(data))
        return data

    def write(self, data: bytes) -> int:
        """Write bytes to the serial transport."""
        if not data:
            raise ValueError("data must not be empty")
        written = self._serial_port.write(data)
        self._logger.debug("Wrote %s bytes to serial transport", written)
        return written

    def close(self) -> None:
        """Close the serial transport."""
        self._serial_port.close()
