#include "watchdog.h"

Watchdog::Watchdog() {
  // Constructor
}

void Watchdog::begin() {
  ticker.attach_ms(WATCHDOG_TIMEOUT_MS, resetFunc);
}

void Watchdog::feed() {
  ticker.detach();
  ticker.attach_ms(WATCHDOG_TIMEOUT_MS, resetFunc);
}

void Watchdog::resetFunc() {
  ESP.restart();
}
