"""Parse binary LoRa frames into packet objects."""

from __future__ import annotations

import struct

from .packet import Packet
from .packet_builder import CRC_FORMAT, HEADER_FORMAT
from .protocol_constants import CRC_BYTES, HEADER_WITHOUT_CRC_BYTES, PacketType


class PacketParseError(ValueError):
    """Raised when raw bytes cannot be parsed as a protocol packet."""


class PacketParser:
    """Converts wire bytes into Packet objects."""

    def parse(self, raw_packet: bytes) -> Packet:
        """Parse raw bytes into a Packet without applying semantic validation."""
        minimum_length = HEADER_WITHOUT_CRC_BYTES + CRC_BYTES
        if len(raw_packet) < minimum_length:
            raise PacketParseError("Packet is shorter than minimum frame length")

        header = raw_packet[:HEADER_WITHOUT_CRC_BYTES]
        try:
            (
                packet_version,
                packet_type_value,
                source_device,
                destination_device,
                timestamp,
                sequence_number,
                payload_length,
            ) = struct.unpack(HEADER_FORMAT, header)
        except struct.error as exc:
            raise PacketParseError("Packet header is malformed") from exc

        expected_length = HEADER_WITHOUT_CRC_BYTES + payload_length + CRC_BYTES
        if len(raw_packet) != expected_length:
            raise PacketParseError("Packet length does not match payload_length")

        payload_start = HEADER_WITHOUT_CRC_BYTES
        payload_end = payload_start + payload_length
        payload = raw_packet[payload_start:payload_end]
        crc = struct.unpack(CRC_FORMAT, raw_packet[payload_end:])[0]

        try:
            packet_type = PacketType(packet_type_value)
        except ValueError as exc:
            raise PacketParseError("Unknown packet type") from exc

        return Packet(
            packet_version=packet_version,
            packet_type=packet_type,
            source_device=source_device,
            destination_device=destination_device,
            timestamp=timestamp,
            sequence_number=sequence_number,
            payload=payload,
            crc=crc,
        )
