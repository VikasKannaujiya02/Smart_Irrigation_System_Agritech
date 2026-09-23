#ifndef POWER_MANAGER_H
#define POWER_MANAGER_H

#include <Arduino.h>
#include <avr/sleep.h>
#include <avr/wdt.h>
#include "config.h"

class PowerManager {
public:
  PowerManager();
  
  void begin();
  void sleep(uint32_t milliseconds);
  void enableWatchdog();
  void resetWatchdog();
};

#endif
