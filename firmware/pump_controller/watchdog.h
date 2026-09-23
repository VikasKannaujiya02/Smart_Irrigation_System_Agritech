#ifndef WATCHDOG_H
#define WATCHDOG_H

#include <Arduino.h>
#include <Ticker.h>
#include "config.h"

class Watchdog {
public:
  Watchdog();
  
  void begin();
  void feed();
  
private:
  Ticker ticker;
  static void resetFunc();
};

#endif
