"""High-level communication manager for packet send and receive workflows."""

from __future__ import annotations

import logging

from .ack_manager import AckManager
from .command_manager import CommandManager
from .packet import Packet
from .packet_builder import PacketBuilder
from .packet_parser import PacketParser
from .packet_validator import PacketValidator, ValidationResult
from .protocol_constants import GATEWAY_DEVICE_ID
from .retry_manager import RetryManager


class CommunicationManager:
    """Coordinates parsing, validation, ACK, retry, and serialization."""

    def __init__(
        self,
        local_device_id: int = GATEWAY_DEVICE_ID,
        logger: logging.Logger | None = None,
        ack_manager: AckManager | None = None,
        retry_manager: RetryManager | None = None,
    ) -> None:
        self.local_device_id = local_device_id
        self.logger = logger or logging.getLogger(__name__)
        self.parser = PacketParser()
        self.builder = PacketBuilder()
        self.validator = PacketValidator()
        self.command_manager = CommandManager(gateway_device_id=local_device_id)
        self.ack_manager = ack_manager or AckManager()
        self.retry_manager = retry_manager or RetryManager()

    def receive(self, raw_packet: bytes) -> tuple[Packet, ValidationResult]:
        """Parse and validate inbound bytes."""
        packet = self.parser.parse(raw_packet)
        validation = self.validator.validate(packet, local_device_id=self.local_device_id)
        if not validation.is_valid:
            self.logger.warning(
                "Invalid packet source=%s sequence=%s errors=%s",
                packet.source_device,
                packet.sequence_number,
                [error.name for error in validation.errors],
            )
        return packet, validation

    def serialize_for_send(self, packet: Packet) -> bytes:
        """Serialize outbound packet and register ACK tracking if needed."""
        raw = self.builder.to_bytes(packet)
        if packet.requires_ack():
            self.ack_manager.register(packet)
        return raw

    def process_ack(self, packet: Packet) -> Packet | None:
        """Process an ACK packet and return the acknowledged packet if matched."""
        acknowledged = self.ack_manager.acknowledge(packet)
        if acknowledged:
            self.logger.info(
                "ACK received destination=%s sequence=%s",
                acknowledged.destination_device,
                acknowledged.sequence_number,
            )
        return acknowledged

    def retry_expired_packets(self) -> list[Packet]:
        """Return packets that should be retransmitted after ACK timeout."""
        packets_to_retry: list[Packet] = []
        for pending in self.ack_manager.expired():
            decision = self.retry_manager.decide(pending)
            if decision.should_retry:
                self.ack_manager.refresh(pending.packet, attempts=decision.attempts)
                packets_to_retry.append(pending.packet)
                self.logger.debug(
                    "Retrying packet destination=%s sequence=%s attempt=%s",
                    pending.packet.destination_device,
                    pending.packet.sequence_number,
                    decision.attempts,
                )
            else:
                self.ack_manager.remove(pending.packet)
                self.logger.debug(
                    "Packet delivery failed destination=%s sequence=%s reason=%s",
                    pending.packet.destination_device,
                    pending.packet.sequence_number,
                    decision.reason,
                )
        return packets_to_retry