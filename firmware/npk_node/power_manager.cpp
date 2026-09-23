#include "power_manager.h"

PowerManager::PowerManager() {
}

void PowerManager::begin() {
  enableWatchdog();
}

void PowerManager::sleep(uint32_t milliseconds) {
  set_sleep_mode(SLEEP_MODE_PWR_DOWN);
  sleep_enable();
  wdt_reset();
  sleep_cpu();
  sleep_disable();
}

void PowerManager::enableWatchdog() {
  cli();
  wdt_reset();
  MCUSR &= ~(1 << WDRF);
  // IMPORTANT: WDTO_4S (WATCHDOG_TIMEOUT) is just a plain index (0-9),
  // NOT a ready-made register bit pattern. Writing it directly into
  // WDTCSR (as the old code did) scrambles the WDP3:0 prescaler bits
  // and was actually configuring a ~16ms timeout instead of 4 seconds --
  // that's why the board reset almost instantly, mid-print, every time.
  // wdt_enable() from <avr/wdt.h> handles the WDP3 bit-splitting correctly.
  wdt_enable(WATCHDOG_TIMEOUT);
  WDTCSR |= (1 << WDE); // ensure reset mode (not interrupt-only) is set
  sei();
}

void PowerManager::disableWatchdog() {
  cli();
  wdt_reset();
  MCUSR &= ~(1 << WDRF);
  WDTCSR |= (1 << WDCE) | (1 << WDE);
  WDTCSR = 0x00;
  sei();
}

void PowerManager::resetWatchdog() {
  wdt_reset();
}
