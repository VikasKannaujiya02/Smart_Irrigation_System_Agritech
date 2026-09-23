"""Communication foundation package."""

from .packet import Packet, PacketType
from .protocol_constants import (
    GATEWAY_DEVICE_ID,
    CommandType,
    ValidationErrorCode,
    MAX_RETRIES,
    ACK_TIMEOUT_MS,
)
from .communication_manager import CommunicationManager
from .command_manager import CommandManager
from .packet_builder import PacketBuilder
from .packet_parser import PacketParser
from .packet_validator import PacketValidator, ValidationResult
from .ack_manager import AckManager
from .retry_manager import RetryManager
from .crc import calculate_crc16, verify_crc16

__all__ = [
    "Packet",
    "PacketType",
    "GATEWAY_DEVICE_ID",
    "CommandType",
    "ValidationErrorCode",
    "MAX_RETRIES",
    "ACK_TIMEOUT_MS",
    "CommunicationManager",
    "CommandManager",
    "PacketBuilder",
    "PacketParser",
    "PacketValidator",
    "ValidationResult",
    "AckManager",
    "RetryManager",
    "calculate_crc16",
    "verify_crc16",
]

