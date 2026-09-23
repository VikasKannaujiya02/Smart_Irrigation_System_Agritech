#include "sensor_manager.h"

SensorManager::SensorManager() {
  soil_moisture_air_value = SOIL_MOISTURE_AIR_VALUE;
  soil_moisture_water_value = SOIL_MOISTURE_WATER_VALUE;
  aht10_available = false;
  last_temperature_c = 0.0f;
  last_humidity_percent = 0.0f;
}

bool SensorManager::begin() {
  pinMode(SOIL_MOISTURE_PIN, INPUT);
  pinMode(BATTERY_PIN, INPUT);
  pinMode(SENSOR_PWM_OUT_PIN, OUTPUT);
  TCCR1A = bit(COM1A0);
  TCCR1B = bit(WGM12) | bit(CS10);
  OCR1A = 1;

  aht10_available = false;

  return true;
}

SensorData SensorManager::readAllSensors() {
  SensorData data;
  data.soil_moisture_percent = readSoilMoisture();
  data.temperature_c = last_temperature_c;
  data.humidity_percent = last_humidity_percent;
  data.battery_voltage  = readBatteryVoltage();
  return data;
}

float SensorManager::readSoilMoisture() {
  ADMUX = _BV(REFS0) | _BV(MUX1);
  ADCSRA = _BV(ADEN) | _BV(ADPS1) | _BV(ADPS0);
  delay(50);
  ADCSRA |= (1 << ADSC);
  while (ADCSRA & (1 << ADSC)) {
  }

  uint8_t adc_low = ADCL;
  uint8_t adc_high = ADCH;
  uint16_t raw_value = (adc_high << 8) | adc_low;
  raw_value = constrain(raw_value, soil_moisture_water_value, soil_moisture_air_value);
  float percent = map(raw_value, soil_moisture_air_value, soil_moisture_water_value, 0, 100);
  return constrain(percent, 0.0f, 100.0f);
}

float SensorManager::readTemperature() {
  readAHT10(last_temperature_c, last_humidity_percent);
  return last_temperature_c;
}

float SensorManager::readHumidity() {
  readAHT10(last_temperature_c, last_humidity_percent);
  return last_humidity_percent;
}

float SensorManager::readBatteryVoltage() {
  return battery.readVoltage();
}

void SensorManager::calibrateSoilMoisture(uint16_t air_value, uint16_t water_value) {
  soil_moisture_air_value  = air_value;
  soil_moisture_water_value = water_value;
}

bool SensorManager::readAHT10(float& temperature_c, float& humidity_percent) {
  if (!aht10_available) {
    return false;
  }

  Wire.beginTransmission(AHT10_ADDRESS);
  Wire.write(0xAC);
  Wire.write(0x33);
  Wire.write(0x00);
  if (Wire.endTransmission() != 0) {
    return false;
  }

  delay(80);
  uint8_t bytes_read = Wire.requestFrom(AHT10_ADDRESS, 6);
  if (bytes_read != 6) {
    return false;
  }

  uint8_t data[6];
  for (uint8_t i = 0; i < 6; i++) {
    data[i] = Wire.read();
  }

  if (data[0] & 0x80) {
    return false;
  }

  uint32_t raw_humidity = ((uint32_t)data[1] << 12) |
                          ((uint32_t)data[2] << 4) |
                          ((uint32_t)(data[3] >> 4));
  uint32_t raw_temperature = (((uint32_t)data[3] & 0x0F) << 16) |
                             ((uint32_t)data[4] << 8) |
                             data[5];

  humidity_percent = ((float)raw_humidity * 100.0f) / 1048576.0f;
  temperature_c = (((float)raw_temperature * 200.0f) / 1048576.0f) - 50.0f;

  humidity_percent = constrain(humidity_percent, 0.0f, 100.0f);
  return true;
}
