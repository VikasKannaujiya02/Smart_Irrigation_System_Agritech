#ifndef SENSOR_MANAGER_H
#define SENSOR_MANAGER_H

#include <Arduino.h>
#include <Wire.h>
#include "config.h"
#include "battery_manager.h"

typedef struct {
  float soil_moisture_percent;
  float temperature_c;
  float humidity_percent;
  float battery_voltage;
} SensorData;

class SensorManager {
public:
  SensorManager();
  
  bool begin();
  SensorData readAllSensors();
  float readSoilMoisture();
  float readTemperature();
  float readHumidity();
  float readBatteryVoltage();
  void calibrateSoilMoisture(uint16_t air_value, uint16_t water_value);
  
private:
  BatteryManager battery;
  uint16_t soil_moisture_air_value;
  uint16_t soil_moisture_water_value;
  bool aht10_available;
  float last_temperature_c;
  float last_humidity_percent;
  bool readAHT10(float& temperature_c, float& humidity_percent);
};

#endif
