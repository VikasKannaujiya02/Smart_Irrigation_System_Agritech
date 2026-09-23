#include "config.h"
#include "packet_builder.h"
#include "lora_manager.h"
#include "modbus_manager.h"
#include "npk_sensor.h"
#include "battery_manager.h"
#include "power_manager.h"
#include "heartbeat.h"

// Initialize managers
PacketBuilder packet_builder;
LoRaManager lora_manager;
ModbusManager modbus_manager;
NpkSensor npk_sensor(&modbus_manager);
BatteryManager battery_manager;
PowerManager power_manager;
Heartbeat heartbeat;

// State variables
uint16_t sequence_number = 0;
uint32_t last_sensor_read_ms = 0;
bool waiting_for_ack = false;
uint8_t retries_remaining = 0;
uint32_t ack_timeout_start_ms = 0;
Packet pending_packet;

void setup() {
  // Read reset cause BEFORE anything clears MCUSR, so we can tell if the
  // previous boot ended in a watchdog reset (this is what was happening
  // when Serial output looked garbled -- the board was restarting mid-print).
  uint8_t resetCause = MCUSR;
  MCUSR = 0;

  Serial.begin(9600);
  delay(50); // let the USB-serial bridge settle before printing
  Serial.println(F("=== NPK Node Starting ==="));

  Serial.print(F("Reset cause: "));
  if (resetCause & (1 << WDRF))  Serial.println(F("WATCHDOG RESET (this is the bug we're chasing)"));
  else if (resetCause & (1 << BORF)) Serial.println(F("Brown-out reset (power supply dip)"));
  else if (resetCause & (1 << EXTRF)) Serial.println(F("External reset (reset button/pin)"));
  else if (resetCause & (1 << PORF)) Serial.println(F("Power-on reset (normal power-up)"));
  else Serial.println(F("Unknown"));

  pinMode(STATUS_LED_PIN, OUTPUT);
  
  // Initialize managers
  modbus_manager.begin();
  npk_sensor.begin();
  power_manager.begin();
  heartbeat.begin();
  
  // Initialize LoRa
  if (lora_manager.begin()) {
    digitalWrite(STATUS_LED_PIN, HIGH);
    delay(100);
    digitalWrite(STATUS_LED_PIN, LOW);
  }
  
  // Send HELLO packet on startup
  sendHelloPacket();
}

void loop() {
  power_manager.resetWatchdog();
  
  // Check for incoming packets
  Packet incoming_packet;
  if (lora_manager.receivePacket(incoming_packet)) {
    handleIncomingPacket(incoming_packet);
  }
  
  // Handle ACK timeout and retries
  if (waiting_for_ack) {
    if (millis() - ack_timeout_start_ms >= DEFAULT_ACK_TIMEOUT_MS) {
      if (retries_remaining > 0) {
        lora_manager.sendPacket(pending_packet);
        retries_remaining--;
        ack_timeout_start_ms = millis();
      } else {
        waiting_for_ack = false;
      }
    }
  }
  
  // Check if it's time to read sensors
  if (!waiting_for_ack && (millis() - last_sensor_read_ms >= DEFAULT_SENSOR_INTERVAL_MS)) {
    sendNPKDataPacket();
    last_sensor_read_ms = millis();
  }
  
  // Check if it's time to send heartbeat
  if (!waiting_for_ack && heartbeat.shouldSend()) {
    sendHeartbeatPacket();
    heartbeat.reset();
  }
}

void sendHelloPacket() {
  Packet packet = packet_builder.build(
    PACKET_TYPE_HELLO,
    NPK_NODE_DEVICE_ID,
    GATEWAY_DEVICE_ID,
    sequence_number++
  );
  sendWithAck(packet);
}

