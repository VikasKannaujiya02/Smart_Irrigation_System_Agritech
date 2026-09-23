#ifndef HEARTBEAT_H
#define HEARTBEAT_H

#include <Arduino.h>
#include "config.h"

class Heartbeat {
public:
  Heartbeat();
  
  void begin(uint32_t interval_ms = DEFAULT_HEARTBEAT_INTERVAL_MS);
  bool shouldSend();
  void reset();
  
private:
  uint32_t last_heartbeat_ms;
  uint32_t heartbeat_interval_ms;
};

#endif
