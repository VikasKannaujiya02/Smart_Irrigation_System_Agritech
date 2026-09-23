#ifndef NPK_SENSOR_H
#define NPK_SENSOR_H

#include <Arduino.h>
#include "config.h"
#include "modbus_manager.h"

typedef struct {
  uint16_t nitrogen;     // mg/kg
  uint16_t phosphorus;   // mg/kg
  uint16_t potassium;    // mg/kg
  float ec;              // mS/cm
  float ph;              // pH
  float soilTemp;        // °C
  uint16_t soilMoisture; // %
  bool valid;
} NPKData;

class NpkSensor {
public:
  NpkSensor(ModbusManager* modbusMgr);
  
  bool begin();
  NPKData readAll();
  bool readNitrogen(uint16_t& value);
  bool readPhosphorus(uint16_t& value);
  bool readPotassium(uint16_t& value);
  bool readEC(float& value);
  bool readPH(float& value);
  bool readSoilTemp(float& value);
  bool readSoilMoisture(uint16_t& value);
  
private:
  ModbusManager* modbus;
};

#endif