void sendNPKDataPacket() {
  NPKData sensorData = npk_sensor.readAll();
  float batteryVoltage = battery_manager.readVoltage();

  // ---- Debug output so you can SEE actual sensor values on Serial Monitor ----
  // If this prints garbage/zeros/"valid=0", it's a wiring/register/config issue.
  // If these numbers look right but the RPi still shows nothing, the problem
  // is downstream (LoRa range, gateway, or RPi parsing) -- not this node.
  Serial.println(F("---- NPK_DATA packet being sent ----"));
  Serial.print(F("Valid        : ")); Serial.println(sensorData.valid ? "YES" : "NO (sensor read failed)");
  Serial.print(F("Nitrogen     : ")); Serial.println(sensorData.nitrogen);
  Serial.print(F("Phosphorus   : ")); Serial.println(sensorData.phosphorus);
  Serial.print(F("Potassium    : ")); Serial.println(sensorData.potassium);
  Serial.print(F("EC           : ")); Serial.println(sensorData.ec);
  Serial.print(F("pH           : ")); Serial.println(sensorData.ph, 2);
  Serial.print(F("Soil Temp    : ")); Serial.println(sensorData.soilTemp, 1);
  Serial.print(F("Soil Moisture: ")); Serial.println(sensorData.soilMoisture);
  Serial.print(F("Battery (V)  : ")); Serial.println(batteryVoltage, 2);
  Serial.println(F("------------------------------------"));

  uint8_t payload[30];
  uint16_t index = 0;
  
  // Nitrogen (2 bytes)
  payload[index++] = (sensorData.nitrogen >> 8) & 0xFF;
  payload[index++] = sensorData.nitrogen & 0xFF;
  
  // Phosphorus (2 bytes)
  payload[index++] = (sensorData.phosphorus >> 8) & 0xFF;
  payload[index++] = sensorData.phosphorus & 0xFF;
  
  // Potassium (2 bytes)
  payload[index++] = (sensorData.potassium >> 8) & 0xFF;
  payload[index++] = sensorData.potassium & 0xFF;
  
  // EC (4 bytes float)
  memcpy(payload + index, &sensorData.ec, 4);
  index += 4;
  
  // pH (4 bytes float)
  memcpy(payload + index, &sensorData.ph, 4);
  index += 4;
  
  // Soil Temperature (4 bytes float)
  memcpy(payload + index, &sensorData.soilTemp, 4);
  index += 4;
  
  // Soil Moisture (2 bytes)
  payload[index++] = (sensorData.soilMoisture >> 8) & 0xFF;
  payload[index++] = sensorData.soilMoisture & 0xFF;
  
  // Battery Voltage (4 bytes float)
  memcpy(payload + index, &batteryVoltage, 4);
  index += 4;
  
  // Valid flag (1 byte)
  payload[index++] = sensorData.valid ? 1 : 0;
  
  Packet packet = packet_builder.build(
    PACKET_TYPE_NPK_DATA,
    NPK_NODE_DEVICE_ID,
    GATEWAY_DEVICE_ID,
    sequence_number++,
    payload,
    index
  );
  Serial.println(F("Sending NPK_DATA packet over LoRa..."));
  sendWithAck(packet);
}

void sendHeartbeatPacket() {
  Packet packet = packet_builder.build(
    PACKET_TYPE_HEARTBEAT,
    NPK_NODE_DEVICE_ID,
    GATEWAY_DEVICE_ID,
    sequence_number++
  );
  lora_manager.sendPacket(packet);
}

void sendWithAck(Packet& packet) {
  pending_packet = packet;
  waiting_for_ack = true;
  retries_remaining = DEFAULT_MAX_RETRIES;
  ack_timeout_start_ms = millis();
  lora_manager.sendPacket(packet);
}

void handleIncomingPacket(Packet& packet) {
  if (packet.destination_device != NPK_NODE_DEVICE_ID && packet.destination_device != BROADCAST_DEVICE_ID) {
    return;
  }
  
  digitalWrite(STATUS_LED_PIN, HIGH);
  delay(50);
  digitalWrite(STATUS_LED_PIN, LOW);
  
  switch (packet.packet_type) {
    case PACKET_TYPE_ACK:
      handleAckPacket(packet);
      break;
    case PACKET_TYPE_COMMAND:
      handleCommandPacket(packet);
      break;
    case PACKET_TYPE_CONFIG:
      handleConfigPacket(packet);
      break;
    case PACKET_TYPE_PING:
      handlePingPacket(packet);
      break;
    default:
      break;
  }
}

void handleAckPacket(Packet& packet) {
  if (waiting_for_ack) {
    uint16_t acked_sequence = (packet.payload[0] << 8) | packet.payload[1];
    if (acked_sequence == pending_packet.sequence_number) {
      waiting_for_ack = false;
    }
  }
}

void handleCommandPacket(Packet& packet) {
  uint8_t command_type = packet.payload[0];
  
  switch (command_type) {
    case COMMAND_TYPE_REQUEST_STATUS:
      sendNPKDataPacket();
      break;
    case COMMAND_TYPE_RESTART_DEVICE:
      // Restart the device
      void (*reset_func)(void) = 0;
      reset_func();
      break;
    default:
      break;
  }
  
  // Send ACK for command packet
  uint8_t ack_payload[2];
  ack_payload[0] = (packet.sequence_number >> 8) & 0xFF;
  ack_payload[1] = packet.sequence_number & 0xFF;
  
  Packet ack_packet = packet_builder.build(
    PACKET_TYPE_ACK,
    NPK_NODE_DEVICE_ID,
    packet.source_device,
    sequence_number++,
    ack_payload,
    2
  );
  lora_manager.sendPacket(ack_packet);
}

void handleConfigPacket(Packet& packet) {
  // Handle configuration update here
  
  // Send ACK
  uint8_t ack_payload[2];
  ack_payload[0] = (packet.sequence_number >> 8) & 0xFF;
  ack_payload[1] = packet.sequence_number & 0xFF;
  
  Packet ack_packet = packet_builder.build(
    PACKET_TYPE_ACK,
    NPK_NODE_DEVICE_ID,
    packet.source_device,
    sequence_number++,
    ack_payload,
    2
  );
  lora_manager.sendPacket(ack_packet);
}

void handlePingPacket(Packet& packet) {
  // Send PONG
  Packet pong_packet = packet_builder.build(
    PACKET_TYPE_PONG,
    NPK_NODE_DEVICE_ID,
    packet.source_device,
    sequence_number++
  );
  lora_manager.sendPacket(pong_packet);
}
