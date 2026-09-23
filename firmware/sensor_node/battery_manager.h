#ifndef BATTERY_MANAGER_H
#define BATTERY_MANAGER_H

#include <Arduino.h>
#include "config.h"

class BatteryManager {
public:
  BatteryManager();
  
  float readVoltage();
};

#endif
