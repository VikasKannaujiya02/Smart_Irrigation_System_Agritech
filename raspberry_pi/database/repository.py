"""Repository helpers for database table access."""

from __future__ import annotations

import json
from typing import Any

from .connection import SQLiteConnectionPool
from .query_builder import SelectQuery, build_insert, build_update


class BaseRepository:
    """Reusable repository with transaction-safe CRUD helpers."""

    table_name: str

    def __init__(self, connection_pool: SQLiteConnectionPool) -> None:
        self.connection_pool = connection_pool

    def insert(self, values: dict[str, Any]) -> int:
        sql, params = build_insert(self.table_name, values)
        with self.connection_pool.transaction() as connection:
            cursor = connection.execute(sql, params)
            return int(cursor.lastrowid)

    def update(self, values: dict[str, Any], where_clause: str, *where_params: object) -> int:
        sql, params = build_update(self.table_name, values, where_clause, tuple(where_params))
        with self.connection_pool.transaction() as connection:
            cursor = connection.execute(sql, params)
            return int(cursor.rowcount)

    def find_by_id(self, row_id: int) -> dict[str, Any] | None:
        query = SelectQuery(self.table_name).where("id = ?", row_id)
        rows = self.select(query)
        return rows[0] if rows else None

    def select(self, query: SelectQuery) -> list[dict[str, Any]]:
        sql, params = query.build()

        with self.connection_pool.connection() as connection:
             rows = connection.execute(sql, params).fetchall()
             return [dict(row) for row in rows]


class DeviceRepository(BaseRepository):
    """Repository for registered gateway and field devices."""

    table_name = "Devices"

    def upsert_device(self, values: dict[str, Any]) -> None:
        payload = dict(values)
        payload["metadata_json"] = _json_value(payload.get("metadata_json", {}))
        with self.connection_pool.transaction() as connection:
            connection.execute(
                """
                INSERT INTO Devices(
                    device_id, device_type, name, hardware_version,
                    firmware_version, lora_version, is_active, last_seen_at,
                    metadata_json
                )
                VALUES(
                    :device_id, :device_type, :name, :hardware_version,
                    :firmware_version, :lora_version, :is_active, :last_seen_at,
                    :metadata_json
                )
                ON CONFLICT(device_id) DO UPDATE SET
                    device_type = excluded.device_type,
                    name = excluded.name,
                    hardware_version = excluded.hardware_version,
                    firmware_version = excluded.firmware_version,
                    lora_version = excluded.lora_version,
                    is_active = excluded.is_active,
                    last_seen_at = excluded.last_seen_at,
                    metadata_json = excluded.metadata_json
                """,
                payload,
            )


class SensorDataRepository(BaseRepository):
    table_name = "SensorData"


class NPKDataRepository(BaseRepository):
    table_name = "NPKData"


class PumpStatusRepository(BaseRepository):
    table_name = "PumpStatus"


class CommandRepository(BaseRepository):
    table_name = "Commands"


class ACKHistoryRepository(BaseRepository):
    table_name = "ACKHistory"


class WeatherHistoryRepository(BaseRepository):
    table_name = "WeatherHistory"


class PredictionHistoryRepository(BaseRepository):
    table_name = "PredictionHistory"


class AlertRepository(BaseRepository):
    table_name = "Alerts"


class SystemLogRepository(BaseRepository):
    table_name = "SystemLogs"


class ConfigurationRepository(BaseRepository):
    table_name = "Configurations"

    def set_value(self, key: str, value: str, value_type: str, scope: str = "SYSTEM") -> None:
        with self.connection_pool.transaction() as connection:
            connection.execute(
                """
                INSERT INTO Configurations(config_key, config_value, value_type, scope)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(config_key) DO UPDATE SET
                    config_value = excluded.config_value,
                    value_type = excluded.value_type,
                    scope = excluded.scope,
                    updated_at = datetime('now')
                """,
                (key, value, value_type, scope),
            )


class HealthStatusRepository(BaseRepository):
    table_name = "HealthStatus"


class RepositoryRegistry:
    """Convenience access to all table repositories."""

    def __init__(self, connection_pool: SQLiteConnectionPool) -> None:
        self.devices = DeviceRepository(connection_pool)
        self.sensor_data = SensorDataRepository(connection_pool)
        self.npk_data = NPKDataRepository(connection_pool)
        self.pump_status = PumpStatusRepository(connection_pool)
        self.commands = CommandRepository(connection_pool)
        self.ack_history = ACKHistoryRepository(connection_pool)
        self.weather_history = WeatherHistoryRepository(connection_pool)
        self.prediction_history = PredictionHistoryRepository(connection_pool)
        self.alerts = AlertRepository(connection_pool)
        self.system_logs = SystemLogRepository(connection_pool)
        self.configurations = ConfigurationRepository(connection_pool)
        self.health_status = HealthStatusRepository(connection_pool)


def _json_value(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, separators=(",", ":"))

