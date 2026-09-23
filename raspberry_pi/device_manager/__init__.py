"""Device management facade over the existing gateway DeviceRegistry."""

from __future__ import annotations

from raspberry_pi.gateway import DeviceRegistry


class DeviceManager:
    """Coordinates device seen-state using the canonical DeviceRegistry."""

    def __init__(self, registry: DeviceRegistry | None = None):
        self.registry = registry or DeviceRegistry()

    def mark_seen(self, device_id: int, sequence_number: int) -> None:
        self.registry.mark_seen(device_id, sequence_number)

    def is_duplicate(self, device_id: int, sequence_number: int) -> bool:
        return self.registry.is_duplicate(device_id, sequence_number)
