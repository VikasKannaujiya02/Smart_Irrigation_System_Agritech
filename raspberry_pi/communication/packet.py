"""Packet model for the smart irrigation LoRa protocol."""

from __future__ import annotations

from dataclasses import dataclass

from .protocol_constants import PacketType, PROTOCOL_VERSION


@dataclass(frozen=True)
class Packet:
    """Immutable packet exchanged between gateway and field nodes."""

    packet_version: int
    packet_type: PacketType
    source_device: int
    destination_device: int
    timestamp: int
    sequence_number: int
    payload: bytes
    crc: int

    @property
    def payload_length(self) -> int:
        """Return payload length in bytes."""
        return len(self.payload)

    @property
    def identity(self) -> tuple[int, int]:
        """Return the source and sequence identity used for duplicate checks."""
        return (self.source_device, self.sequence_number)

    def requires_ack(self) -> bool:
        """Return True when this packet type expects acknowledgement."""
        from .protocol_constants import ACK_REQUIRED_PACKET_TYPES

        return self.packet_type in ACK_REQUIRED_PACKET_TYPES


def create_empty_packet(
    packet_type: PacketType,
    source_device: int,
    destination_device: int,
    timestamp: int,
    sequence_number: int,
    crc: int,
) -> Packet:
    """Create a packet with no payload."""
    return Packet(
        packet_version=PROTOCOL_VERSION,
        packet_type=packet_type,
        source_device=source_device,
        destination_device=destination_device,
        timestamp=timestamp,
        sequence_number=sequence_number,
        payload=b"",
        crc=crc,
    )
