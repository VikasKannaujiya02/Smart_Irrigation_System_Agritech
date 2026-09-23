#include "packet_builder.h"

PacketBuilder::PacketBuilder() {
}

Packet PacketBuilder::build(uint8_t packet_type, uint16_t source_device, uint16_t destination_device,
                            uint16_t sequence_number, const uint8_t* payload, uint16_t payload_length,
                            uint32_t timestamp) {
  Packet packet;
  packet.packet_version = PROTOCOL_VERSION;
  packet.packet_type = packet_type;
  packet.source_device = source_device;
  packet.destination_device = destination_device;
  packet.timestamp = timestamp == 0 ? (uint32_t)millis() / 1000 : timestamp;
  packet.sequence_number = sequence_number;
  packet.payload_length = payload_length > MAX_PAYLOAD_BYTES ? MAX_PAYLOAD_BYTES : payload_length;
  
  if (payload != nullptr && packet.payload_length > 0) {
    memcpy(packet.payload, payload, packet.payload_length);
  }
  
  uint8_t header_buffer[HEADER_WITHOUT_CRC_BYTES];
  uint16_t header_length = 0;
  pack_header(packet, header_buffer, &header_length);
  
  uint8_t crc_data[HEADER_WITHOUT_CRC_BYTES + MAX_PAYLOAD_BYTES];
  memcpy(crc_data, header_buffer, header_length);
  if (packet.payload_length > 0) {
    memcpy(crc_data + header_length, packet.payload, packet.payload_length);
  }
  
  packet.crc = calculate_crc16(crc_data, header_length + packet.payload_length);
  
  return packet;
}

void PacketBuilder::to_bytes(const Packet& packet, uint8_t* buffer, uint16_t* buffer_length) {
  uint16_t header_length = 0;
  pack_header(packet, buffer, &header_length);
  memcpy(buffer + header_length, packet.payload, packet.payload_length);
  buffer[header_length + packet.payload_length] = (packet.crc >> 8) & 0xFF;
  buffer[header_length + packet.payload_length + 1] = packet.crc & 0xFF;
  *buffer_length = header_length + packet.payload_length + CRC_BYTES;
}

bool PacketBuilder::parse(const uint8_t* raw_packet, uint16_t raw_length, Packet& packet) {
  if (raw_length < HEADER_WITHOUT_CRC_BYTES + CRC_BYTES) {
    return false;
  }
  
  packet.packet_version = raw_packet[0];
  packet.packet_type = raw_packet[1];
  packet.source_device = (raw_packet[2] << 8) | raw_packet[3];
  packet.destination_device = (raw_packet[4] << 8) | raw_packet[5];
  packet.timestamp = (raw_packet[6] << 24) | (raw_packet[7] << 16) | (raw_packet[8] << 8) | raw_packet[9];
  packet.sequence_number = (raw_packet[10] << 8) | raw_packet[11];
  packet.payload_length = (raw_packet[12] << 8) | raw_packet[13];
  
  uint16_t expected_length = HEADER_WITHOUT_CRC_BYTES + packet.payload_length + CRC_BYTES;
  if (raw_length != expected_length) {
    return false;
  }
  
  if (packet.payload_length > 0 && packet.payload_length <= MAX_PAYLOAD_BYTES) {
    memcpy(packet.payload, raw_packet + HEADER_WITHOUT_CRC_BYTES, packet.payload_length);
  }
  
  packet.crc = (raw_packet[HEADER_WITHOUT_CRC_BYTES + packet.payload_length] << 8) | 
               raw_packet[HEADER_WITHOUT_CRC_BYTES + packet.payload_length + 1];
  
  uint8_t crc_data[HEADER_WITHOUT_CRC_BYTES + MAX_PAYLOAD_BYTES];
  memcpy(crc_data, raw_packet, HEADER_WITHOUT_CRC_BYTES);
  if (packet.payload_length > 0) {
    memcpy(crc_data + HEADER_WITHOUT_CRC_BYTES, packet.payload, packet.payload_length);
  }
  uint16_t calculated_crc = calculate_crc16(crc_data, HEADER_WITHOUT_CRC_BYTES + packet.payload_length);
  
  return calculated_crc == packet.crc;
}

uint16_t PacketBuilder::calculate_crc16(const uint8_t* data, uint16_t length) {
  uint16_t crc = 0xFFFF;
  for (uint16_t i = 0; i < length; i++) {
    crc ^= (uint16_t)data[i] << 8;
    for (uint8_t j = 0; j < 8; j++) {
      if (crc & 0x8000) {
        crc = ((crc << 1) ^ 0x1021) & 0xFFFF;
      } else {
        crc = (crc << 1) & 0xFFFF;
      }
    }
  }
  return crc;
}

void PacketBuilder::pack_header(const Packet& packet, uint8_t* buffer, uint16_t* length) {
  buffer[0] = packet.packet_version;
  buffer[1] = packet.packet_type;
  buffer[2] = (packet.source_device >> 8) & 0xFF;
  buffer[3] = packet.source_device & 0xFF;
  buffer[4] = (packet.destination_device >> 8) & 0xFF;
  buffer[5] = packet.destination_device & 0xFF;
  buffer[6] = (packet.timestamp >> 24) & 0xFF;
  buffer[7] = (packet.timestamp >> 16) & 0xFF;
  buffer[8] = (packet.timestamp >> 8) & 0xFF;
  buffer[9] = packet.timestamp & 0xFF;
  buffer[10] = (packet.sequence_number >> 8) & 0xFF;
  buffer[11] = packet.sequence_number & 0xFF;
  buffer[12] = (packet.payload_length >> 8) & 0xFF;
  buffer[13] = packet.payload_length & 0xFF;
  *length = HEADER_WITHOUT_CRC_BYTES;
}
