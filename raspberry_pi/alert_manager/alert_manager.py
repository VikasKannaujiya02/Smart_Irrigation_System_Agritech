"""Alert Manager for AI Smart Irrigation Digital Twin."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional
from enum import Enum

from ..database.repository import RepositoryRegistry


class AlertSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertStatus(Enum):
    OPEN = "OPEN"
    ACKED = "ACKED"
    RESOLVED = "RESOLVED"


class AlertType(Enum):
    # System
    SYSTEM_ERROR = "SYSTEM_ERROR"
    SYSTEM_WARNING = "SYSTEM_WARNING"
    # Safety
    EMERGENCY_STOP = "EMERGENCY_STOP"
    PUMP_PROTECTION = "PUMP_PROTECTION"
    DRY_RUN = "DRY_RUN"
    # Sensors
    SENSOR_HEALTH = "SENSOR_HEALTH"
    SENSOR_TIMEOUT = "SENSOR_TIMEOUT"
    # Devices
    DEVICE_OFFLINE = "DEVICE_OFFLINE"
    DEVICE_LOW_BATTERY = "DEVICE_LOW_BATTERY"
    # Weather
    RAIN_FORECAST = "RAIN_FORECAST"
    # Irrigation
    IRRIGATION_FAILURE = "IRRIGATION_FAILURE"
    # AI
    PREDICTION_LOW_CONFIDENCE = "PREDICTION_LOW_CONFIDENCE"


class Alert:
    """Data class for alert information."""
    def __init__(
        self,
        alert_type: str,
        severity: str,
        source_module: str,
        message: str,
        device_id: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        self.alert_type = alert_type
        self.severity = severity
        self.source_module = source_module
        self.message = message
        self.device_id = device_id
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow().isoformat()
        self.status = AlertStatus.OPEN.value


class AlertManager:
    """Manages alert creation, storage, and retrieval."""

    def __init__(
        self,
        repository_registry: Optional[RepositoryRegistry] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.repository_registry = repository_registry

    def create_alert(
        self,
        alert_type: str,
        severity: str,
        source_module: str,
        message: str,
        device_id: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> int:
        """Create and store a new alert."""
        import json

        self.logger.warning(
            "[%s] %s: %s",
            severity,
            source_module,
            message,
        )

        if self.repository_registry:
            return self.repository_registry.alerts.insert({
                "alert_type": alert_type,
                "severity": severity,
                "source_module": source_module,
                "device_id": device_id,
                "message": message,
                "status": AlertStatus.OPEN.value,
                "metadata_json": json.dumps(metadata or {}, separators=(",", ":")),
            })
        return -1

    def acknowledge_alert(self, alert_id: int) -> None:
        """Mark an alert as acknowledged."""
        if self.repository_registry:
            self.repository_registry.alerts.update(
                {
                    "status": AlertStatus.ACKED.value,
                    "acknowledged_at": datetime.utcnow().isoformat(),
                },
                "id = ?",
                alert_id,
            )
        self.logger.info("Alert %d acknowledged", alert_id)

    def resolve_alert(self, alert_id: int) -> None:
        """Mark an alert as resolved."""
        if self.repository_registry:
            self.repository_registry.alerts.update(
                {
                    "status": AlertStatus.RESOLVED.value,
                    "resolved_at": datetime.utcnow().isoformat(),
                },
                "id = ?",
                alert_id,
            )
        self.logger.info("Alert %d resolved", alert_id)

    def get_active_alerts(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get all active (open/acked) alerts."""
        if self.repository_registry:
            from ..database.query_builder import SelectQuery
            query = (
                SelectQuery("Alerts")
                .where("status IN (?, ?)", AlertStatus.OPEN.value, AlertStatus.ACKED.value)
                .order_by("id DESC")
                .limit(limit)
            )
            return self.repository_registry.alerts.select(query)
        return []

    def get_alerts(
        self,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get alerts with optional filters."""
        if not self.repository_registry:
            return []

        from ..database.query_builder import SelectQuery
        query = SelectQuery("Alerts").order_by("id DESC").limit(limit)

        if status:
            query = query.where("status = ?", status)
        if severity:
            query = query.where("severity = ?", severity)

        return self.repository_registry.alerts.select(query)
