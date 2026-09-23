"""Gateway packet handling for the Raspberry Pi LoRa service."""

from __future__ import annotations

import logging

from .device_registry import DeviceRegistry
from .heartbeat_manager import HeartbeatManager
from .lora_interface import LoRaInterface
from ..communication.communication_manager import CommunicationManager
from ..communication.packet import Packet
from ..communication.packet_parser import PacketParseError
from ..communication.protocol_constants import (
    GATEWAY_DEVICE_ID,
    PacketType,
    ValidationErrorCode,
)


class Gateway:
    """Coordinates LoRa transport with communication protocol handling."""

    def __init__(
        self,
        lora_interface: LoRaInterface,
        communication_manager: CommunicationManager | None = None,
        device_registry: DeviceRegistry | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.lora_interface = lora_interface
        self.communication_manager = communication_manager or CommunicationManager(
            local_device_id=GATEWAY_DEVICE_ID,
            logger=self.logger,
        )
        self.device_registry = device_registry or DeviceRegistry()
        self.heartbeat_manager = HeartbeatManager(self.device_registry)

    def handle_raw_packet(self, raw_packet: bytes) -> Packet | None:
        """Parse, validate, ACK, and register inbound packets."""
        try:
            packet, validation = self.communication_manager.receive(raw_packet)
        except PacketParseError as exc:
            self.logger.warning(
                "Ignoring malformed LoRa packet bytes=%s reason=%s",
                len(raw_packet),
                exc,
            )
            return None
        if not validation.is_valid:
            if validation.errors == (ValidationErrorCode.DUPLICATE_PACKET,):
                self._ack_duplicate(packet)
            return None

        self.device_registry.mark_seen(packet.source_device, packet.sequence_number)
        if packet.packet_type == PacketType.HEARTBEAT:
            self.heartbeat_manager.record_heartbeat(
                packet.source_device,
                packet.sequence_number,
            )
        if packet.packet_type == PacketType.ACK:
            self.communication_manager.process_ack(packet)
        elif packet.requires_ack():
            ack_packet = self.communication_manager.command_manager.build_ack(packet)
            self.send_packet(ack_packet)
        return packet

    def _ack_duplicate(self, packet: Packet) -> None:
        """ACK duplicate retransmissions without reprocessing payload."""
        if packet.requires_ack():
            ack_packet = self.communication_manager.command_manager.build_ack(packet)
            self.send_packet(ack_packet)

    def send_packet(self, packet: Packet) -> None:
        """Serialize and transmit a packet through LoRa."""
        raw_packet = self.communication_manager.serialize_for_send(packet)
        self.lora_interface.send_packet(raw_packet)

    def retry_due_packets(self) -> None:
        """Retransmit packets whose ACK timeout has expired."""
        for packet in self.communication_manager.retry_expired_packets():
            raw_packet = self.communication_manager.builder.to_bytes(packet)
            self.lora_interface.send_packet(raw_packet)
