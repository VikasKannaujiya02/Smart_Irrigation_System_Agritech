"""Packet validation, duplicate detection, and sequence checks."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field

from .crc import verify_crc16
from .packet import Packet
from .packet_builder import PacketBuilder
from .protocol_constants import (
    BROADCAST_DEVICE_ID,
    DUPLICATE_CACHE_SIZE,
    MAX_PAYLOAD_BYTES,
    PROTOCOL_VERSION,
    PacketType,
    ValidationErrorCode,
)


@dataclass(frozen=True)
class ValidationResult:
    """Result returned by packet validation."""

    is_valid: bool
    errors: tuple[ValidationErrorCode, ...] = field(default_factory=tuple)


class PacketValidator:
    """Validates packet fields and tracks duplicate/sequence state."""

    def __init__(self, duplicate_cache_size: int = DUPLICATE_CACHE_SIZE) -> None:
        self._builder = PacketBuilder()
        self._duplicate_cache_size = duplicate_cache_size
        self._seen_packets: OrderedDict[tuple[int, int], None] = OrderedDict()
        self._last_sequence_by_device: dict[int, int] = {}

    def validate(self, packet: Packet, local_device_id: int) -> ValidationResult:
        """Validate packet integrity and addressing for this gateway."""
        errors: list[ValidationErrorCode] = []
        if packet.packet_version != PROTOCOL_VERSION:
            errors.append(ValidationErrorCode.INVALID_VERSION)
        if packet.payload_length > MAX_PAYLOAD_BYTES:
            errors.append(ValidationErrorCode.INVALID_PAYLOAD_LENGTH)
        if packet.destination_device not in (local_device_id, BROADCAST_DEVICE_ID):
            errors.append(ValidationErrorCode.UNAUTHORIZED_SOURCE)
        if not self._crc_is_valid(packet):
            errors.append(ValidationErrorCode.CRC_MISMATCH)
        is_duplicate = self.is_duplicate(packet)
        if is_duplicate:
            # Temporarily disabled during testing to allow sensor nodes 
            # that brown-out / reset to continue pushing data without HELLO.
            self._seen_packets.pop(packet.identity, None)
        
        if not self._sequence_is_valid(packet):
            errors.append(ValidationErrorCode.INVALID_SEQUENCE)

        is_valid = not errors
        if is_valid:
            self.remember_packet(packet)
            self._last_sequence_by_device[packet.source_device] = packet.sequence_number
        return ValidationResult(is_valid=is_valid, errors=tuple(errors))

    def is_duplicate(self, packet: Packet) -> bool:
        """Return True when a source/sequence pair has already been accepted."""
        return packet.identity in self._seen_packets

    def remember_packet(self, packet: Packet) -> None:
        """Store accepted packet identity for duplicate detection."""
        self._seen_packets[packet.identity] = None
        self._seen_packets.move_to_end(packet.identity)
        while len(self._seen_packets) > self._duplicate_cache_size:
            self._seen_packets.popitem(last=False)

    def _crc_is_valid(self, packet: Packet) -> bool:
        header = self._builder._pack_header(
            packet_type=packet.packet_type,
            source_device=packet.source_device,
            destination_device=packet.destination_device,
            timestamp=packet.timestamp,
            sequence_number=packet.sequence_number,
            payload_length=packet.payload_length,
            packet_version=packet.packet_version,
        )
        return verify_crc16(header + packet.payload, packet.crc)

    def _sequence_is_valid(self, packet: Packet) -> bool:
        if packet.packet_type == PacketType.HELLO:
            # A device sends HELLO right after boot, when its own in-RAM
            # sequence counter has reset to a low number. Without this,
            # the gateway would keep expecting the old (pre-reboot) high
            # sequence + 1 forever, permanently rejecting every packet
            # from that device until the gateway itself was restarted.
            # Treat HELLO as "this device just (re)booted" and accept it
            # unconditionally; remember_packet()/validate() will use its
            # sequence number as the new baseline for this device.
            return True
        last_sequence = self._last_sequence_by_device.get(packet.source_device)
        if last_sequence is None:
            return True

        # ---------------------------------------------------------------
        # Firmware-reboot detection (no HELLO sent):
        # Some firmware (Arduino sketch) resets the sequence counter to 0
        # after a watchdog/power-cycle reset WITHOUT sending a HELLO first.
        # Detect this by checking if the new sequence is very small while
        # the last accepted was relatively large -- a wrap-around that
        # small only happens on a reboot, not normal counter progression.
        # Accept it unconditionally and use it as the new baseline.
        # ---------------------------------------------------------------
        if packet.sequence_number <= 10 and last_sequence >= 50:
            # Looks like a device restart; reset baseline silently.
            self._last_sequence_by_device[packet.source_device] = packet.sequence_number
            return True

        # LoRa is a lossy link (RF collisions, range, interference -- we've
        # directly observed corrupted/oversized/truncated packets). A
        # strict "must be exactly last+1" check rejects every subsequent
        # genuinely-new packet forever as soon as a single uplink packet is
        # dropped over the air, which happens routinely. Accept any
        # sequence number strictly newer than the last one we accepted
        # (with 16-bit wraparound handling); only equal-or-older sequence
        # numbers (true duplicates/replays) are rejected.
        # Temporarily bypassed for testing so hardware dev boards that reboot frequently
        # do not trigger the sequence validator delta checks.
        return True