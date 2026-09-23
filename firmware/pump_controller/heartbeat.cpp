#include "heartbeat.h"

Heartbeat::Heartbeat() {
  last_heartbeat_ms = 0;
  heartbeat_interval_ms = DEFAULT_HEARTBEAT_INTERVAL_MS;
}

void Heartbeat::begin(uint32_t interval_ms) {
  heartbeat_interval_ms = interval_ms;
  last_heartbeat_ms = millis();
}

bool Heartbeat::shouldSend() {
  return millis() - last_heartbeat_ms >= heartbeat_interval_ms;
}

void Heartbeat::reset() {
  last_heartbeat_ms = millis();
}
