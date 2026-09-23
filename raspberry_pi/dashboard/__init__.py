"""Dashboard Backend for AI Smart Irrigation Digital Twin.

This module provides the FastAPI-based dashboard backend with REST APIs for:
- Live Sensor Data
- Pump Control and Status
- Weather Information and Forecasts
- AI Predictions
- Water Saving Statistics
- Alerts
- NPK Sensor Data
- Analytics
- Digital Twin Integration
- System Configuration
- Health Status
- Logs
"""

from .main import app
from .schemas import (
    SensorReading,
    SensorDataResponse,
    PumpStatus,
    PumpControlRequest,
    WeatherCurrent,
    WeatherForecastItem,
    WeatherResponse,
    AIPrediction,
    AIPredictionResponse,
    WaterSavingStats,
    Alert,
    AlertsResponse,
    NPKReading,
    NPKResponse,
    AnalyticsSummary,
    DigitalTwinState,
    DigitalTwinSimulationRequest,
    SystemConfig,
    HealthStatus,
    LogEntry,
    LogsResponse
)

__all__ = [
    "app",
    "SensorReading",
    "SensorDataResponse",
    "PumpStatus",
    "PumpControlRequest",
    "WeatherCurrent",
    "WeatherForecastItem",
    "WeatherResponse",
    "AIPrediction",
    "AIPredictionResponse",
    "WaterSavingStats",
    "Alert",
    "AlertsResponse",
    "NPKReading",
    "NPKResponse",
    "AnalyticsSummary",
    "DigitalTwinState",
    "DigitalTwinSimulationRequest",
    "SystemConfig",
    "HealthStatus",
    "LogEntry",
    "LogsResponse"
]
