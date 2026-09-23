"""Protocol constants for the LoRa communication foundation."""

from __future__ import annotations

from enum import IntEnum


PROTOCOL_VERSION = 1
MAX_PAYLOAD_BYTES = 180
HEADER_WITHOUT_CRC_BYTES = 14
CRC_BYTES = 2
MAX_PACKET_BYTES = HEADER_WITHOUT_CRC_BYTES + MAX_PAYLOAD_BYTES + CRC_BYTES
BROADCAST_DEVICE_ID = 0xFFFF
GATEWAY_DEVICE_ID = 0x0001
DEFAULT_ACK_TIMEOUT_SECONDS = 2.0
DEFAULT_MAX_RETRIES = 3
ACK_TIMEOUT_MS = int(DEFAULT_ACK_TIMEOUT_SECONDS * 1000)
MAX_RETRIES = DEFAULT_MAX_RETRIES
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 60.0
DEFAULT_DEVICE_TIMEOUT_SECONDS = 180.0
DUPLICATE_CACHE_SIZE = 128


class PacketType(IntEnum):
    """Supported packet types on the irrigation LoRa network."""

    HELLO = 1
    HEARTBEAT = 2
    SENSOR_DATA = 3
    NPK_DATA = 4
    PUMP_STATUS = 5
    COMMAND = 6
    ACK = 7
    ERROR = 8
    CONFIG = 9
    PING = 10
    PONG = 11


class CommandType(IntEnum):
    """Supported gateway command types."""

    MOTOR_ON = 1
    MOTOR_OFF = 2
    REQUEST_STATUS = 3
    SYNC_TIME = 4
    RESTART_DEVICE = 5
    UPDATE_CONFIG = 6
    EMERGENCY_STOP = 7


class DeviceType(IntEnum):
    """Known device roles in the fixed architecture."""

    GATEWAY = 1
    SENSOR_NODE = 2
    NPK_NODE = 3
    PUMP_CONTROLLER = 4


class ValidationErrorCode(IntEnum):
    """Packet validation error codes used for local logging and ERROR packets."""

    INVALID_VERSION = 1
    INVALID_PACKET_TYPE = 2
    INVALID_PAYLOAD_LENGTH = 3
    CRC_MISMATCH = 4
    INVALID_SEQUENCE = 5
    DUPLICATE_PACKET = 6
    UNAUTHORIZED_SOURCE = 7
    MALFORMED_PAYLOAD = 8


ACK_REQUIRED_PACKET_TYPES = frozenset(
    {
        PacketType.HELLO,
        PacketType.SENSOR_DATA,
        PacketType.NPK_DATA,
        PacketType.PUMP_STATUS,
        PacketType.COMMAND,
        PacketType.CONFIG,
        PacketType.PING,
    }
)
