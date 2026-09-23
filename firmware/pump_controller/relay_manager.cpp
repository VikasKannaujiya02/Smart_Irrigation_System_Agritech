#include "relay_manager.h"

RelayManager::RelayManager() {
  status.relayState = false;
  status.feedbackState = false;
  status.manualOverrideActive = false;
  status.emergencyStopActive = false;
  status.diagnosticsOk = true;
  status.runtimeMs = 0;
  status.lastOnTimeMs = 0;
  status.totalRuntimeMs = 0;
  lastFeedbackCheckMs = 0;
  lastFeedbackState = false;
}

bool RelayManager::begin() {
  pinMode(RELAY_PIN, OUTPUT);
  if (MANUAL_SWITCH_PIN >= 0) {
    pinMode(MANUAL_SWITCH_PIN, INPUT_PULLUP);
  }
  if (PUMP_FEEDBACK_PIN >= 0) {
    pinMode(PUMP_FEEDBACK_PIN, INPUT_PULLUP);
  }
  if (EMERGENCY_STOP_PIN >= 0) {
    pinMode(EMERGENCY_STOP_PIN, INPUT_PULLUP);
  }
  digitalWrite(RELAY_PIN, RELAY_INACTIVE_LEVEL);
  return true;
}

bool RelayManager::turnOn() {
  if (status.emergencyStopActive) {
    return false;
  }
  
  digitalWrite(RELAY_PIN, RELAY_ACTIVE_LEVEL);
  status.relayState = true;
  status.lastOnTimeMs = millis();
  return true;
}

bool RelayManager::turnOff() {
  digitalWrite(RELAY_PIN, RELAY_INACTIVE_LEVEL);
  status.relayState = false;
  if (status.lastOnTimeMs > 0) {
    status.totalRuntimeMs += millis() - status.lastOnTimeMs;
    status.lastOnTimeMs = 0;
  }
  return true;
}

bool RelayManager::emergencyStop() {
  turnOff();
  status.emergencyStopActive = true;
  return true;
}

void RelayManager::clearEmergencyStop() {
  status.emergencyStopActive = false;
}

void RelayManager::update() {
  // Check manual switch
  if (MANUAL_SWITCH_PIN >= 0) {
    bool manualSwitchState = !digitalRead(MANUAL_SWITCH_PIN); // INPUT_PULLUP, LOW means active
    if (manualSwitchState && !status.manualOverrideActive) {
      status.manualOverrideActive = true;
      if (status.relayState) {
        turnOff();
      } else {
        turnOn();
      }
    } else if (!manualSwitchState && status.manualOverrideActive) {
      status.manualOverrideActive = false;
    }
  }
  
  // Check emergency stop
  if (EMERGENCY_STOP_PIN >= 0) {
    bool emergencyStopState = !digitalRead(EMERGENCY_STOP_PIN); // INPUT_PULLUP, LOW means active
    if (emergencyStopState && !status.emergencyStopActive) {
      emergencyStop();
    }
  }
  
  // Check feedback
  if (millis() - lastFeedbackCheckMs >= PUMP_FEEDBACK_DEBOUNCE_MS) {
    lastFeedbackCheckMs = millis();
    bool currentFeedback = status.relayState;
    if (PUMP_FEEDBACK_PIN >= 0) {
      currentFeedback = !digitalRead(PUMP_FEEDBACK_PIN); // INPUT_PULLUP, LOW means pump is running
    }
    status.feedbackState = currentFeedback;
    
    // Check feedback consistency
    if (status.relayState && !status.feedbackState) {
      // Relay is on but no feedback - possible dry run
      status.diagnosticsOk = false;
    } else if (!status.relayState && status.feedbackState) {
      // Relay is off but feedback says on - possible stuck relay
      status.diagnosticsOk = false;
    } else {
      status.diagnosticsOk = true;
    }
  }
  
  // Update runtime
  if (status.relayState && status.lastOnTimeMs > 0) {
    status.runtimeMs = millis() - status.lastOnTimeMs;
  } else {
    status.runtimeMs = 0;
  }
}

RelayStatus RelayManager::getStatus() {
  return status;
}
