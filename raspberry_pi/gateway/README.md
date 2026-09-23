# Gateway

Coordinates LoRa ingestion from nodes, sends pump commands, routes validated packets to data collection and device management, and exposes gateway service lifecycle hooks.

Implemented communication-foundation files:

- `gateway.py`: Handles inbound packets, ACK replies, and retry transmission.
- `lora_interface.py`: LoRa SX1278 gateway transport abstraction.
- `serial_interface.py`: Serial transport wrapper for LoRa gateway access.
- `gateway_manager.py`: Gateway lifecycle wrapper.
- `device_registry.py`: Tracks known devices and online state.
- `heartbeat_manager.py`: Handles heartbeat updates, timeout detection, offline state, and reconnect marking.
