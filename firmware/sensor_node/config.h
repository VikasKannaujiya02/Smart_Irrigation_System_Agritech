#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// Protocol constants
#define PROTOCOL_VERSION 1
#define MAX_PAYLOAD_BYTES 180
#define HEADER_WITHOUT_CRC_BYTES 14
#define CRC_BYTES 2
#define MAX_PACKET_BYTES 196
#define BROADCAST_DEVICE_ID 0xFFFF
#define GATEWAY_DEVICE_ID 0x0001
#define SENSOR_NODE_DEVICE_ID 0x0002
#define DEFAULT_ACK_TIMEOUT_MS 2000
#define DEFAULT_MAX_RETRIES 3
#define DEFAULT_HEARTBEAT_INTERVAL_MS 60000
#define DEFAULT_SENSOR_INTERVAL_MS 15000
// ^ 2 seconds -- fast field-test response for water/dry soil checks.
//   data. Once everything is confirmed working end-to-end, change this back
//   to something like 300000 (5 min) for real deployment to save battery.

// Packet types
#define PACKET_TYPE_HELLO 1
#define PACKET_TYPE_HEARTBEAT 2
#define PACKET_TYPE_SENSOR_DATA 3
#define PACKET_TYPE_NPK_DATA 4
#define PACKET_TYPE_PUMP_STATUS 5
#define PACKET_TYPE_COMMAND 6
#define PACKET_TYPE_ACK 7
#define PACKET_TYPE_ERROR 8
#define PACKET_TYPE_CONFIG 9
#define PACKET_TYPE_PING 10
#define PACKET_TYPE_PONG 11

// Command types
#define COMMAND_TYPE_MOTOR_ON 1
#define COMMAND_TYPE_MOTOR_OFF 2
#define COMMAND_TYPE_REQUEST_STATUS 3
#define COMMAND_TYPE_SYNC_TIME 4
#define COMMAND_TYPE_RESTART_DEVICE 5
#define COMMAND_TYPE_UPDATE_CONFIG 6

// Pin definitions
#define LORA_SS 10
#define LORA_RST 4
#define LORA_DIO0 2
#define DHT_PIN 3
#define SOIL_MOISTURE_PIN A2
#define BATTERY_PIN A1
#define STATUS_LED_PIN 13
#define SENSOR_PWM_OUT_PIN 9
#define AHT10_ADDRESS 0x38

// LoRa settings
#define LORA_FREQUENCY 868E6
#define LORA_SPREADING_FACTOR 7
#define LORA_SIGNAL_BANDWIDTH 125E3
#define LORA_CODING_RATE 5
#define LORA_POWER 20
#define LORA_SYNC_WORD 0x12

// Sensor calibration
#define SOIL_MOISTURE_AIR_VALUE 895
#define SOIL_MOISTURE_WATER_VALUE 711

// Watchdog settings
#define WATCHDOG_TIMEOUT WDTO_4S

#endif
