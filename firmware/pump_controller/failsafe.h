#ifndef FAILSAFE_H
#define FAILSAFE_H

#include <Arduino.h>
#include "config.h"
#include "relay_manager.h"

class Failsafe {
public:
  Failsafe(RelayManager* relayMgr);
  
  void begin();
  void update();
  void checkRuntimeProtection();
  void checkDryRunProtection();
  void triggerEmergencyStop();
  bool isInEmergency();
  void clearEmergencyStop();
  
private:
  RelayManager* relay;
  uint32_t lastDryRunCheckMs;
  bool emergencyStopActive;
};

#endif
