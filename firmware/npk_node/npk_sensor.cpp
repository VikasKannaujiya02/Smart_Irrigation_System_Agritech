#include "npk_sensor.h"
#include <avr/wdt.h>

// ---- JXBS-3001-TR-RS register map (NOT contiguous!) ----
// Confirmed working against the real sensor via Serial Monitor testing.
#define REG_PH          0x0006   // 1 register,  value / 100.0  -> pH
#define REG_MOIST_TEMP  0x0012   // 2 registers, [0]=moisture /10.0 (%), [1]=temp /10.0 (C, signed)
#define REG_EC          0x0015   // 1 register,  raw value in us/cm
#define REG_NPK         0x001E   // 3 registers, N, P, K in mg/kg

NpkSensor::NpkSensor(ModbusManager* modbusMgr) {
  modbus = modbusMgr;
}

bool NpkSensor::begin() {
  return true;
}

NPKData NpkSensor::readAll() {
  NPKData data = {0};
  data.valid = true;

  uint16_t regs[3];

  // wdt_reset() is called between every step below. Even in the worst
  // case (every single read times out at MODBUS_TIMEOUT_MS), this
  // function can never silently eat the whole watchdog window on its
  // own -- a genuinely stuck sensor will still be caught by the
  // watchdog eventually (via loop()'s own resetWatchdog() call), but
  // won't reset mid-read here.
  wdt_reset();

  // ---- 1. Moisture + Temperature (2 registers at 0x0012) ----
  if (modbus->readHoldingRegisters(MODBUS_SLAVE_ADDRESS, REG_MOIST_TEMP, 2, regs)) {
    data.soilMoisture = regs[0] / 10;               // reported as %, kept as uint16 (whole %)
    int16_t rawTemp = (int16_t) regs[1];            // signed, can go negative
    data.soilTemp = rawTemp / 10.0f;
  } else {
    data.valid = false;
  }

  wdt_reset();
  delay(100); // small gap between requests, sensor needs it

  // ---- 2. EC (1 register at 0x0015) ----
  if (modbus->readHoldingRegisters(MODBUS_SLAVE_ADDRESS, REG_EC, 1, regs)) {
    data.ec = (float) regs[0];   // raw counts, matches confirmed-working sketch (no /1000 here)
  } else {
    data.valid = false;
  }

  wdt_reset();
  delay(100);

  // ---- 3. pH (1 register at 0x0006) ----
  if (modbus->readHoldingRegisters(MODBUS_SLAVE_ADDRESS, REG_PH, 1, regs)) {
    data.ph = regs[0] / 100.0f;   // pH is scaled by 100, not 10
  } else {
    data.valid = false;
  }

  wdt_reset();
  delay(100);

  // ---- 4. NPK (3 registers at 0x001E) ----
  if (modbus->readHoldingRegisters(MODBUS_SLAVE_ADDRESS, REG_NPK, 3, regs)) {
    data.nitrogen = regs[0];
    data.phosphorus = regs[1];
    data.potassium = regs[2];
  } else {
    data.valid = false;
  }

  wdt_reset();

  return data;
}

bool NpkSensor::readNitrogen(uint16_t& value) {
  uint16_t regs[3];
  if (!modbus->readHoldingRegisters(MODBUS_SLAVE_ADDRESS, REG_NPK, 3, regs)) {
    return false;
  }
  value = regs[0];
  return true;
}

bool NpkSensor::readPhosphorus(uint16_t& value) {
  uint16_t regs[3];
  if (!modbus->readHoldingRegisters(MODBUS_SLAVE_ADDRESS, REG_NPK, 3, regs)) {
    return false;
  }
  value = regs[1];
  return true;
}

bool NpkSensor::readPotassium(uint16_t& value) {
  uint16_t regs[3];
  if (!modbus->readHoldingRegisters(MODBUS_SLAVE_ADDRESS, REG_NPK, 3, regs)) {
    return false;
  }
  value = regs[2];
  return true;
}

bool NpkSensor::readEC(float& value) {
  uint16_t reg;
  if (!modbus->readHoldingRegisters(MODBUS_SLAVE_ADDRESS, REG_EC, 1, &reg)) {
    return false;
  }
  value = (float) reg;
  return true;
}

bool NpkSensor::readPH(float& value) {
  uint16_t reg;
  if (!modbus->readHoldingRegisters(MODBUS_SLAVE_ADDRESS, REG_PH, 1, &reg)) {
    return false;
  }
  value = reg / 100.0f;
  return true;
}

bool NpkSensor::readSoilTemp(float& value) {
  uint16_t regs[2];
  if (!modbus->readHoldingRegisters(MODBUS_SLAVE_ADDRESS, REG_MOIST_TEMP, 2, regs)) {
    return false;
  }
  int16_t rawTemp = (int16_t) regs[1];
  value = rawTemp / 10.0f;
  return true;
}

bool NpkSensor::readSoilMoisture(uint16_t& value) {
  uint16_t regs[2];
  if (!modbus->readHoldingRegisters(MODBUS_SLAVE_ADDRESS, REG_MOIST_TEMP, 2, regs)) {
    return false;
  }
  value = regs[0] / 10;
  return true;
}
