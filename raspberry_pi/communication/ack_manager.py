"""ACK tracking for reliable LoRa communication."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .packet import Packet
from .protocol_constants import DEFAULT_ACK_TIMEOUT_SECONDS, PacketType


@dataclass
class PendingAck:
    """Tracks an outbound packet waiting for ACK."""

    packet: Packet
    deadline: float
    attempts: int = 1


class AckManager:
    """Registers outbound packets and resolves matching ACK packets."""

    def __init__(self, ack_timeout_seconds: float = DEFAULT_ACK_TIMEOUT_SECONDS) -> None:
        self._ack_timeout_seconds = ack_timeout_seconds
        self._pending: dict[tuple[int, int], PendingAck] = {}

    def register(self, packet: Packet) -> None:
        """Register a packet that requires ACK."""
        key = self._key(packet.destination_device, packet.sequence_number)
        self._pending[key] = PendingAck(
            packet=packet,
            deadline=time.monotonic() + self._ack_timeout_seconds,
        )

    def acknowledge(self, ack_packet: Packet) -> Packet | None:
        """Resolve a matching ACK packet and return the original packet."""
        if ack_packet.packet_type != PacketType.ACK:
            return None
        if len(ack_packet.payload) < 2:
            return None
        acknowledged_sequence = int.from_bytes(ack_packet.payload[:2], "big")
        key = self._key(ack_packet.source_device, acknowledged_sequence)
        pending = self._pending.pop(key, None)
        return pending.packet if pending else None

    def expired(self) -> list[PendingAck]:
        """Return pending ACKs whose timeout has elapsed."""
        now = time.monotonic()
        return [pending for pending in self._pending.values() if pending.deadline <= now]

    def remove(self, packet: Packet) -> None:
        """Remove pending ACK state for a packet."""
        self._pending.pop(self._key(packet.destination_device, packet.sequence_number), None)

    def refresh(self, packet: Packet, attempts: int) -> None:
        """Refresh ACK deadline after a retry attempt."""
        key = self._key(packet.destination_device, packet.sequence_number)
        self._pending[key] = PendingAck(
            packet=packet,
            deadline=time.monotonic() + self._ack_timeout_seconds,
            attempts=attempts,
        )

    def _key(self, remote_device: int, sequence_number: int) -> tuple[int, int]:
        return (remote_device, sequence_number)
