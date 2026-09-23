#include "battery_manager.h"

BatteryManager::BatteryManager() {
  pinMode(BATTERY_PIN, INPUT);
}

float BatteryManager::readVoltage() {
  uint16_t raw_value = analogRead(BATTERY_PIN);
  float voltage = (raw_value / 1023.0f) * 5.0f * 2.0f;
  return voltage;
}
