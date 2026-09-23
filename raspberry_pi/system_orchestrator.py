"""
System Orchestrator for AI Smart Irrigation Digital Twin - connects all modules together.

Integration Flow:
Firmware -> LoRa -> Gateway -> Packet -> Device Manager -> SQLite DB -> Validation -> Feature Engineering -> AI Prediction -> Decision Engine -> Safety Layer -> Pump Command -> Analytics -> Dashboard -> Digital Twin -> Logging -> Alerts -> Backup -> Config
"""

from __future__ import annotations
import torch # CRITICAL: FIXES THE free(): invalid pointer error on RPi

import logging
import json
import struct
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from collections import deque
import pandas as pd
import numpy as np

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "raspberry_pi"

from .gateway import Gateway, LoRaInterface, DeviceRegistry
from .communication import Packet, CommunicationManager
from .communication.packet_parser import PacketParseError
from .database import DatabaseManager, RepositoryRegistry
# data_processing is deprecated and removed
from .ai.models.predictor import IrrigationPredictor
from .decision_engine import (
    DecisionEngine,
    CommandExecutor,
    SensorData as DESensorData,
    NPKData as DENPKData,
    WeatherData as DEWeatherData,
    AIPrediction as DEAIPrediction,
    TankStatus as DETankStatus,
    PumpStatus as DEPumpStatus,
    IrrigationMode,
    PumpCommand,
    CropConfig,
    SystemConfig
)
from .safety_layer import FailsafeManager
from .analytics import AnalyticsEngine
from .digital_twin import StateManager as DigitalTwinStateManager
# csv_exporter removed as datasets are built purely from sqlite database

# --- Optional add-on modules (new, separate -- do not affect anything above) ---
try:
    from .continuous_learning_module.continuous_learning import DataLogger, ContinuousTrainer, RainGate
    from .continuous_learning_module.weather_predictor import WeatherPredictor
    _ADDON_MODULES_AVAILABLE = True
except ImportError as _addon_import_err:
    _ADDON_MODULES_AVAILABLE = False
    DataLogger = ContinuousTrainer = RainGate = WeatherPredictor = None
from .alert_manager import AlertManager
from .configuration_manager import ConfigurationManager

logger = logging.getLogger(__name__)


