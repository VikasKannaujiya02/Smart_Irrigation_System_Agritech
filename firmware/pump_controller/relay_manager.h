#ifndef RELAY_MANAGER_H
#define RELAY_MANAGER_H

#include <Arduino.h>
#include "config.h"

typedef struct {
  bool relayState;
  bool feedbackState;
  bool manualOverrideActive;
  bool emergencyStopActive;
  bool diagnosticsOk;
  uint32_t runtimeMs;
  uint32_t lastOnTimeMs;
  uint32_t totalRuntimeMs;
} RelayStatus;

class RelayManager {
public:
  RelayManager();
  
  bool begin();
  bool turnOn();
  bool turnOff();
  bool emergencyStop();
  void clearEmergencyStop();
  void update();
  RelayStatus getStatus();
  
private:
  RelayStatus status;
  uint32_t lastFeedbackCheckMs;
  bool lastFeedbackState;
};

#endif
