"""Build binary packets for the LoRa protocol."""

from __future__ import annotations

import struct
import time

from .crc import calculate_crc16
from .packet import Packet
from .protocol_constants import MAX_PAYLOAD_BYTES, PacketType, PROTOCOL_VERSION


HEADER_FORMAT = ">BBHHIHH"
CRC_FORMAT = ">H"


class PacketBuildError(ValueError):
    """Raised when a packet cannot be built safely."""


class PacketBuilder:
    """Creates validated packet objects and their wire representation."""

    def build(
        self,
        packet_type: PacketType,
        source_device: int,
        destination_device: int,
        sequence_number: int,
        payload: bytes = b"",
        timestamp: int | None = None,
    ) -> Packet:
        """Build a packet and calculate its CRC."""
        timestamp_value = int(time.time()) if timestamp is None else timestamp
        self._validate_build_inputs(
            source_device=source_device,
            destination_device=destination_device,
            sequence_number=sequence_number,
            payload=payload,
        )
        header = self._pack_header(
            packet_type=packet_type,
            source_device=source_device,
            destination_device=destination_device,
            timestamp=timestamp_value,
            sequence_number=sequence_number,
            payload_length=len(payload),
        )
        crc = calculate_crc16(header + payload)
        return Packet(
            packet_version=PROTOCOL_VERSION,
            packet_type=packet_type,
            source_device=source_device,
            destination_device=destination_device,
            timestamp=timestamp_value,
            sequence_number=sequence_number,
            payload=payload,
            crc=crc,
        )

    def to_bytes(self, packet: Packet) -> bytes:
        """Serialize a packet into big-endian wire bytes."""
        header = self._pack_header(
            packet_type=packet.packet_type,
            source_device=packet.source_device,
            destination_device=packet.destination_device,
            timestamp=packet.timestamp,
            sequence_number=packet.sequence_number,
            payload_length=packet.payload_length,
            packet_version=packet.packet_version,
        )
        expected_crc = calculate_crc16(header + packet.payload)
        if packet.crc != expected_crc:
            raise PacketBuildError("Packet CRC does not match serialized content")
        return header + packet.payload + struct.pack(CRC_FORMAT, packet.crc)

    def _pack_header(
        self,
        packet_type: PacketType,
        source_device: int,
        destination_device: int,
        timestamp: int,
        sequence_number: int,
        payload_length: int,
        packet_version: int = PROTOCOL_VERSION,
    ) -> bytes:
        return struct.pack(
            HEADER_FORMAT,
            packet_version,
            int(packet_type),
            source_device,
            destination_device,
            timestamp,
            sequence_number,
            payload_length,
        )

    def _validate_build_inputs(
        self,
        source_device: int,
        destination_device: int,
        sequence_number: int,
        payload: bytes,
    ) -> None:
        if not 0 <= source_device <= 0xFFFF:
            raise PacketBuildError("source_device must fit uint16")
        if not 0 <= destination_device <= 0xFFFF:
            raise PacketBuildError("destination_device must fit uint16")
        if not 0 <= sequence_number <= 0xFFFF:
            raise PacketBuildError("sequence_number must fit uint16")
        if len(payload) > MAX_PAYLOAD_BYTES:
            raise PacketBuildError("payload exceeds maximum LoRa payload size")
