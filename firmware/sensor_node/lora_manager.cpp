#include "lora_manager.h"

LoRaManager::LoRaManager() {
}

bool LoRaManager::begin() {
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  
  if (!LoRa.begin(LORA_FREQUENCY)) {
    return false;
  }
  
  LoRa.setSpreadingFactor(LORA_SPREADING_FACTOR);
  LoRa.setSignalBandwidth(LORA_SIGNAL_BANDWIDTH);
  LoRa.setCodingRate4(LORA_CODING_RATE);
  LoRa.setTxPower(LORA_POWER);
  LoRa.setSyncWord(LORA_SYNC_WORD);
  LoRa.enableCrc();
  
  return true;
}

void LoRaManager::sendPacket(const Packet& packet) {
  uint8_t buffer[MAX_PACKET_BYTES];
  uint16_t buffer_length = 0;
  packet_builder.to_bytes(packet, buffer, &buffer_length);
  
  LoRa.beginPacket();
  LoRa.write(buffer, buffer_length);
  LoRa.endPacket(true);
}

bool LoRaManager::receivePacket(Packet& packet) {
  int packet_size = LoRa.parsePacket();
  if (packet_size == 0) {
    return false;
  }
  
  uint8_t raw_packet[MAX_PACKET_BYTES];
  uint16_t index = 0;
  while (LoRa.available() && index < MAX_PACKET_BYTES) {
    raw_packet[index++] = LoRa.read();
  }
  
  return packet_builder.parse(raw_packet, index, packet);
}
