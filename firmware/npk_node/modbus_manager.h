#ifndef MODBUS_MANAGER_H
#define MODBUS_MANAGER_H

#include <Arduino.h>
#include <SoftwareSerial.h>
#include "config.h"

class ModbusManager {
public:
  ModbusManager();
  
  bool begin();
  bool readHoldingRegisters(uint8_t slaveAddr, uint16_t startAddr, uint16_t numRegs, uint16_t* regs);
  bool writeSingleRegister(uint8_t slaveAddr, uint16_t regAddr, uint16_t value);
  
private:
  SoftwareSerial* modbusSerial;
  uint16_t calculateCRC(const uint8_t* data, uint16_t length);
  void setTransmitMode();
  void setReceiveMode();
};

#endif
