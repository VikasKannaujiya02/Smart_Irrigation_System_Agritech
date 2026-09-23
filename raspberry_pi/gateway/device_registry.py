"""Device registry for known LoRa nodes."""

from __future__ import annotations

import time
from dataclasses import dataclass

from ..communication.protocol_constants import DeviceType


@dataclass
class DeviceRecord:
    """Tracks current gateway knowledge for a field device."""

    device_id: int
    device_type: DeviceType
    name: str
    last_seen: float
    is_online: bool = True
    last_sequence_number: int | None = None


class DeviceRegistry:
    """Maintains device identity and online state."""

    def __init__(self) -> None:
        self._devices: dict[int, DeviceRecord] = {}

    def register(self, device_id: int, device_type: DeviceType, name: str) -> DeviceRecord:
        """Register or refresh a known device."""
        record = DeviceRecord(
            device_id=device_id,
            device_type=device_type,
            name=name,
            last_seen=time.monotonic(),
            is_online=True,
        )
        self._devices[device_id] = record
        return record

    def mark_seen(self, device_id: int, sequence_number: int | None = None) -> DeviceRecord:
        """Mark a device as seen and online."""
        record = self._devices.get(device_id)
        if record is None:
            record = self.register(device_id, DeviceType.SENSOR_NODE, f"unknown-{device_id}")
        record.last_seen = time.monotonic()
        record.is_online = True
        if sequence_number is not None:
            record.last_sequence_number = sequence_number
        return record

    def mark_offline(self, device_id: int) -> None:
        """Mark a device as offline."""
        if device_id in self._devices:
            self._devices[device_id].is_online = False

    def get(self, device_id: int) -> DeviceRecord | None:
        """Return a device record by id."""
        return self._devices.get(device_id)

    def all_devices(self) -> list[DeviceRecord]:
        """Return all registered device records."""
        return list(self._devices.values())
