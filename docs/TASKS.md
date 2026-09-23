# Project Tasks

## Completed Phase: Communication Foundation

Completed:

- Defined LoRa packet fields.
- Defined packet types.
- Defined command types.
- Implemented CRC-16/CCITT-FALSE utility.
- Implemented packet model.
- Implemented packet builder.
- Implemented packet parser.
- Implemented packet validator.
- Implemented ACK manager.
- Implemented retry manager.
- Implemented command manager.
- Implemented communication manager.
- Implemented serial transport abstraction.
- Implemented LoRa transport abstraction.
- Implemented gateway packet handler.
- Implemented gateway manager.
- Implemented device registry.
- Implemented heartbeat manager.
- Documented protocol workflow.

Not started in this phase:

- AI engine.
- Dashboard.
- Database persistence.
- Decision engine.

Next recommended task:

Add focused unit tests for CRC, packet build/parse round trip, validation, ACK matching, retry decisions, duplicate detection, and heartbeat timeout behavior.

## Completed Phase: Database Layer

Completed:

- Designed SQLite schema for required tables.
- Added `schema.sql`.
- Implemented automatic database creation.
- Implemented version migration.
- Implemented indexes.
- Implemented transaction context manager.
- Implemented SQLite connection pool.
- Implemented repository classes.
- Implemented query builder helpers.
- Implemented backup support.
- Implemented restore support.
- Implemented integrity checks.
- Implemented startup recovery from latest backup when integrity fails.
- Documented every database table.
- Added ER diagram documentation.

Not started in this phase:

- AI engine.
- Dashboard.
- Decision engine.

Next recommended task:

Add focused unit tests for migration, schema creation, repository inserts, transactions, rollback behavior, backup creation, restore, and integrity checks.

## Completed Phase: Sensor Node Firmware

Completed:

- Implemented config.h with protocol constants, pin definitions, and configuration parameters.
- Implemented packet_builder.h/cpp for packet building and parsing with CRC-16/CCITT-FALSE.
- Implemented lora_manager.h/cpp for LoRa SX1278 communication.
- Implemented sensor_manager.h/cpp for reading soil moisture, DHT22, and battery voltage.
- Implemented battery_manager.h/cpp for battery monitoring.
- Implemented power_manager.h/cpp for power management and watchdog.
- Implemented heartbeat.h/cpp for heartbeat functionality.
- Implemented sensor_node.ino main sketch with ACK handling, retries, periodic transmission, and sleep mode.

Not started in this phase:

- AI engine.
- Dashboard.
- Decision engine.

Next recommended task:

Implement pump controller firmware.

## Completed Phase: NPK Node Firmware

Completed:

