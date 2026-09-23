"""SQLite schema definitions for the irrigation gateway database."""

from __future__ import annotations

SCHEMA_VERSION = 1

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS SchemaMigrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now')),
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Devices (
    device_id INTEGER PRIMARY KEY,
    device_type TEXT NOT NULL CHECK (
        device_type IN ('GATEWAY', 'SENSOR_NODE', 'NPK_NODE', 'PUMP_CONTROLLER')
    ),
    name TEXT NOT NULL,
    hardware_version TEXT,
    firmware_version TEXT,
    lora_version TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    registered_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS SensorData (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    recorded_at TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    soil_moisture_raw REAL,
    soil_moisture_percent REAL,
    temperature_c REAL,
    humidity_percent REAL,
    battery_voltage REAL,
    battery_percent REAL,
    rssi REAL,
    snr REAL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (device_id) REFERENCES Devices(device_id),
    UNIQUE(device_id, sequence_number)
);

CREATE TABLE IF NOT EXISTS NPKData (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    recorded_at TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    nitrogen_mg_kg REAL,
    phosphorus_mg_kg REAL,
    potassium_mg_kg REAL,
    ph REAL,
    electrical_conductivity REAL,
    soil_temperature_c REAL,
    moisture_percent REAL,
    battery_voltage REAL,
    battery_percent REAL,
    rssi REAL,
    snr REAL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (device_id) REFERENCES Devices(device_id),
    UNIQUE(device_id, sequence_number)
);

CREATE TABLE IF NOT EXISTS PumpStatus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    recorded_at TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    relay_state TEXT NOT NULL CHECK (relay_state IN ('ON', 'OFF', 'UNKNOWN')),
    pump_feedback_state TEXT NOT NULL CHECK (
        pump_feedback_state IN ('RUNNING', 'STOPPED', 'FAULT', 'UNKNOWN')
    ),
    manual_switch_state TEXT NOT NULL CHECK (
        manual_switch_state IN ('AUTO', 'MANUAL_ON', 'MANUAL_OFF', 'UNKNOWN')
    ),
    runtime_seconds INTEGER NOT NULL DEFAULT 0,
    battery_voltage REAL,
    rssi REAL,
    snr REAL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (device_id) REFERENCES Devices(device_id),
    UNIQUE(device_id, sequence_number)
);

CREATE TABLE IF NOT EXISTS Commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command_id TEXT NOT NULL UNIQUE,
    target_device_id INTEGER NOT NULL,
    command_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('QUEUED', 'SENT', 'ACKED', 'FAILED', 'CANCELLED')
    ),
    payload_json TEXT NOT NULL DEFAULT '{}',
    sequence_number INTEGER,
    retry_count INTEGER NOT NULL DEFAULT 0,
    requested_at TEXT NOT NULL DEFAULT (datetime('now')),
    sent_at TEXT,
    acknowledged_at TEXT,
    error_message TEXT,
    FOREIGN KEY (target_device_id) REFERENCES Devices(device_id)
);

CREATE TABLE IF NOT EXISTS ACKHistory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    sequence_number INTEGER NOT NULL,
    packet_type TEXT NOT NULL,
    acked_at TEXT NOT NULL DEFAULT (datetime('now')),
    latency_ms REAL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('ACKED', 'TIMEOUT', 'DUPLICATE')),
    FOREIGN KEY (device_id) REFERENCES Devices(device_id)
);

CREATE TABLE IF NOT EXISTS WeatherHistory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    temperature_c REAL,
    humidity_percent REAL,
    rainfall_mm REAL,
    wind_speed_mps REAL,
    pressure_hpa REAL,
    forecast_horizon_hours INTEGER NOT NULL DEFAULT 0,
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS PredictionHistory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    model_version TEXT,
    prediction_type TEXT NOT NULL,
    horizon_hours INTEGER NOT NULL,
    predicted_for TEXT NOT NULL,
    prediction_value REAL,
    confidence REAL CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    input_hash TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS Alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('INFO', 'WARNING', 'CRITICAL')),
    source_module TEXT NOT NULL,
    device_id INTEGER,
    message TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('OPEN', 'ACKED', 'RESOLVED')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    acknowledged_at TEXT,
    resolved_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (device_id) REFERENCES Devices(device_id)
);

CREATE TABLE IF NOT EXISTS SystemLogs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    logged_at TEXT NOT NULL DEFAULT (datetime('now')),
    level TEXT NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    module TEXT NOT NULL,
    message TEXT NOT NULL,
    device_id INTEGER,
    sequence_number INTEGER,
    context_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (device_id) REFERENCES Devices(device_id)
);

CREATE TABLE IF NOT EXISTS Configurations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT NOT NULL UNIQUE,
    config_value TEXT NOT NULL,
    value_type TEXT NOT NULL CHECK (
        value_type IN ('STRING', 'INTEGER', 'FLOAT', 'BOOLEAN', 'JSON')
    ),
    scope TEXT NOT NULL DEFAULT 'SYSTEM',
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_by TEXT NOT NULL DEFAULT 'system'
);

CREATE TABLE IF NOT EXISTS HealthStatus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    checked_at TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT NOT NULL CHECK (status IN ('ONLINE', 'OFFLINE', 'DEGRADED', 'UNKNOWN')),
    battery_voltage REAL,
    battery_percent REAL,
    last_heartbeat_at TEXT,
    missed_heartbeats INTEGER NOT NULL DEFAULT 0,
    rssi REAL,
    snr REAL,
    error_count INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (device_id) REFERENCES Devices(device_id)
);

CREATE INDEX IF NOT EXISTS idx_devices_type ON Devices(device_type);
CREATE INDEX IF NOT EXISTS idx_devices_last_seen ON Devices(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_sensor_device_time ON SensorData(device_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_npk_device_time ON NPKData(device_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_pump_device_time ON PumpStatus(device_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_commands_target_status ON Commands(target_device_id, status);
CREATE INDEX IF NOT EXISTS idx_ack_device_sequence ON ACKHistory(device_id, sequence_number);
CREATE INDEX IF NOT EXISTS idx_weather_recorded ON WeatherHistory(recorded_at);
CREATE INDEX IF NOT EXISTS idx_predictions_type_horizon ON PredictionHistory(prediction_type, horizon_hours);
CREATE INDEX IF NOT EXISTS idx_alerts_status_severity ON Alerts(status, severity);
CREATE INDEX IF NOT EXISTS idx_system_logs_module_time ON SystemLogs(module, logged_at);
CREATE INDEX IF NOT EXISTS idx_health_device_time ON HealthStatus(device_id, checked_at);
"""

