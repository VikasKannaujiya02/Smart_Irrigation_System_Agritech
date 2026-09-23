# Module Dependency Graph

## Runtime Dependency Map

```mermaid
graph TD
  FirmwareSensor[ESP8266 Sensor Node Firmware] --> LoRaPacket[LoRa Packet]
  FirmwareNPK[Arduino UNO + RS485 + NPK Firmware] --> LoRaPacket
  FirmwarePump[ESP8266 Pump Controller Firmware] <--> LoRaPacket
  LoRaPacket --> Gateway[raspberry_pi.gateway]
  Gateway --> Communication[raspberry_pi.communication]
  Communication --> Parser[PacketParser / PacketValidator / AckManager / RetryManager]
  Parser --> Database[raspberry_pi.database]
  Database --> Repositories[RepositoryRegistry]
  Repositories --> DataProcessing[raspberry_pi.data_processing]
  DataProcessing --> AI[raspberry_pi.ai]
  AI --> DecisionEngine[raspberry_pi.decision_engine]
  DecisionEngine --> SafetyLayer[raspberry_pi.safety_layer]
  SafetyLayer --> CommandExecutor[CommandExecutor]
  CommandExecutor --> Gateway
  Gateway --> SX1278[SX1278 Serial Transport]
  DecisionEngine --> DigitalTwin[raspberry_pi.digital_twin]
  Repositories --> Analytics[raspberry_pi.analytics]
  Repositories --> Dashboard[raspberry_pi.dashboard]
  Repositories --> Alerts[raspberry_pi.alert_manager]
  Database --> Backup[raspberry_pi.backup]
  Configs[configs/*.yaml] --> ConfigurationManager[raspberry_pi.configuration_manager]
  ConfigurationManager --> Dashboard
  Weather[raspberry_pi.weather_api] --> DecisionEngine
```

## Status

All reported software integration gaps are resolved in existing modules. SX1278 radio behavior, pump ACK round trip, live sensor packets, and target TensorFlow inference are marked Hardware/Runtime Validation Required.
