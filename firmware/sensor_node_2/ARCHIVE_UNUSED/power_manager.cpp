#include "power_manager.h"

// Watchdog interrupt fires on timeout when only WDIE (not WDE) is set,
// waking the CPU from power-down sleep without resetting the device.
ISR(WDT_vect) {
  // Intentionally empty: firing the ISR is enough to wake sleep_cpu().
}

// Actual period of one WATCHDOG_TIMEOUT cycle (config.h uses WDTO_4S).
static const uint32_t WATCHDOG_PERIOD_MS = 4000UL;

PowerManager::PowerManager() {
}

void PowerManager::begin() {
  enableWatchdog();
}

void PowerManager::sleep(uint32_t milliseconds) {
  uint32_t slept_ms = 0;
  while (slept_ms < milliseconds) {
    set_sleep_mode(SLEEP_MODE_PWR_DOWN);
    sleep_enable();
    wdt_reset();
    sleep_cpu();
    sleep_disable();
    slept_ms += WATCHDOG_PERIOD_MS;
  }
}

void PowerManager::enableWatchdog() {
  cli();
  wdt_reset();
  MCUSR &= ~(1 << WDRF);
  WDTCSR |= (1 << WDCE) | (1 << WDE);
  WDTCSR = WATCHDOG_TIMEOUT | (1 << WDIE);
  sei();
}

void PowerManager::resetWatchdog() {
  wdt_reset();
}
