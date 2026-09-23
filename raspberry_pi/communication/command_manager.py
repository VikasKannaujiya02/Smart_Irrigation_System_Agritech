"""Command packet creation for gateway-to-node operations."""

from __future__ import annotations

from .packet import Packet
from .packet_builder import PacketBuilder
from .protocol_constants import CommandType, GATEWAY_DEVICE_ID, PacketType


class CommandManager:
    """Builds command packets without executing irrigation decisions."""

    def __init__(self, gateway_device_id: int = GATEWAY_DEVICE_ID) -> None:
        self._gateway_device_id = gateway_device_id
        self._builder = PacketBuilder()
        self._next_sequence = 1

    def build_command(
        self,
        destination_device: int,
        command_type: CommandType,
        parameters: dict[str, object] | None = None,
    ) -> Packet:
        """Build a command packet using the firmware command-byte payload."""
        payload = bytes([int(command_type)])
        packet = self._builder.build(
            packet_type=PacketType.COMMAND,
            source_device=self._gateway_device_id,
            destination_device=destination_device,
            sequence_number=self._allocate_sequence(),
            payload=payload,
        )
        return packet

    def build_ack(self, received_packet: Packet) -> Packet:
        """Build an ACK packet for a received packet."""
        return self._builder.build(
            packet_type=PacketType.ACK,
            source_device=self._gateway_device_id,
            destination_device=received_packet.source_device,
            sequence_number=self._allocate_sequence(),
            payload=received_packet.sequence_number.to_bytes(2, "big"),
        )

    def build_ping(self, destination_device: int) -> Packet:
        """Build a PING packet to verify remote connectivity."""
        return self._builder.build(
            packet_type=PacketType.PING,
            source_device=self._gateway_device_id,
            destination_device=destination_device,
            sequence_number=self._allocate_sequence(),
        )

    def _allocate_sequence(self) -> int:
        sequence = self._next_sequence
        self._next_sequence = (self._next_sequence + 1) & 0xFFFF
        if self._next_sequence == 0:
            self._next_sequence = 1
        return sequence
