#ifndef PACKET_BUILDER_H
#define PACKET_BUILDER_H

#include <Arduino.h>
#include "config.h"

typedef struct {
  uint8_t packet_version;
  uint8_t packet_type;
  uint16_t source_device;
  uint16_t destination_device;
  uint32_t timestamp;
  uint16_t sequence_number;
  uint16_t payload_length;
  uint8_t payload[MAX_PAYLOAD_BYTES];
  uint16_t crc;
} Packet;

class PacketBuilder {
public:
  PacketBuilder();
  
  Packet build(uint8_t packet_type, uint16_t source_device, uint16_t destination_device, 
               uint16_t sequence_number, const uint8_t* payload = nullptr, uint16_t payload_length = 0, 
               uint32_t timestamp = 0);
  
  void to_bytes(const Packet& packet, uint8_t* buffer, uint16_t* buffer_length);
  
  bool parse(const uint8_t* raw_packet, uint16_t raw_length, Packet& packet);
  
  uint16_t calculate_crc16(const uint8_t* data, uint16_t length);
  
private:
  void pack_header(const Packet& packet, uint8_t* buffer, uint16_t* length);
};

#endif
