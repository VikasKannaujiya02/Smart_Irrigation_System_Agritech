#include "failsafe.h"

Failsafe::Failsafe(RelayManager* relayMgr) {
  relay = relayMgr;
  lastDryRunCheckMs = 0;
  emergencyStopActive = false;
}

void Failsafe::begin() {
  // Nothing to initialize here
}

void Failsafe::update() {
  checkRuntimeProtection();
  checkDryRunProtection();
}

void Failsafe::checkRuntimeProtection() {
  RelayStatus status = relay->getStatus();
  if (status.relayState && status.runtimeMs >= MAX_PUMP_RUNTIME_MS) {
    triggerEmergencyStop();
  }
}

void Failsafe::checkDryRunProtection() {
  if (millis() - lastDryRunCheckMs >= DRY_RUN_CHECK_INTERVAL_MS) {
    lastDryRunCheckMs = millis();
    RelayStatus status = relay->getStatus();
    if (status.relayState && !status.feedbackState) {
      // No feedback from pump - possible dry run
      triggerEmergencyStop();
    }
  }
}

void Failsafe::triggerEmergencyStop() {
  emergencyStopActive = true;
  relay->emergencyStop();
}

bool Failsafe::isInEmergency() {
  return emergencyStopActive;
}

void Failsafe::clearEmergencyStop() {
  emergencyStopActive = false;
  relay->clearEmergencyStop();
}
