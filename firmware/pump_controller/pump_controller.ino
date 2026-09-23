#include "config.h"
#include "packet_builder.h"
#include "lora_manager.h"
#include "relay_manager.h"
#include "failsafe.h"
#include "watchdog.h"
#include "heartbeat.h"
#include "command_processor.h"

// Initialize managers
PacketBuilder packet_builder;
LoRaManager lora_manager;
RelayManager relay_manager;
Failsafe failsafe(&relay_manager);
Watchdog watchdog;
Heartbeat heartbeat;
CommandProcessor command_processor(&relay_manager, &failsafe);

// State variables
uint16_t sequence_number = 0;
uint32_t last_status_send_ms = 0;
const uint32_t STATUS_SEND_INTERVAL_MS = 30000UL; // Send status every 30 seconds

// Non-blocking LED pulse state (avoids delay() stalling LoRa RX / watchdog feed)
bool led_active = false;
uint32_t led_on_ms = 0;
const uint32_t LED_PULSE_MS = 50;

void pulseLed() {
  digitalWrite(STATUS_LED_PIN, HIGH);
  led_active = true;
  led_on_ms = millis();
}

void serviceLed() {
  if (led_active && millis() - led_on_ms >= LED_PULSE_MS) {
    digitalWrite(STATUS_LED_PIN, LOW);
    led_active = false;
  }
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println();
  Serial.println("=== Pump Controller Boot ===");

  pinMode(STATUS_LED_PIN, OUTPUT);
  
  // Initialize managers
  relay_manager.begin();
  failsafe.begin();
  watchdog.begin();
  heartbeat.begin();
  Serial.println("Managers initialized");
  
  // Initialize LoRa
  if (lora_manager.begin()) {
    pulseLed();
    Serial.println("LoRa init: OK");
  } else {
    Serial.println("LoRa init: FAILED");
  }
  
  // Send HELLO packet on startup
  Packet helloPacket = packet_builder.build(
    PACKET_TYPE_HELLO,
    PUMP_CONTROLLER_DEVICE_ID,
    GATEWAY_DEVICE_ID,
    sequence_number++
  );
  lora_manager.sendPacket(helloPacket);
  Serial.println("HELLO packet sent");
}

void loop() {
  watchdog.feed();
  relay_manager.update();
  failsafe.update();
  serviceLed();
  
  // Check for incoming packets
  Packet incomingPacket;
  if (lora_manager.receivePacket(incomingPacket)) {
    pulseLed();

    Serial.print("RX packet type=");
    Serial.print(incomingPacket.packet_type);
    Serial.print(" src=");
    Serial.print(incomingPacket.source_device);
    Serial.print(" dst=");
    Serial.print(incomingPacket.destination_device);
    Serial.print(" seq=");
    Serial.println(incomingPacket.sequence_number);
    
    if (incomingPacket.destination_device == PUMP_CONTROLLER_DEVICE_ID || 
        incomingPacket.destination_device == BROADCAST_DEVICE_ID) {
      
      if (incomingPacket.packet_type == PACKET_TYPE_COMMAND) {
        Serial.println("-> Handling COMMAND, sending ACK");
        command_processor.processCommand(incomingPacket, packet_builder, lora_manager, sequence_number);
        Serial.println("-> ACK sent");
      } else if (incomingPacket.packet_type == PACKET_TYPE_PING) {
        // Send PONG response
        Packet pongPacket = packet_builder.build(
          PACKET_TYPE_PONG,
          PUMP_CONTROLLER_DEVICE_ID,
          incomingPacket.source_device,
          sequence_number++
        );
        lora_manager.sendPacket(pongPacket);
        Serial.println("-> PONG sent");
      } else if (incomingPacket.packet_type == PACKET_TYPE_CONFIG) {
        // Config update handling; ACK reuses CommandProcessor's shared sender
        command_processor.sendAck(incomingPacket, packet_builder, lora_manager, sequence_number);
        Serial.println("-> CONFIG ACK sent");
      } else {
        Serial.println("-> Unhandled packet_type, ignored");
      }
    } else {
      Serial.println("-> Not addressed to us, ignored");
    }
  }
  
  // Send periodic status updates
  if (millis() - last_status_send_ms >= STATUS_SEND_INTERVAL_MS) {
    last_status_send_ms = millis();
    command_processor.sendStatus(packet_builder, lora_manager, sequence_number);
    Serial.println("STATUS packet sent");
  }
  
  // Send heartbeat
  if (heartbeat.shouldSend()) {
    Packet heartbeatPacket = packet_builder.build(
      PACKET_TYPE_HEARTBEAT,
      PUMP_CONTROLLER_DEVICE_ID,
      GATEWAY_DEVICE_ID,
      sequence_number++
    );
    lora_manager.sendPacket(heartbeatPacket);
    heartbeat.reset();
    Serial.println("HEARTBEAT sent");
  }
}
