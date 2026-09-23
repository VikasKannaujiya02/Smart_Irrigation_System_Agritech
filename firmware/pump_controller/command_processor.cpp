#include "command_processor.h"

CommandProcessor::CommandProcessor(RelayManager* relayMgr, Failsafe* failsafeMgr) {
  relay = relayMgr;
  failsafe = failsafeMgr;
}

void CommandProcessor::processCommand(const Packet& packet, PacketBuilder& packetBuilder, LoRaManager& loraMgr, uint16_t& sequenceNumber) {
  if (packet.packet_type != PACKET_TYPE_COMMAND) {
    return;
  }

  if (packet.payload_length == 0) {
    return;
  }

  uint8_t commandType = packet.payload[0];
  Serial.print("COMMAND received type=");
  Serial.println(commandType);
  
  switch (commandType) {
    case COMMAND_TYPE_MOTOR_ON:
      if (!failsafe->isInEmergency()) {
        bool relayChanged = relay->turnOn();
        Serial.print("MOTOR_ON relay_result=");
        Serial.println(relayChanged ? "OK" : "BLOCKED");
      } else {
        Serial.println("MOTOR_ON blocked: failsafe emergency active");
      }
      sendAck(packet, packetBuilder, loraMgr, sequenceNumber);
      sendStatus(packetBuilder, loraMgr, sequenceNumber);
      break;
      
    case COMMAND_TYPE_MOTOR_OFF:
      {
        bool relayChanged = relay->turnOff();
        Serial.print("MOTOR_OFF relay_result=");
        Serial.println(relayChanged ? "OK" : "FAILED");
      }
      // Turning the motor off is always safe; use it as the recovery path
      // out of a latched emergency stop (mirrors legacy FAILSAFE_OFF).
      if (failsafe->isInEmergency()) {
        failsafe->clearEmergencyStop();
        Serial.println("Emergency stop cleared by MOTOR_OFF");
      }
      sendAck(packet, packetBuilder, loraMgr, sequenceNumber);
      sendStatus(packetBuilder, loraMgr, sequenceNumber);
      break;
      
    case COMMAND_TYPE_REQUEST_STATUS:
      sendAck(packet, packetBuilder, loraMgr, sequenceNumber);
      sendStatus(packetBuilder, loraMgr, sequenceNumber);
      break;
      
    case COMMAND_TYPE_SYNC_TIME:
      // For now, just send ACK - time sync can be implemented later
      sendAck(packet, packetBuilder, loraMgr, sequenceNumber);
      break;
      
    case COMMAND_TYPE_RESTART_DEVICE:
      sendAck(packet, packetBuilder, loraMgr, sequenceNumber);
      delay(1000);
      ESP.restart();
      break;
      
    case COMMAND_TYPE_UPDATE_CONFIG:
      // Handle config update here
      sendAck(packet, packetBuilder, loraMgr, sequenceNumber);
      break;
      
    case COMMAND_TYPE_EMERGENCY_STOP:
      failsafe->triggerEmergencyStop();
      Serial.println("EMERGENCY_STOP activated");
      sendAck(packet, packetBuilder, loraMgr, sequenceNumber);
      sendStatus(packetBuilder, loraMgr, sequenceNumber);
      break;
      
    default:
      Serial.println("Unknown command type ignored");
      break;
  }
}

void CommandProcessor::sendAck(const Packet& originalPacket, PacketBuilder& packetBuilder, LoRaManager& loraMgr, uint16_t& sequenceNumber) {
  uint8_t ackPayload[2];
  ackPayload[0] = (originalPacket.sequence_number >> 8) & 0xFF;
  ackPayload[1] = originalPacket.sequence_number & 0xFF;
  
  Packet ackPacket = packetBuilder.build(
    PACKET_TYPE_ACK,
    PUMP_CONTROLLER_DEVICE_ID,
    originalPacket.source_device,
    sequenceNumber++,
    ackPayload,
    2
  );
  
  loraMgr.sendPacket(ackPacket);
}

void CommandProcessor::sendStatus(PacketBuilder& packetBuilder, LoRaManager& loraMgr, uint16_t& sequenceNumber) {
  RelayStatus status = relay->getStatus();
  
  uint8_t payload[20];
  uint16_t index = 0;
  
  payload[index++] = status.relayState ? 1 : 0;
  payload[index++] = status.feedbackState ? 1 : 0;
  payload[index++] = status.manualOverrideActive ? 1 : 0;
  payload[index++] = status.emergencyStopActive ? 1 : 0;
  payload[index++] = status.diagnosticsOk ? 1 : 0;
  
  // runtimeMs (4 bytes)
  payload[index++] = (status.runtimeMs >> 24) & 0xFF;
  payload[index++] = (status.runtimeMs >> 16) & 0xFF;
  payload[index++] = (status.runtimeMs >> 8) & 0xFF;
  payload[index++] = status.runtimeMs & 0xFF;
  
  // totalRuntimeMs (4 bytes)
  payload[index++] = (status.totalRuntimeMs >> 24) & 0xFF;
  payload[index++] = (status.totalRuntimeMs >> 16) & 0xFF;
  payload[index++] = (status.totalRuntimeMs >> 8) & 0xFF;
  payload[index++] = status.totalRuntimeMs & 0xFF;
  
  Packet statusPacket = packetBuilder.build(
    PACKET_TYPE_PUMP_STATUS,
    PUMP_CONTROLLER_DEVICE_ID,
    GATEWAY_DEVICE_ID,
    sequenceNumber++,
    payload,
    index
  );
  
  loraMgr.sendPacket(statusPacket);
}