- Implemented config.h with protocol constants, pin definitions, Modbus settings.
- Implemented packet_builder.h/cpp (reused from sensor node).
- Implemented lora_manager.h/cpp (reused from sensor node).
- Implemented modbus_manager.h/cpp for RS485 Modbus RTU communication.
- Implemented npk_sensor.h/cpp for reading NPK sensor (nitrogen, phosphorus, potassium, EC, pH, soil temperature, soil moisture.
- Implemented battery_manager.h/cpp (reused from sensor node).
- Implemented power_manager.h/cpp (reused from sensor node).
- Implemented heartbeat.h/cpp (reused from sensor node).
- Implemented npk_node.ino main sketch with ACK handling, retries, periodic transmission, and sleep mode.

Not started in this phase:

- AI engine.
- Dashboard.
- Decision engine.

Next recommended task:

Implement pump controller firmware.

## Completed Phase: Pump Controller Firmware

Completed:

- Implemented config.h with protocol constants, pin definitions, and configuration parameters.
- Implemented packet_builder.h/cpp (reused from sensor node).
- Implemented lora_manager.h/cpp (reused from sensor node).
- Implemented heartbeat.h/cpp (reused from sensor node).
- Implemented relay_manager.h/cpp for relay control, manual override, emergency stop, and diagnostics.
- Implemented failsafe.h/cpp for runtime protection and dry run protection.
- Implemented watchdog.h/cpp using ESP8266 Ticker for hardware watchdog reset.
- Implemented command_processor.h/cpp for handling gateway commands.
- Implemented pump_controller.ino main sketch with all features integrated.

Not started in this phase:

- AI engine.
- Dashboard.
- Decision engine.

Next recommended task:

Add focused unit tests for the pump controller firmware components.

## Completed Phase: Weather Integration Service

Completed:

- Implemented weather_provider.py with WeatherProvider abstract base class and concrete OpenWeatherMapProvider implementation.
- Implemented weather_cache.py for file-based weather data caching with TTL.
- Implemented rain_prediction.py with RainPredictor and IrrigationRecommendation logic.
- Implemented forecast_manager.py for managing forecast retrieval, caching, and validation.
- Implemented weather_service.py as the main service class with config loading.
- Created __init__.py for weather_api module exports.
- Updated configs/system.yaml with weather configuration settings.

Not started in this phase:

- AI engine.
- Dashboard.
- Decision engine.

Next recommended task:

Add focused unit tests for the weather integration components.

## Completed Phase: Data Processing Layer

Completed:

- Created data_processing directory and module.
- Implemented missing_value_handler.py for handling missing data.
- Implemented outlier_detection.py for detecting and handling outliers.
- Implemented normalization.py for normalizing features.
- Implemented cleaner.py for cleaning data (remove duplicates, sort, etc.).
- Implemented validator.py for validating sensor data (range checks, etc.).
- Implemented feature_engineering.py for generating features (time, rolling, weather, etc.).
- Updated requirements.txt with data processing dependencies.

Not started in this phase:

- AI engine.
- Dashboard.
- Decision engine.

Next recommended task:

Add focused unit tests for the data processing components.

## Completed Phase: AI Data Pipeline

Completed:

- Created raspberry_pi/ai/data_pipeline directory and module.
- Implemented dataset_builder.py for loading data from SQLite database.
- Implemented dataset_validator.py for validating merged datasets.
- Implemented dataset_cleaner.py for cleaning and preprocessing data.
- Implemented dataset_merger.py for merging sensor, NPK, pump, and weather data.
- Implemented feature_extractor.py for feature engineering.
- Implemented feature_selector.py for feature selection.
- Implemented sliding_window.py for creating time series sequences.
- Implemented normalizer.py for feature scaling.
- Implemented train_test_split.py for time series train/val/test splitting.
- Implemented dataset_version_manager.py for dataset versioning and storage.
- Created __init__.py exporting all pipeline components.

Not started in this phase:

- AI engine.
- Dashboard.
- Decision engine.

Next recommended task:

Add focused unit tests for the AI Prediction Engine components.

## Completed Phase: AI Prediction Engine

Completed:
- Created `ai/models` directory and module structure
- Implemented `tcn_model.py`: Temporal Convolutional Network model for time series prediction
- Implemented `lstm_model.py`: Long Short-Term Memory model
- Implemented `hybrid_model.py`: Combined TCN+LSTM hybrid model (primary model)
- Implemented `xgboost_fallback.py`: XGBoost fallback model for low-confidence predictions
- Implemented `metrics.py`: Evaluation metrics (MAE, MSE, RMSE, MAPE, R²)
- Implemented `confidence_estimator.py`: Estimates prediction confidence and triggers fallback
- Implemented `model_registry.py`: Model versioning and management system
- Implemented `trainer.py`: Training pipeline with early stopping, checkpointing
- Implemented `predictor.py`: Prediction interface with automatic fallback
- Implemented `inference.py`: End-to-end inference pipeline
- Updated `requirements.txt` with TensorFlow, XGBoost, scikit-learn, scipy
- Updated `docs/TASKS.md` to mark phase as complete

Prediction Targets:
- Future Soil Moisture
- Future Irrigation Need
- Water Requirement

Prediction Horizons:
- 1 Hour
- 6 Hours
- 12 Hours
- 24 Hours
- 7 Days (168 Hours)

Key Features:
- Hybrid TCN+LSTM as primary model
- XGBoost as fallback for low confidence
- Early stopping during training
- Model checkpointing
- Model versioning with registry
- Confidence-based fallback
- Multi-horizon prediction support

## Completed Phase: Decision Engine

Completed:
- Created decision_engine module structure
- Implemented core data models and enums for decision inputs/outputs
- Implemented MoistureRuleEngine (soil-moisture based decisions)
- Implemented WeatherRuleEngine (rain/humidity based decisions)
- Implemented AIRuleEngine (AI prediction based decisions)
- Implemented CropRuleEngine (crop preference based decisions)
- Implemented WaterRequirementEngine (calculates water volume/duration)
- Implemented IrrigationScheduler (schedules irrigation at optimal times)
- Implemented PumpControllerLogic (enforces safety constraints)
- Implemented main DecisionEngine orchestrator (combines all rules)
- Updated __init__.py files for module exports

Key Rules Implemented:
- Rain delay: if rain expected, keep motor off (unless emergency)
- AI confidence: switch to rule engine if confidence is low
- Sensor faults: ignore faulty sensor inputs
- Battery level: reduce communication if battery low (in config)
- Tank status: prevent pump from running if tank empty
- Emergency irrigation: override all delays if soil moisture critically low

Prediction Targets:
- Future Soil Moisture
- Future Irrigation Need
- Water Requirement
