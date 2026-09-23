#ifndef COMMAND_PROCESSOR_H
#define COMMAND_PROCESSOR_H

#include <Arduino.h>
#include "config.h"
#include "packet_builder.h"
#include "relay_manager.h"
#include "failsafe.h"
#include "lora_manager.h"
class CommandProcessor {
public:
  CommandProcessor(RelayManager* relayMgr, Failsafe* failsafeMgr);
  
  void processCommand(const Packet& packet, PacketBuilder& packetBuilder, LoRaManager& loraMgr, uint16_t& sequenceNumber);
  void sendAck(const Packet& originalPacket, PacketBuilder& packetBuilder, LoRaManager& loraMgr, uint16_t& sequenceNumber);
  void sendStatus(PacketBuilder& packetBuilder, LoRaManager& loraMgr, uint16_t& sequenceNumber);

private:
  RelayManager* relay;
  Failsafe* failsafe;
};

#endif
