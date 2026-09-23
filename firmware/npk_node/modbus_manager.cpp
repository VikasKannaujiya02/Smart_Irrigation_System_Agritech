#include "modbus_manager.h"

ModbusManager::ModbusManager() {
  modbusSerial = new SoftwareSerial(6, 7); // RX=6, TX=7
}

bool ModbusManager::begin() {
  pinMode(RS485_DE, OUTPUT);
  pinMode(RS485_RE, OUTPUT);
  setReceiveMode();
  modbusSerial->begin(MODBUS_BAUD_RATE);
  return true;
}

void ModbusManager::setTransmitMode() {
  digitalWrite(RS485_DE, HIGH);
  digitalWrite(RS485_RE, HIGH);
  delayMicroseconds(10);
}

void ModbusManager::setReceiveMode() {
  delayMicroseconds(10);
  digitalWrite(RS485_DE, LOW);
  digitalWrite(RS485_RE, LOW);
}

uint16_t ModbusManager::calculateCRC(const uint8_t* data, uint16_t length) {
  uint16_t crc = 0xFFFF;
  for (uint16_t i = 0; i < length; i++) {
    crc ^= data[i];
    for (uint8_t j = 0; j < 8; j++) {
      if (crc & 0x0001) {
        crc = (crc >> 1) ^ 0xA001;
      } else {
        crc >>= 1;
      }
    }
  }
  return crc;
}

bool ModbusManager::readHoldingRegisters(uint8_t slaveAddr, uint16_t startAddr, uint16_t numRegs, uint16_t* regs) {
  uint8_t request[8];
  request[0] = slaveAddr;
  request[1] = 0x03; // Function code 03: Read Holding Registers
  request[2] = (startAddr >> 8) & 0xFF;
  request[3] = startAddr & 0xFF;
  request[4] = (numRegs >> 8) & 0xFF;
  request[5] = numRegs & 0xFF;
  uint16_t crc = calculateCRC(request, 6);
  request[6] = crc & 0xFF;
  request[7] = (crc >> 8) & 0xFF;

  // Flush any stale bytes sitting in the receive buffer from a previous
  // failed/partial exchange, so they don't get misread as part of this
  // response.
  while (modbusSerial->available()) modbusSerial->read();

  setTransmitMode();
  modbusSerial->write(request, 8);
  modbusSerial->flush();
  setReceiveMode();

  uint32_t startTime = millis();
  while (modbusSerial->available() < 5 + 2 * numRegs) {
    if (millis() - startTime > MODBUS_TIMEOUT_MS) {
      Serial.print(F("[Modbus] TIMEOUT waiting for reg 0x"));
      Serial.print(startAddr, HEX);
      Serial.print(F(" -- got "));
      Serial.print(modbusSerial->available());
      Serial.print(F(" bytes, needed "));
      Serial.println(5 + 2 * numRegs);
      return false;
    }
  }

  uint8_t response[256];
  uint16_t index = 0;
  while (modbusSerial->available() && index < 256) {
    response[index++] = modbusSerial->read();
  }

  if (index < 5 + 2 * numRegs) {
    Serial.print(F("[Modbus] SHORT response for reg 0x"));
    Serial.print(startAddr, HEX);
    Serial.print(F(" -- got "));
    Serial.print(index);
    Serial.print(F(" bytes, needed "));
    Serial.println(5 + 2 * numRegs);
    return false;
  }

  uint16_t receivedCRC = (response[index-1] << 8) | response[index-2];
  uint16_t calculatedCRC = calculateCRC(response, index - 2);
  if (receivedCRC != calculatedCRC) {
    Serial.print(F("[Modbus] CRC MISMATCH for reg 0x"));
    Serial.print(startAddr, HEX);
    Serial.print(F(" -- got 0x"));
    Serial.print(receivedCRC, HEX);
    Serial.print(F(", expected 0x"));
    Serial.print(calculatedCRC, HEX);
    Serial.print(F(" -- raw bytes: "));
    for (uint16_t i = 0; i < index; i++) {
      if (response[i] < 0x10) Serial.print('0');
      Serial.print(response[i], HEX);
      Serial.print(' ');
    }
    Serial.println();
    return false;
  }

  for (uint16_t i = 0; i < numRegs; i++) {
    regs[i] = (response[3 + 2*i] << 8) | response[4 + 2*i];
  }

  return true;
}

bool ModbusManager::writeSingleRegister(uint8_t slaveAddr, uint16_t regAddr, uint16_t value) {
  uint8_t request[8];
  request[0] = slaveAddr;
  request[1] = 0x06; // Function code 06: Write Single Register
  request[2] = (regAddr >> 8) & 0xFF;
  request[3] = regAddr & 0xFF;
  request[4] = (value >> 8) & 0xFF;
  request[5] = value & 0xFF;
  uint16_t crc = calculateCRC(request, 6);
  request[6] = crc & 0xFF;
  request[7] = (crc >> 8) & 0xFF;

  setTransmitMode();
  modbusSerial->write(request, 8);
  modbusSerial->flush();
  setReceiveMode();

  uint32_t startTime = millis();
  while (modbusSerial->available() < 8) {
    if (millis() - startTime > MODBUS_TIMEOUT_MS) {
      return false;
    }
  }

  uint8_t response[8];
  uint16_t index = 0;
  while (modbusSerial->available() && index < 8) {
    response[index++] = modbusSerial->read();
  }

  if (index < 8) {
    return false;
  }

  uint16_t receivedCRC = (response[7] << 8) | response[6];
  uint16_t calculatedCRC = calculateCRC(response, 6);
  if (receivedCRC != calculatedCRC) {
    return false;
  }

  return true;
}