class SystemOrchestrator:
    """Main system orchestrator that wires all modules together and coordinates the complete data flow."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the system orchestrator with all module dependencies."""
        self.config = config or {}
        logger.info("=== Initializing AI Smart Irrigation Digital Twin System ===")

        # 1. Initialize configuration manager
        self.configuration_manager = ConfigurationManager()
        logger.info("Configuration Manager initialized")

        # 2. Initialize database layer
        db_config = self.configuration_manager.get_config().database
        self.database_manager = DatabaseManager(
            database_path=db_config.sqlite_path,
            backup_directory=db_config.backup_directory,
            pool_size=db_config.pool_size,
        )
        self.database_manager.start()
        self.repository_registry = RepositoryRegistry(self.database_manager.database.connection_pool)
        # self.csv_exporter = LiveCSVExporter() removed
        logger.info("Database Layer initialized")

        # 3. Initialize safety layer
        self.failsafe_manager = FailsafeManager()
        logger.info("Safety Layer initialized")

        # 4. Initialize communication and gateway
        self.lora_interface = LoRaInterface()
        self.device_registry = DeviceRegistry()
        self.communication_manager = CommunicationManager()
        self.gateway = Gateway(
            lora_interface=self.lora_interface,
            communication_manager=self.communication_manager,
            device_registry=self.device_registry
        )
        logger.info("Gateway & Communication layer initialized")

        logger.info("Legacy Data Processing pipeline references removed")

        # 5b. Rolling window buffer for the production AI model, which
        # expects (30 timesteps x 8 features): Soil_Moisture,
        # Ambient_Temperature, Soil_Temperature, Humidity, Soil_pH,
        # Nitrogen_Level, Phosphorus_Level, Potassium_Level -- in that exact
        # order. A single incoming packet only ever contains SOME of these
        # (SENSOR_DATA gives moisture/ambient temp/humidity, NPK_DATA gives
        # soil temp/pH/N/P/K), so we carry forward the latest known value of
        # each field and snapshot a full 8-value row every time any packet
        # arrives. Once we have 30 rows the AI model can run; before that,
        # AI prediction is skipped gracefully (existing fallback in
        # process_inbound_packet already handles this).
        self.AI_FEATURE_ORDER = [
            "node_1_soil_moisture", "node_2_soil_moisture", "temperature",
            "humidity", "rainfall", "wind_speed", "solar_radiation",
        ]
        self._ai_expected_feature_count = 7
        self._ai_shape_warning_logged = False
        self._latest_sensor_state: Dict[str, float] = {
            "node_1_soil_moisture": 30.0,
            "node_2_soil_moisture": 30.0,
            "temperature": 25.0,
            "humidity": 60.0,
            "rainfall": 0.0,
            "wind_speed": 5.0,
            "solar_radiation": 400.0,
        }
        self._feature_window: deque = deque(maxlen=24)
        logger.info("AI feature window initialized (0/24 readings so far)")

        # --- Optional add-ons: continuous learning + rain gate + weather model ---
        # These are new and independent of everything above. If anything here
        # is missing (files, .pkl scalers, etc.) it's logged and skipped --
        # it will never prevent the existing system from starting or running.
        self._data_logger = None
        self._continuous_trainer = None
        self._rain_gate = None
        self._weather_predictor = None
        self._latest_regional_wetness: Optional[Dict[str, Any]] = None
        self._last_weather_check = None
        self._last_retrain_check = None
        self._manual_pump_latch: Optional[PumpCommand] = None
        self._last_auto_pump_command: Optional[PumpCommand] = None
        self._last_auto_pump_command_at: float = 0.0
        self._auto_pump_command_min_interval_seconds = 10.0
        self._cached_feature_scaler = None  # loaded once on first AI prediction

        if _ADDON_MODULES_AVAILABLE:
            try:
                self._data_logger = DataLogger(
                    csv_path="data/real_field_readings.csv"
                )
                self._continuous_trainer = ContinuousTrainer(
                    csv_path="data/real_field_readings.csv",
                    model_path=str(Path(__file__).resolve().parent.parent / "HYBRID TCN + LSTM MODEL" / "Models" / "FINAL_GA_GAT_TCN_LSTM.pth"),
                    scaler_path=str(Path(__file__).resolve().parent.parent / "HYBRID TCN + LSTM MODEL" / "Models" / "FINAL_GA_feature_scaler.pkl"),
                )
                
                # Setup live weather service instead of the old RainGate
                logger.info("Initializing Live WeatherService")
                from .weather_api.weather_service import WeatherService
                
                config_path = str(Path(__file__).resolve().parent.parent / "configs" / "system.yaml")
                if Path(config_path).exists():
                    self._weather_service = WeatherService.from_config(config_path)
                else: # fallback for unit tests or missed configs
                    from .weather_api.forecast_manager import ForecastManager
                    from .weather_api.weather_provider import OpenMeteoProvider
                    from .weather_api.weather_cache import WeatherCache
                    from .weather_api.rain_prediction import RainPredictor
                    provider = OpenMeteoProvider(api_key="", base_url="https://api.open-meteo.com/v1", timeout=10, retries=3)
                    cache = WeatherCache(cache_dir="data/weather_cache", cache_ttl_seconds=1800)
                    forecast_manager = ForecastManager(provider=provider, cache=cache, latitude=25.3176, longitude=82.9739)
                    rain_predictor = RainPredictor(rain_threshold_probability=50.0, rain_threshold_volume=2.0)
                    self._weather_service = WeatherService(forecast_manager, rain_predictor)
                
                logger.info("Continuous learning / live weather service add-ons initialized")
            except Exception as addon_exc:
                logger.warning(
                    "Add-on modules (continuous learning / live weather "
                    "service) could not initialize -- system "
                    "continues normally without them: %s", addon_exc
                )
        else:
            logger.info("Add-on modules not found -- system continues normally without them")

        # 6. Initialize AI and Prediction
        self.model_registry_dir = Path(__file__).parent / 'ai' / 'models'
        self.irrigation_predictor = IrrigationPredictor(
            registry_dir=self.model_registry_dir,
            horizon_hours=[24],
        )
        self.model_registry = self.irrigation_predictor.registry
        logger.info("AI Prediction layer initialized")

        # 7. Initialize Decision Engine
        self.crop_config = CropConfig()
        self.system_config = SystemConfig()
        self.decision_engine = DecisionEngine(
            crop_config=self.crop_config,
            system_config=self.system_config,
            failsafe_manager=self.failsafe_manager
        )
        self.command_executor = CommandExecutor(
            failsafe_manager=self.failsafe_manager,
            command_manager=self.communication_manager.command_manager,
            ack_manager=self.communication_manager.ack_manager,
            retry_manager=self.communication_manager.retry_manager,
            gateway=self.gateway,
            repository_registry=self.repository_registry,
        )
        logger.info("Decision Engine initialized")

        # 8. Initialize Analytics
        self.analytics_engine = AnalyticsEngine(self.repository_registry)
        logger.info("Analytics Engine initialized")

        # 9. Initialize Digital Twin
        self.digital_twin = DigitalTwinStateManager()
        logger.info("Digital Twin initialized")

        # 10. Initialize Alert Manager
        self.alert_manager = AlertManager(self.repository_registry)
        logger.info("Alert Manager initialized")

        logger.info("=== System Initialization Complete ===")

    def process_inbound_packet(self, raw_packet: bytes) -> None:
        """
        Process an inbound LoRa packet end-to-end through the complete flow.

        Args:
            raw_packet: Raw bytes from LoRa radio
        """
        logger.info("Processing inbound LoRa packet")
        
        try:
            # 1. Gateway processes raw packet
            try:
                packet = self.gateway.handle_raw_packet(raw_packet)
            except PacketParseError as parse_exc:
                logger.warning(
                    "Ignoring invalid LoRa frame bytes=%d: %s",
                    len(raw_packet), parse_exc
                )
                return
            if not packet:
                logger.debug("Packet processing skipped (invalid or duplicate)")
                return

            # Device-labeled debug print -- shows which physical node this
            # packet came from and what type it is. Device ID -> name mapping
            # comes from your config; if it looks wrong, check
            # NODE_DEVICE_ID / PUMP_CONTROLLER_DEVICE_ID etc. in each
            # firmware's config.h against these numbers.
            device_labels = {}  # fill in once you confirm exact IDs, e.g. {1: "SENSOR_NODE", 2: "NPK_NODE", 4: "PUMP_CONTROLLER"}
            source_label = device_labels.get(packet.source_device, f"DEVICE_ID_{packet.source_device}")
            print(f"[{source_label}] {packet.packet_type.name} (seq={packet.sequence_number}, "
                  f"bytes={len(packet.payload)})")

            # 2. Parse packet payload
            payload = self._parse_packet_payload(packet)

            # 2b. Ensure the sending device is registered (Devices table is
            # the FK parent for SensorData/NPKData/PumpStatus/Commands;
            # devices were never being registered before their first
            # insert, causing every first-contact packet to fail with a
            # FOREIGN KEY constraint error).
            self._ensure_device_registered(packet)

            # 3. Store in database
            self._store_packet_data(packet, payload)

            # ---------------------------------------------------------------
            # CRITICAL GATE: Only run the irrigation decision pipeline for
            # packets that carry actual sensor readings.  ACK, HEARTBEAT,
            # PUMP_STATUS, COMMAND, HELLO, PING, PONG, ERROR, CONFIG packets
            # are control / housekeeping messages -- they MUST NOT trigger a
            # new irrigation decision.  Before this gate was added, every ACK
            # that arrived after a PUMP ON command immediately re-evaluated
            # the decision engine (with no moisture data → DO_NOT_IRRIGATE)
            # and sent a PUMP OFF, making the motor flip ON→OFF within ~1s.
            # ---------------------------------------------------------------
            from .communication.protocol_constants import PacketType as _PT
            DATA_PACKET_TYPES = {_PT.SENSOR_DATA, _PT.NPK_DATA}
            if packet.packet_type not in DATA_PACKET_TYPES:
                logger.debug(
                    "Housekeeping packet type=%s — skipping decision pipeline",
                    packet.packet_type.name,
                )
                return

            # 4. Validate data
            validated_data = self._validate_data(payload)
            
            # 5. Update the 7-feature rolling window 
            self._update_feature_window(packet, payload)
            features = validated_data
            
            # 6. AI Prediction
            # NOTE: the production TCN+LSTM model expects a (30, 8) rolling
            # window (30 past readings x 8 specific features), but we only
            # have a single reading here, so this will fail until the
            # rolling-window pipeline is built. That is a separate, larger
            # task. Until then, AI failures must NOT block the rest of the
            # pipeline (decision engine / motor command) -- fall back to a
            # "no AI opinion" prediction and keep going on rule-based logic.
            try:
                prediction = self._run_ai_prediction(features)
            except Exception as ai_exc:
                ai_exc_text = str(ai_exc)
                if (
                    "AI model input not compatible" in ai_exc_text
                    and self._ai_shape_warning_logged
                ):
                    logger.debug(
                        "AI prediction skipped; continuing with rule-based "
                        "decision only: %s", ai_exc_text
                    )
                else:
                    logger.warning(
                        "AI prediction unavailable, continuing with rule-based "
                        "decision only: %s", ai_exc
                    )
                prediction = DEAIPrediction(
                    soil_moisture_predicted=None,
                    irrigation_need_score=None,
                    water_requirement_liters=None,
                    confidence=0.0,
                    used_fallback=True,
                )
            self._store_prediction(prediction)
            
            # 7. Decision Engine
            decision = self._run_decision_engine(validated_data, prediction)
            
            # 8. Execute pump command if needed.
            # Dashboard manual control sets a temporary latch to execute the
            # command. If the user explicitly configured the system to AI or
            # Rules mode, we clear that latch here so the AI takes back
            # autonomous control on the next telemetry packet cycle. 
            # (To lock the pump permanently, the user must set Config to MANUAL).
            if self.system_config.irrigation_mode != IrrigationMode.MANUAL and self._manual_pump_latch is not None:
                logger.info("System is in %s mode: clearing temporary manual dashboard latch", self.system_config.irrigation_mode.name)
                self._manual_pump_latch = None
                if self.failsafe_manager.manual_override.enabled:
                    self.failsafe_manager.deactivate_manual_override()

            if self._manual_pump_latch is not None:
                logger.info(
                    "Manual pump latch active (%s); skipping automatic pump command %s",
                    self._manual_pump_latch.name,
                    decision.pump_command.name,
                )
            else:
                # IMPORTANT: PumpCommand uses Python auto() so .value is an
                # integer (1, 2, 3), NOT a string like "ON"/"OFF".
                # Always compare using the enum member directly with `is`.
                suppress_for_rain = False
                if getattr(self, "_weather_service", None) is not None:
                    # Run rain prediction based on OpenMeteo live feed!
                    recommendation = self._weather_service.get_irrigation_recommendation()
                    if recommendation and not recommendation.should_irrigate:
                        suppress_for_rain = True
                        prob = recommendation.rain_prediction.rain_probability if recommendation.rain_prediction else 0.0
                        vol = recommendation.rain_prediction.rain_volume if recommendation.rain_prediction else 0.0
                        logger.info(
                            "IRRIGATION SUPPRESSED DUE TO UPCOMING RAIN: %s (Probability: %.1f%%, Volume: %.1f mm)",
                            recommendation.reason, prob, vol
                        )

                if decision.pump_command is PumpCommand.ON:
                    # Rule-Based / AI says irrigate — send ON if not duplicate
                    if not suppress_for_rain and not self._should_skip_duplicate_auto_command(decision.pump_command):
                        logger.info(
                            "Decision=%s mode=%s — sending PUMP ON command",
                            decision.decision.name, decision.mode.name,
                        )
                        execution_result = self.command_executor.execute_pump_command(decision)
                        self._store_command_result(execution_result)
                        self._last_auto_pump_command = decision.pump_command
                        self._last_auto_pump_command_at = time.monotonic()
                    elif suppress_for_rain:
                        logger.info(
                            "Decision=%s mode=%s — skipping PUMP ON command (Rain expected)",
                            decision.decision.name, decision.mode.name,
                        )

                elif decision.pump_command is PumpCommand.OFF:
                    # Rule-Based / AI says stop — only send OFF if pump was
                    # previously turned ON automatically (avoid redundant OFFs).
                    if self._last_auto_pump_command is PumpCommand.ON or suppress_for_rain:
                        if not self._should_skip_duplicate_auto_command(decision.pump_command):
                            logger.info(
                                "Decision=%s mode=%s — sending PUMP OFF command (moisture satisfied)",
                                decision.decision.name, decision.mode.name,
                            )
                            execution_result = self.command_executor.execute_pump_command(decision)
                            self._store_command_result(execution_result)
                            self._last_auto_pump_command = decision.pump_command
                            self._last_auto_pump_command_at = time.monotonic()

            # 9. Update digital twin
            try:
                self._update_digital_twin(validated_data, decision)
            except Exception as dt_exc:
                logger.warning(
                    "Digital twin update skipped (needs proper "
                    "Field/Soil/Pump/Crop/Weather model integration): %s",
                    dt_exc,
                )

            # 10. Run analytics
            self._run_analytics()

            # 11. Check for alerts
            self._check_alerts()

            # 12. Add-on: daily weather prediction + continuous-learning check
            self._run_addon_daily_tasks()

            logger.info("Packet processing complete")
            
        except Exception as e:
            logger.error(f"Error processing inbound packet: {str(e)}", exc_info=True)
            self.alert_manager.create_alert(
                alert_type="SYSTEM_ERROR",
                severity="CRITICAL",
                source_module="SystemOrchestrator",
                message=f"Packet processing failed: {str(e)}"
            )

    def _should_skip_duplicate_auto_command(self, pump_command: PumpCommand) -> bool:
        """Prevent automatic decisions from flooding LoRa with repeated commands."""
        elapsed = time.monotonic() - self._last_auto_pump_command_at
        if (
            self._last_auto_pump_command == pump_command
            and elapsed < self._auto_pump_command_min_interval_seconds
        ):
            logger.info(
                "Skipping duplicate automatic pump command %s; %.1fs since last send",
                pump_command.name, elapsed
            )
            return True
        return False

    def _ensure_device_registered(self, packet: Packet) -> None:
        """Upsert the sending device into the Devices table.

        Devices is the FK parent for SensorData/NPKData/PumpStatus/Commands,
        but nothing was calling DeviceRepository.upsert_device before this,
        so any device's very first packet failed the insert with a
        FOREIGN KEY constraint error.
        """
        from communication.protocol_constants import DeviceType

        try:
            device_type = DeviceType(packet.source_device)
        except ValueError:
            logger.warning(
                "Unknown source_device=%s; skipping device registration",
                packet.source_device,
            )
            return

        self.repository_registry.devices.upsert_device({
            "device_id": packet.source_device,
            "device_type": device_type.name,
            "name": device_type.name.replace("_", " ").title(),
            "hardware_version": None,
            "firmware_version": None,
            "lora_version": None,
            "is_active": 1,
            "last_seen_at": datetime.now(timezone.utc).isoformat(),
            "metadata_json": {},
        })

    def set_manual_pump_latch(self, command: PumpCommand) -> None:
        """Latch dashboard manual pump state until the next manual command."""
        self._manual_pump_latch = command
        logger.info("Manual pump latch set to %s", command.name)

    def _parse_packet_payload(self, packet: Packet) -> Dict[str, Any]:
        """Decode the packet payload into a dict of named fields.

        Field devices (ESP8266 pump controller, sensor/NPK nodes) do not
        send JSON over LoRa -- payloads are compact packed binary to
        conserve airtime. Decode per packet type using the wire format
        each node's firmware actually emits (see pump_controller's
        command_processor.cpp::sendStatus / sendAck).
        """
        try:
            packet_type_name = packet.packet_type.name
            if packet_type_name == "PUMP_STATUS":
                return self._parse_pump_status_payload(packet.payload)
            if packet_type_name == "NPK_DATA":
                return self._parse_npk_data_payload(packet.payload)
            if packet_type_name == "SENSOR_DATA":
                return self._parse_sensor_data_payload(packet.payload)
            if packet_type_name == "ACK":
                return self._parse_ack_payload(packet.payload)
            if not packet.payload:
                return {}
            # Fallback for any node/packet type that does send JSON.
            payload = json.loads(packet.payload.decode('utf-8'))
            return payload
        except Exception as e:
            logger.warning(f"Failed to parse payload: {e}")
            return {}

    def _parse_pump_status_payload(self, payload: bytes) -> Dict[str, Any]:
        """Decode PUMP_STATUS payload (13 bytes, big-endian) built by
        CommandProcessor::sendStatus on the ESP8266:
        [relay][feedback][manual][estop][diag] uint8 x5, runtimeMs uint32,
        totalRuntimeMs uint32.

        Field values are mapped to the exact enums enforced by the
        PumpStatus table CHECK constraints in database/schema.py:
          relay_state          IN ('ON', 'OFF', 'UNKNOWN')
          pump_feedback_state  IN ('RUNNING', 'STOPPED', 'FAULT', 'UNKNOWN')
          manual_switch_state  IN ('AUTO', 'MANUAL_ON', 'MANUAL_OFF', 'UNKNOWN')
        """
        if len(payload) < 13:
            raise ValueError(f"PUMP_STATUS payload too short: {len(payload)} bytes")
        relay_state, feedback_state, manual_override, emergency_stop, diagnostics_ok = payload[0:5]
        runtime_ms, total_runtime_ms = struct.unpack('>II', payload[5:13])

        if not diagnostics_ok:
            pump_feedback = "FAULT"
        elif feedback_state:
            pump_feedback = "RUNNING"
        else:
            pump_feedback = "STOPPED"

        if manual_override:
            manual_switch = "MANUAL_ON" if relay_state else "MANUAL_OFF"
        else:
            manual_switch = "AUTO"

        return {
            "relay_state": "ON" if relay_state else "OFF",
            "pump_state": pump_feedback,
            "switch_state": manual_switch,
            "runtime": runtime_ms // 1000,
            "emergency_stop_active": bool(emergency_stop),
            "diagnostics_ok": bool(diagnostics_ok),
            "total_runtime_ms": total_runtime_ms,
        }

    def _parse_npk_data_payload(self, payload: bytes) -> Dict[str, Any]:
        """Decode NPK_DATA payload (25 bytes) built by
        npk_node.ino::sendNPKDataPacket on the ESP8266.

        Layout (mixed endianness -- matches the firmware exactly):
          nitrogen        uint16  big-endian    bytes 0-1
          phosphorus      uint16  big-endian    bytes 2-3
          potassium       uint16  big-endian    bytes 4-5
          ec              float32 little-endian bytes 6-9   (raw memcpy on AVR/ESP)
          ph              float32 little-endian bytes 10-13 (raw memcpy on AVR/ESP)
          soil_temp       float32 little-endian bytes 14-17 (raw memcpy on AVR/ESP)
          soil_moisture   uint16  big-endian    bytes 18-19
          battery_voltage float32 little-endian bytes 20-23 (raw memcpy on AVR/ESP)
          valid           uint8                 byte 24

        The integer fields are manually byte-swapped MSB-first in firmware,
        but the float fields are copied via memcpy() of the MCU's native
        (little-endian) in-memory representation -- so this packet mixes two
        different byte orders for different fields, by construction.
        """
        if len(payload) < 25:
            raise ValueError(f"NPK_DATA payload too short: {len(payload)} bytes")

        nitrogen, phosphorus, potassium = struct.unpack('>HHH', payload[0:6])
        ec, ph, soil_temp = struct.unpack('<fff', payload[6:18])
        (soil_moisture,) = struct.unpack('>H', payload[18:20])
        (battery_voltage,) = struct.unpack('<f', payload[20:24])
        valid = bool(payload[24])

        return {
            "nitrogen": nitrogen,
            "phosphorus": phosphorus,
            "potassium": potassium,
            "ec": ec,
            "ph": ph,
            "soil_temp": soil_temp,
            "soil_moisture": soil_moisture,
            "battery_voltage": battery_voltage,
            "valid": valid,
        }

    def _parse_sensor_data_payload(self, payload: bytes) -> Dict[str, Any]:
        """Decode SENSOR_DATA payload (16 bytes) built by
        sensor_node.ino::sendSensorDataPacket: four float32 values in
        the AVR's native little-endian layout (memcpy'd directly, no
        manual byte packing) -- soil_moisture_percent, temperature_c,
        humidity_percent, battery_voltage, in that order.
        """
        if len(payload) < 16:
            raise ValueError(f"SENSOR_DATA payload too short: {len(payload)} bytes")
        soil_moisture, temperature, humidity, battery_voltage = struct.unpack(
            '<ffff', payload[0:16]
        )
        return {
            "soil_moisture": soil_moisture,
            "temperature": temperature,
            "humidity": humidity,
            "battery_voltage": battery_voltage,
        }

    def _parse_ack_payload(self, payload: bytes) -> Dict[str, Any]:
        """Decode ACK payload (2 bytes, big-endian acked sequence number)
        built by CommandProcessor::sendAck on the ESP8266."""
        if len(payload) < 2:
            return {}
        (acked_sequence,) = struct.unpack('>H', payload[:2])
        return {"acked_sequence": acked_sequence}

    def _store_packet_data(self, packet: Packet, payload: Dict[str, Any]) -> None:
        """Store packet data in the appropriate database table.

        Storage failures here (e.g. a UNIQUE(device_id, sequence_number)
        collision after a device reboots and its sequence counter restarts
        from 0) must NOT abort the rest of the pipeline -- feature
        engineering, the decision engine, and the motor command all still
        need to run for this packet even if the raw telemetry row couldn't
        be persisted. We log and continue instead of propagating.
        """
        recorded_at = datetime.now(timezone.utc).isoformat()

        try:
            if packet.packet_type.name == "SENSOR_DATA":
                values = {
                    "device_id": packet.source_device,
                    "recorded_at": recorded_at,
                    "sequence_number": packet.sequence_number,
                    "soil_moisture_percent": payload.get("soil_moisture"),
                    "temperature_c": payload.get("temperature"),
                    "humidity_percent": payload.get("humidity"),
                    "battery_voltage": payload.get("battery_voltage"),
                    "battery_percent": payload.get("battery_percent"),
                    "rssi": payload.get("rssi"),
                    "snr": payload.get("snr"),
                    "payload_json": json.dumps(payload)
                }
                self.repository_registry.sensor_data.insert(values)
                # csv_exporter removed
            elif packet.packet_type.name == "NPK_DATA":
                values = {
                    "device_id": packet.source_device,
                    "recorded_at": recorded_at,
                    "sequence_number": packet.sequence_number,
                    "nitrogen_mg_kg": payload.get("nitrogen"),
                    "phosphorus_mg_kg": payload.get("phosphorus"),
                    "potassium_mg_kg": payload.get("potassium"),
                    "ph": payload.get("ph"),
                    "electrical_conductivity": payload.get("ec"),
                    "soil_temperature_c": payload.get("soil_temp"),
                    "moisture_percent": payload.get("soil_moisture"),
                    "battery_voltage": payload.get("battery_voltage"),
                    "battery_percent": payload.get("battery_percent"),
                    "rssi": payload.get("rssi"),
                    "snr": payload.get("snr"),
                    "payload_json": json.dumps(payload)
                }
                self.repository_registry.npk_data.insert(values)
                # csv_exporter removed
            elif packet.packet_type.name == "PUMP_STATUS":
                values = {
                    "device_id": packet.source_device,
                    "recorded_at": recorded_at,
                    "sequence_number": packet.sequence_number,
                    "relay_state": payload.get("relay_state", "UNKNOWN"),
                    "pump_feedback_state": payload.get("pump_state", "UNKNOWN"),
                    "manual_switch_state": payload.get("switch_state", "UNKNOWN"),
                    "runtime_seconds": payload.get("runtime", 0),
                    "battery_voltage": payload.get("battery_voltage"),
                    "rssi": payload.get("rssi"),
                    "snr": payload.get("snr"),
                    "payload_json": json.dumps(payload)
                }
                self.repository_registry.pump_status.insert(values)
                # csv_exporter removed
        except Exception as storage_exc:
            logger.warning(
                "Telemetry storage skipped for %s seq=%s (likely duplicate "
                "sequence number after a device reboot) -- continuing: %s",
                packet.packet_type.name, packet.sequence_number, storage_exc
            )

    def _validate_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate inbound data."""
        return {k: [v] for k, v in payload.items()}

    def _run_addon_daily_tasks(self) -> None:
        """Runs the two add-on periodic tasks (weather prediction and
        continuous-learning fine-tune) at most once per day. Simple
        date-based check, no complex scheduling. Every call here is wrapped
        so a failure never affects packet processing.
        """
        today = datetime.now(timezone.utc).date()

        if self._weather_predictor is not None and self._last_weather_check != today:
            try:
                result = self._weather_predictor.predict_regional_wetness()
                self._latest_regional_wetness = result
                logger.info("Daily regional weather prediction: %s", result)
            except Exception as weather_exc:
                logger.warning("Daily weather prediction skipped (non-fatal): %s", weather_exc)
            finally:
                self._last_weather_check = today

        if self._continuous_trainer is not None and self._last_retrain_check != today:
            try:
                self._continuous_trainer.maybe_retrain()
            except Exception as retrain_exc:
                logger.warning("Daily continuous-learning check skipped (non-fatal): %s", retrain_exc)
            finally:
                self._last_retrain_check = today

    def get_regional_wetness_prediction(self) -> Optional[Dict[str, Any]]:
        """Return the latest NASA POWER regional wetness prediction.

        This is an optional add-on value for dashboard display only. Failures
        stay non-fatal so LoRa packet processing and irrigation control keep
        running exactly as before.
        """
        if self._weather_predictor is None:
            return self._latest_regional_wetness

        today = datetime.now(timezone.utc).date()
        if self._latest_regional_wetness and self._last_weather_check == today:
            return self._latest_regional_wetness

        try:
            self._latest_regional_wetness = self._weather_predictor.predict_regional_wetness()
            self._last_weather_check = today
        except Exception as weather_exc:
            logger.warning("Regional wetness prediction unavailable (non-fatal): %s", weather_exc)
        return self._latest_regional_wetness

    def _update_feature_window(self, packet: Packet, payload: Dict[str, Any]) -> None:
        """Update the carry-forward sensor state from whatever fields this
        packet's payload contains, then snapshot a full 7-value row into the
        rolling window. Missing fields keep their last known value (carry
        forward) rather than resetting to 0. ROUTE MULTIPLE SENSOR NODES
        TO SEPARATE NODE FEATURES BASED ON DEVICE ID!
        """
        from raspberry_pi.database.query_builder import SelectQuery
        
        wea = self.repository_registry.weather_history.select(SelectQuery("WeatherHistory").order_by("id DESC").limit(1))
        latest_weather = wea[0] if wea else {}
        
        temp = payload.get("temperature")
        if temp == 0.0 or temp is None:
            temp = latest_weather.get("temperature_c") if latest_weather.get("temperature_c") is not None else 25.0
            
        hum = payload.get("humidity")
        if hum == 0.0 or hum is None:
            hum = latest_weather.get("humidity_percent") if latest_weather.get("humidity_percent") is not None else 60.0

        rain = latest_weather.get("rainfall_mm", 0.0)
        wind = latest_weather.get("wind_speed_kmh", 5.0)
        solar = latest_weather.get("solar_radiation_wm2", 400.0)

        # Assuming device_id 3 is Node 2. If it's something else, adjust accordingly.
        # Fallback to Node 1 if not explicitly Node 2.
        is_node_2 = packet.source_device == 3
        
        node_1_moisture = payload.get("soil_moisture") if not is_node_2 else None
        node_2_moisture = payload.get("soil_moisture") if is_node_2 else None

        field_map = {
            "node_1_soil_moisture": node_1_moisture,
            "node_2_soil_moisture": node_2_moisture,
            "temperature": temp,
            "humidity": hum,
            "rainfall": rain,
            "wind_speed": wind,
            "solar_radiation": solar,
        }
        for key, value in field_map.items():
            if value is not None:
                self._latest_sensor_state[key] = float(value)

        row = [self._latest_sensor_state[key] for key in self.AI_FEATURE_ORDER]
        self._feature_window.append(row)
        logger.debug(
            "Feature window updated (%d/24 readings): %s",
            len(self._feature_window), self._latest_sensor_state
        )

        # --- Add-on: log this real reading for continuous learning ---
        # This only ever appends to a CSV -- it cannot affect the buffer,
        # the prediction, or anything above.
        if self._data_logger is not None:
            try:
                self._data_logger.log_reading(self._latest_sensor_state)
            except Exception as log_exc:
                logger.warning("Continuous-learning data logging failed (non-fatal): %s", log_exc)

    # def _engineer_features removed because the legacy pipeline was archived

    def _run_ai_prediction(self, features) -> DEAIPrediction:
        """Run AI prediction using the rolling window."""
        if len(self._feature_window) < 24:
            raise ValueError(
                f"AI prediction needs a full 24-reading window, only have "
                f"{len(self._feature_window)} so far"
            )

        live_feature_count = len(self.AI_FEATURE_ORDER)
        x_raw = np.array(self._feature_window, dtype=np.float32)
        x = x_raw.reshape((1, 24, live_feature_count))

        import joblib
        import os
        if self._cached_feature_scaler is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            scaler_path = os.path.join(base_dir, "HYBRID TCN + LSTM MODEL", "Models", "FINAL_GA_feature_scaler.pkl")
            self._cached_feature_scaler = joblib.load(scaler_path)
            logger.info("Feature scaler loaded and cached from %s", scaler_path)
        x_scaled = self._cached_feature_scaler.transform(x[0])
        x_scaled = x_scaled.reshape((1, 24, 7))
        
        # Predict uses our new pytorch model registry logic
        out = self.irrigation_predictor.registry.get_model("all_targets", 24).predict(x_scaled)
        
        # out shape is (1, 10). Horizons are 1, 6, 12, 24, 168.
        # [1h Node1, 1h Node2, 6h Node1, 6h Node2, 12h Node1, 12h Node2, 24h Node1, 24h Node2, 168h Node1, 168h Node2]
        
        soil_24h_node1 = float(out[0, 6])
        
        raw_out = {
            "1h": {"node_1": float(out[0, 0]), "node_2": float(out[0, 1])},
            "6h": {"node_1": float(out[0, 2]), "node_2": float(out[0, 3])},
            "12h": {"node_1": float(out[0, 4]), "node_2": float(out[0, 5])},
            "24h": {"node_1": float(out[0, 6]), "node_2": float(out[0, 7])},
            "7d": {"node_1": float(out[0, 8]), "node_2": float(out[0, 9])}
        }
        
        # Irrigation need score: graded based on predicted 24h soil moisture.
        # Uses dynamically configured thresholds from System and Crop configurations.
        emerg_thresh = self.system_config.emergency_moisture_threshold
        min_thresh = self.crop_config.min_soil_moisture
        ideal_thresh = self.crop_config.ideal_soil_moisture
        
        if soil_24h_node1 < emerg_thresh:
            irr_score = 1.0
        elif soil_24h_node1 < min_thresh:
            range_span = max(1.0, min_thresh - emerg_thresh)
            irr_score = 0.75 + (min_thresh - soil_24h_node1) / (range_span * 4) # 0.75 - 1.0
        elif soil_24h_node1 < ideal_thresh:
            range_span = max(1.0, ideal_thresh - min_thresh)
            irr_score = (ideal_thresh - soil_24h_node1) / (range_span / 0.3) # 0.0 - 0.30
        else:
            irr_score = 0.0
        irr_score = round(min(1.0, max(0.0, irr_score)), 3)

        water_req = max(0.0, (ideal_thresh - soil_24h_node1) * 2) if soil_24h_node1 < ideal_thresh else 0.0
        pred_obj = DEAIPrediction(
            soil_moisture_predicted=soil_24h_node1,
            irrigation_need_score=irr_score,
            water_requirement_liters=round(water_req, 1),
            confidence=0.9,
            used_fallback=False,
            prediction_horizon_hours=24,
        )
        pred_obj.raw_output = raw_out
        return pred_obj
    def _store_prediction(self, prediction: DEAIPrediction) -> None:
        """Store prediction in database."""
        values = {
            "model_name": "GA-GAT-TCN-LSTM",
            "model_version": "ga_gat_tcn_lstm_v1",
            "prediction_type": "soil_moisture_multi_horizon",
            "horizon_hours": prediction.prediction_horizon_hours,
            "predicted_for": datetime.now(timezone.utc).isoformat(),
            "prediction_value": prediction.soil_moisture_predicted,
            "confidence": prediction.confidence,
            "payload_json": json.dumps({
                "irrigation_need_score": prediction.irrigation_need_score,
                "water_requirement_liters": prediction.water_requirement_liters,
                "used_fallback": prediction.used_fallback,
                "raw_output": getattr(prediction, "raw_output", {})
            })
        }
        self.repository_registry.prediction_history.insert(values)
        # self.csv_exporter.append_ai_prediction(values) removed

    def _run_decision_engine(self, validated_data: pd.DataFrame, prediction: DEAIPrediction):
        """Run decision engine to get irrigation decision."""
        # Convert DataFrame to decision engine data models
        sensor_data = DESensorData(
            soil_moisture_percent=validated_data.get("soil_moisture_percent",
                validated_data.get("soil_moisture", [None]))[0],
            temperature_c=validated_data.get("temperature_c",
                validated_data.get("temperature", [None]))[0],
            humidity_percent=validated_data.get("humidity_percent",
                validated_data.get("humidity", [None]))[0],
            battery_voltage=validated_data.get("battery_voltage", [None])[0],
            battery_percent=validated_data.get("battery_percent", [None])[0]
        )
        npk_data = DENPKData(
            nitrogen_mg_kg=validated_data.get("nitrogen_mg_kg",
                validated_data.get("nitrogen", [None]))[0],
            phosphorus_mg_kg=validated_data.get("phosphorus_mg_kg",
                validated_data.get("phosphorus", [None]))[0],
            potassium_mg_kg=validated_data.get("potassium_mg_kg",
                validated_data.get("potassium", [None]))[0],
            ph=validated_data.get("ph", [None])[0],
            electrical_conductivity=validated_data.get("electrical_conductivity",
                validated_data.get("ec", [None]))[0]
        )
        weather_data = DEWeatherData()
        tank_status = DETankStatus()
        pump_status = DEPumpStatus()
        
        return self.decision_engine.evaluate(
            sensor_data=sensor_data,
            npk_data=npk_data,
            weather_data=weather_data,
            ai_prediction=prediction,
            tank_status=tank_status,
            pump_status=pump_status
        )

    def _store_command_result(self, execution_result):
        """CommandExecutor persists command and ACK state; this hook records a system log."""
        self.repository_registry.system_logs.insert({
            "level": "INFO" if execution_result.success else "ERROR",
            "module": "SystemOrchestrator",
            "message": execution_result.message,
            "context_json": json.dumps(execution_result.details),
        })
    def _update_digital_twin(self, data, decision):
        """Update digital twin with latest data."""
        self.digital_twin.update_state({
            "sensor_data": data.to_dict(orient="records") if isinstance(data, pd.DataFrame) else data,
            "decision": decision
        })

    def _run_analytics(self):
        """Run analytics pipeline against the current repository state."""
        self.analytics_engine.refresh_from_repositories()
        return self.analytics_engine.get_summary(period_days=30)

    def _check_alerts(self):
        """Check for queued alert conditions after processing a packet."""
        return self.alert_manager.get_active_alerts() if hasattr(self.alert_manager, "get_active_alerts") else []

    def run(self) -> None:
        """Main LoRa receiver loop."""
        logger.info("=== LoRa Receiver Started ===")

        while True:
            try:
                raw_packet = self.lora_interface.receive_packet()

                if not raw_packet:
                    time.sleep(0.05)
                    continue

                self.process_inbound_packet(raw_packet)

                # Retry packets waiting for ACK
                self.gateway.retry_due_packets()

            except TimeoutError:
                # No packet received, continue listening
                continue

            except KeyboardInterrupt:
                raise

            except Exception as e:
                logger.exception("Receiver Loop Error: %s", e)
                time.sleep(0.2)

    def shutdown(self) -> None:
        """Gracefully shutdown all modules."""
        logger.info("=== Shutting down system ===")
        self.database_manager.stop()
        logger.info("=== Shutdown complete ===")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    orchestrator = SystemOrchestrator()

    try:
        orchestrator.run()

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user.")
        orchestrator.shutdown()
