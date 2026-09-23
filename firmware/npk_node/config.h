#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// Protocol constants (same as sensor node)
#define PROTOCOL_VERSION 1
#define MAX_PAYLOAD_BYTES 180
#define HEADER_WITHOUT_CRC_BYTES 14
#define CRC_BYTES 2
#define MAX_PACKET_BYTES 196
#define BROADCAST_DEVICE_ID 0xFFFF
#define GATEWAY_DEVICE_ID 0x0001
#define NPK_NODE_DEVICE_ID 0x0003
#define DEFAULT_ACK_TIMEOUT_MS 2000
#define DEFAULT_MAX_RETRIES 3
#define DEFAULT_HEARTBEAT_INTERVAL_MS 60000
#define DEFAULT_SENSOR_INTERVAL_MS 20000
// ^ 20 seconds, per your request. Once fully validated, consider raising
//   this back to something like 300000 (5 min) for real deployment to save
//   battery -- 20s is a testing interval, not a production one.

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
#define LORA_RST 9
#define LORA_DIO0 2
#define RS485_DE 3
#define RS485_RE 4
#define BATTERY_PIN A0
#define STATUS_LED_PIN 13

// LoRa settings
#define LORA_FREQUENCY 868E6
#define LORA_SPREADING_FACTOR 7
#define LORA_SIGNAL_BANDWIDTH 125E3
#define LORA_CODING_RATE 5
#define LORA_POWER 20
#define LORA_SYNC_WORD 0x12

// Modbus settings
#define MODBUS_BAUD_RATE 9600
#define MODBUS_SLAVE_ADDRESS 1
#define MODBUS_TIMEOUT_MS 500
// ^ Real sensor responses arrive within tens of ms at 9600 baud; 500ms
//   is already generous. The old 1000ms, combined with 4 sequential
//   reads in npk_sensor.readAll(), could total ~4.4s in a worst case
//   (all 4 timing out) -- longer than the watchdog window, causing a
//   reset mid-read. Lowered here, and watchdog widened below, so a
//   single bad read can never trip the watchdog on its own.

// Watchdog settings
#define WATCHDOG_TIMEOUT WDTO_8S
// ^ Widened from 4S to 8S for safety margin. Combined with the
//   wdt_reset() calls now inside npk_sensor.cpp's readAll(), a full
//   worst-case sensor read (~2.3s) has comfortable headroom.

#endif
