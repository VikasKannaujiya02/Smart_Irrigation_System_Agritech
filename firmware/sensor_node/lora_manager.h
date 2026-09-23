#ifndef LORA_MANAGER_H
#define LORA_MANAGER_H

#include <Arduino.h>
#include <LoRa.h>
#include "config.h"
#include "packet_builder.h"
#include <DHT.h>
class LoRaManager {
public:
  LoRaManager();
  
  bool begin();
  void sendPacket(const Packet& packet);
  bool receivePacket(Packet& packet);
  
private:
  PacketBuilder packet_builder;
};

#endif
