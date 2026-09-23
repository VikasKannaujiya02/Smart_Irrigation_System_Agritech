# Communication Layer

Owns physical LoRa gateway access on Raspberry Pi 4 and provides reliable send and receive primitives to higher layers. It must not make irrigation decisions.

Implemented files:

- `communication_manager.py`: Coordinates parse, validation, ACK, retry, and serialization.
- `packet.py`: Immutable packet model.
- `packet_parser.py`: Converts wire bytes into packet objects.
- `packet_builder.py`: Builds packet objects and serialized bytes.
- `packet_validator.py`: Validates version, length, CRC, destination, duplicate state, and sequence.
- `command_manager.py`: Builds transport-level command, ACK, and ping packets.
- `ack_manager.py`: Tracks pending ACKs.
- `retry_manager.py`: Applies retry limits after ACK timeout.
- `crc.py`: CRC-16/CCITT-FALSE utility.
- `protocol_constants.py`: Packet types, command types, device types, and protocol limits.
