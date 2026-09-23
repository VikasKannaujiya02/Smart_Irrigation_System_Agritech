/* =====================================================================
   Sensor Node 1  –  AI Smart Irrigation Digital Twin
   Device ID : 0x0002
   Board     : Arduino Pro or Pro Mini (3.3 V / 8 MHz  OR  5 V / 16 MHz)
   Sensors   : Capacitive soil-moisture (A2) | AHT10 (I2C) | Battery (A1)
   ===================================================================== */

#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include "config.h"
#include "packet_builder.h"

// ── AHT10 I2C ────────────────────────────────────────────────────────────────
#define AHT10_ADDR 0x38

static bool aht10_init() {
  // Soft-reset / initialise command
  Wire.beginTransmission(AHT10_ADDR);
  Wire.write(0xBE);
  Wire.write(0x08);
  Wire.write(0x00);
  return Wire.endTransmission() == 0;
}

static bool readAHT10(float &temp_c, float &hum_pct) {
  // Trigger measurement
  Wire.beginTransmission(AHT10_ADDR);
  Wire.write(0xAC);
  Wire.write(0x33);
  Wire.write(0x00);
  if (Wire.endTransmission() != 0) return false;

  delay(85); // measurement time

  if (Wire.requestFrom((uint8_t)AHT10_ADDR, (uint8_t)6) != 6) return false;

  uint8_t d[6];
  for (uint8_t i = 0; i < 6; i++) d[i] = Wire.read();

  if (d[0] & 0x80) return false; // sensor busy

  uint32_t raw_hum  = ((uint32_t)d[1] << 12) | ((uint32_t)d[2] << 4) | (d[3] >> 4);
  uint32_t raw_temp = (((uint32_t)d[3] & 0x0F) << 16) | ((uint32_t)d[4] << 8) | d[5];

  hum_pct = constrain(((float)raw_hum  * 100.0f) / 1048576.0f, 0.0f, 100.0f);
  temp_c  = (((float)raw_temp * 200.0f) / 1048576.0f) - 50.0f;
  return true;
}

// ── Soil moisture ─────────────────────────────────────────────────────────────
static uint16_t readSoilRawAdc() {
  ADMUX  = _BV(REFS0) | _BV(MUX1);           // AVCC ref, channel A2
  ADCSRA = _BV(ADEN) | _BV(ADPS2) | _BV(ADPS1) | _BV(ADPS0); // prescaler 128
  delay(50);

  uint32_t total = 0;
  const uint8_t N = 8;
  for (uint8_t i = 0; i < N + 1; i++) {
    ADCSRA |= _BV(ADSC);
    while (ADCSRA & _BV(ADSC)) {}
    uint16_t v = (ADCH << 8) | ADCL;
    if (i > 0) total += v;
    delay(5);
  }
  return (uint16_t)(total / N);
}

static float readSoilMoisturePercent(uint16_t raw) {
  int m = map(raw, SOIL_MOISTURE_AIR_VALUE, SOIL_MOISTURE_WATER_VALUE, 0, 100);
  return (float)constrain(m, 0, 100);
}

// ── Battery ───────────────────────────────────────────────────────────────────
static float readBatteryVoltage() {
  int raw = analogRead(BATTERY_PIN);
  return (raw * (3.3f / 1023.0f)) * 2.0f;   // voltage divider ×2
}

// ── LoRa packet ───────────────────────────────────────────────────────────────
PacketBuilder pkt_builder;
uint16_t seq = 0;

static void sendPacket(float moisture, float temp, float hum, float batt) {
  uint8_t payload[16];
  memcpy(payload +  0, &moisture, 4);
  memcpy(payload +  4, &temp,     4);
  memcpy(payload +  8, &hum,      4);
  memcpy(payload + 12, &batt,     4);

  Packet p = pkt_builder.build(
    PACKET_TYPE_SENSOR_DATA,
    SENSOR_NODE_DEVICE_ID,   // 0x0002
    GATEWAY_DEVICE_ID,        // 0x0001
    seq++,
    payload, sizeof(payload)
  );

  uint8_t buf[MAX_PACKET_BYTES];
  uint16_t buf_len = 0;
  pkt_builder.to_bytes(p, buf, &buf_len);

  Serial.print("[TX] SENSOR_DATA seq="); Serial.print(p.sequence_number);
  Serial.print(" bytes=");              Serial.print(buf_len);
  Serial.print(" moisture=");           Serial.print(moisture, 2);
  Serial.print(" temp=");               Serial.print(temp, 2);
  Serial.print(" humidity=");           Serial.print(hum, 2);
  Serial.print(" battery=");            Serial.println(batt, 2);

  LoRa.beginPacket();
  LoRa.write(buf, buf_len);
  LoRa.endPacket();
}

// ── setup ─────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println();
  Serial.println("=== Sensor Node 1 Boot (0x0002) ===");

  // Soil-moisture capacitive excitation PWM on pin 9
  pinMode(SENSOR_PWM_OUT_PIN, OUTPUT);
  TCCR1A = bit(COM1A0);
  TCCR1B = bit(WGM12) | bit(CS10);
  OCR1A  = 1;
  Serial.println("Soil PWM excitation: OK");

  // I2C + AHT10
  Wire.begin();
  delay(100);
  if (aht10_init()) {
    Serial.println("AHT10 init: OK");
  } else {
    Serial.println("[WARN] AHT10 not detected – temp/hum will be 0.00");
  }

  // LoRa
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
  if (!LoRa.begin(LORA_FREQUENCY)) {
    Serial.println("[FATAL] LoRa init failed");
    while (true) delay(1000);
  }
  LoRa.setSpreadingFactor(LORA_SPREADING_FACTOR);
  LoRa.setSignalBandwidth(LORA_SIGNAL_BANDWIDTH);
  LoRa.setCodingRate4(LORA_CODING_RATE);
  LoRa.setSyncWord(LORA_SYNC_WORD);
  LoRa.enableCrc();
  Serial.println("LoRa init: OK");

  Serial.println("[SYSTEM] NODE1 ready – telemetry starting");
}

// ── loop ──────────────────────────────────────────────────────────────────────
void loop() {
  uint16_t raw_soil = readSoilRawAdc();
  float moisture    = readSoilMoisturePercent(raw_soil);
  float temperature = 0.0f;
  float humidity    = 0.0f;
  float battery     = readBatteryVoltage();

  if (!readAHT10(temperature, humidity)) {
    Serial.println("[WARN] AHT10 read failed");
  }

  Serial.println("--------------------------------");
  Serial.print("RAW ADC   = "); Serial.println(raw_soil);
  Serial.print("MOISTURE  = "); Serial.print(moisture);  Serial.println("%");
  Serial.print("TEMP      = "); Serial.println(temperature, 2);
  Serial.print("HUMIDITY  = "); Serial.println(humidity,    2);
  Serial.print("BATTERY   = "); Serial.println(battery,     2);

  sendPacket(moisture, temperature, humidity, battery);

  delay(DEFAULT_SENSOR_INTERVAL_MS);
}
