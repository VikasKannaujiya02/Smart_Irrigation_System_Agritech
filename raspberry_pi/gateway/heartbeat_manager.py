"""Heartbeat state and timeout detection for LoRa devices."""

from __future__ import annotations

import time

from ..communication.protocol_constants import DEFAULT_DEVICE_TIMEOUT_SECONDS
from .device_registry import DeviceRegistry


class HeartbeatManager:
    """Detects offline and reconnected devices from heartbeat activity."""

    def __init__(
        self,
        device_registry: DeviceRegistry,
        device_timeout_seconds: float = DEFAULT_DEVICE_TIMEOUT_SECONDS,
    ) -> None:
        self._device_registry = device_registry
        self._device_timeout_seconds = device_timeout_seconds

    def record_heartbeat(self, device_id: int, sequence_number: int) -> None:
        """Record heartbeat activity for a device."""
        self._device_registry.mark_seen(device_id, sequence_number)

    def detect_offline_devices(self) -> list[int]:
        """Mark and return devices whose heartbeat timeout expired."""
        now = time.monotonic()
        offline: list[int] = []
        for record in self._device_registry.all_devices():
            if record.is_online and now - record.last_seen > self._device_timeout_seconds:
                self._device_registry.mark_offline(record.device_id)
                offline.append(record.device_id)
        return offline
