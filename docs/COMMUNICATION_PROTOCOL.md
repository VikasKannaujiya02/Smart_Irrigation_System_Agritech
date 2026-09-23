# Communication Protocol

## Scope

This document defines the communication foundation between Raspberry Pi 4, Sensor Node, NPK Node, and Pump Controller. It covers LoRa packet structure, packet types, command types, acknowledgement, retry, timeout, duplicate detection, sequence validation, heartbeat, offline detection, and reconnect handling.

This phase does not implement AI, dashboard, database persistence, decision engine, or firmware.

## Devices

| Device | Role | Device Type |
| --- | --- | --- |
| Raspberry Pi 4 | Gateway and coordinator | `GATEWAY` |
| Sensor Node | Soil moisture, DHT22, battery telemetry | `SENSOR_NODE` |
| NPK Node | RS485 7 in 1 NPK and battery telemetry | `NPK_NODE` |
| Pump Controller | Relay, manual switch, pump feedback status | `PUMP_CONTROLLER` |

## Packet Format

All packet fields are serialized in big-endian byte order.

| Field | Size | Description |
| --- | ---: | --- |
| Packet Version | 1 byte | Protocol version. Current value is `1`. |
| Packet Type | 1 byte | Numeric packet type. |
| Source Device | 2 bytes | Device id of sender. |
| Destination Device | 2 bytes | Device id of receiver or `0xFFFF` broadcast. |
| Timestamp | 4 bytes | Unix timestamp in seconds. |
| Sequence Number | 2 bytes | Per-sender packet sequence, wraps after `65535`. |
| Payload Length | 2 bytes | Payload size in bytes. |
| Payload | 0-180 bytes | Packet-specific payload bytes. |
| CRC | 2 bytes | CRC-16/CCITT-FALSE over every previous field. |

The fixed header is 14 bytes. Maximum packet size is 196 bytes.

## Packet Types

| Type | Direction | ACK Required | Purpose |
| --- | --- | --- | --- |
| `HELLO` | Node to Gateway | Yes | Device announces boot or reconnect. |
| `HEARTBEAT` | Node to Gateway | No | Device proves it is alive. |
| `SENSOR_DATA` | Sensor Node to Gateway | Yes | Soil moisture, DHT22, and battery telemetry. |
| `NPK_DATA` | NPK Node to Gateway | Yes | NPK and battery telemetry. |
| `PUMP_STATUS` | Pump Controller to Gateway | Yes | Pump state, relay state, feedback, manual switch state. |
| `COMMAND` | Gateway to Node | Yes | Gateway command to a node. |
| `ACK` | Receiver to Sender | No | Acknowledges a received packet sequence. |
| `ERROR` | Any | No | Reports malformed payload, invalid state, or unsupported command. |
| `CONFIG` | Gateway to Node | Yes | Sends configuration update. |
| `PING` | Gateway to Node | Yes | Connectivity check. |
| `PONG` | Node to Gateway | No | Reply to ping. |

## Command Types

| Command | Target | Purpose |
| --- | --- | --- |
| `MOTOR_ON` | Pump Controller | Turn pump relay on when allowed by higher safety layers. |
| `MOTOR_OFF` | Pump Controller | Turn pump relay off. |
| `REQUEST_STATUS` | Any node | Request immediate status packet. |
| `SYNC_TIME` | Any node | Synchronize node clock to gateway time. |
| `RESTART_DEVICE` | Any node | Request controlled node restart. |
| `UPDATE_CONFIG` | Any node | Apply configuration values. |

The communication layer only transports commands. It does not decide when irrigation should happen.

## ACK Workflow

1. Sender builds a packet with a sequence number.
2. If the packet type requires ACK, the sender stores it in the pending ACK table.
3. Receiver validates version, length, CRC, destination, duplicate state, and sequence.
4. Receiver processes the packet only if validation succeeds.
5. Receiver sends an `ACK` payload containing the acknowledged 2-byte sequence number.
6. Sender removes the pending packet when the matching ACK arrives.

## Retry and Timeout

- Default ACK timeout is 2 seconds.
- Default retry limit is 3 retries.
- When timeout expires, the retry manager decides whether to retransmit.
- If the retry limit is exceeded, the packet is removed from pending ACK tracking and logged as delivery failure.

## Duplicate Packet Detection

The gateway stores accepted `(source_device, sequence_number)` identities in a bounded duplicate cache. If the same pair arrives again, the packet is not processed a second time. If the duplicated packet normally requires ACK, the gateway sends another ACK so a node can recover when the original ACK was lost.

## Sequence Validation

The gateway tracks the last accepted sequence number per source device. The next accepted sequence should equal the previous sequence plus one, wrapping at `65535`. This detects packet gaps and out-of-order delivery.

## Heartbeat Workflow

1. Each node sends `HEARTBEAT` at the configured interval.
2. Gateway updates the device registry `last_seen` timestamp.
3. Heartbeat manager checks device age.
4. If `last_seen` exceeds the timeout window, the device is marked offline.
5. A later `HELLO`, `HEARTBEAT`, or valid data packet marks the device online again.

## Reconnect Handling

After node restart or link recovery, the node should send `HELLO`. The gateway marks the device online and can respond with configuration or time sync in a later phase. Sequence state should be reset only after a validated reconnect policy is added to firmware and gateway together.

## Implemented Files

Communication layer:

- `raspberry_pi/communication/communication_manager.py`
- `raspberry_pi/communication/packet.py`
- `raspberry_pi/communication/packet_parser.py`
- `raspberry_pi/communication/packet_builder.py`
- `raspberry_pi/communication/packet_validator.py`
- `raspberry_pi/communication/command_manager.py`
- `raspberry_pi/communication/ack_manager.py`
- `raspberry_pi/communication/retry_manager.py`
- `raspberry_pi/communication/crc.py`
- `raspberry_pi/communication/protocol_constants.py`

Gateway layer:

- `raspberry_pi/gateway/gateway.py`
- `raspberry_pi/gateway/lora_interface.py`
- `raspberry_pi/gateway/serial_interface.py`
- `raspberry_pi/gateway/gateway_manager.py`
- `raspberry_pi/gateway/device_registry.py`
- `raspberry_pi/gateway/heartbeat_manager.py`
