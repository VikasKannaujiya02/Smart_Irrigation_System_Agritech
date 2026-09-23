"""Data collection adapters for gateway-originated sensor packets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CollectedPacket:
    """Normalized packet collected from the LoRa gateway."""

    source_device: int
    sequence_number: int
    packet_type: str
    payload: dict[str, Any]


class DataCollector:
    """Collects packets by delegating raw frame handling to the existing Gateway."""

    def __init__(self, gateway):
        self.gateway = gateway

    def collect_raw(self, raw_packet: bytes):
        """Parse a raw packet through the configured gateway."""
        return self.gateway.handle_raw_packet(raw_packet)
