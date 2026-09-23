# Model Audit Report

Audit date: 2026-07-03
Repository: `C:\Users\lenovo\al\AI-Smart-Irrigation-Digital-Twin`
Mode: final production model selection implemented.

## Final Answer

The model actually used by the production inference pipeline is:

`HYBRID TCN + LSTM MODEL/Models/best_model_v2.keras`

It is selected by:

1. `raspberry_pi/system_orchestrator.py` initializes `IrrigationPredictor(registry_dir=Path(__file__).parent / 'ai' / 'models', horizon_hours=[24])`.
2. `raspberry_pi/ai/models/predictor.py` loads active models through `ModelRegistry.get_model("all_targets", 24)`.
3. `raspberry_pi/ai/models/registry_metadata.json` has exactly one active entry for `all_targets_horizon_24`, with `model_type: hybrid_keras` and `artifact_path` / `model_path` pointing to `best_model_v2.keras`.
4. `raspberry_pi/ai/models/model_registry.py` loads `hybrid_keras` models through `KerasArtifactModel`, which calls `tf.keras.models.load_model(self.model_path)`.

Therefore the single production model is `best_model_v2.keras`.

## Model Artifact Inventory

| Artifact | Path | Size | Why It Exists | Training Or Inference | Active Or Unused | Classification |
|---|---|---:|---|---|---|---|
| `best_model_v2.keras` | `HYBRID TCN + LSTM MODEL/Models/best_model_v2.keras` | 7,240,386 bytes | Approved final primary production Hybrid TCN + LSTM model and the only active registry artifact. | Inference | Active | Production |
| `FINAL_TCN_LSTM_MODEL.keras` | `HYBRID TCN + LSTM MODEL/Models/FINAL_TCN_LSTM_MODEL.keras` | 7,240,127 bytes | Archived backup model retained for recovery/reference only. It is not selected by the production registry. | Backup/reference | Unused by production | Archived Backup |
| `tcn_lstm_research_final.keras` | `HYBRID TCN + LSTM MODEL/Models/tcn_lstm_research_final.keras` | 7,240,386 bytes | Archived research backup model retained outside normal production inference. | Backup/reference | Unused by production | Archived Backup |
| `tcn_lstm_final.keras` | `HYBRID TCN + LSTM MODEL/Models/tcn_lstm_final.keras` | 1,593,917 bytes | Legacy fallback artifact with a different input shape; not used during normal execution. | Legacy fallback only if explicitly required | Unused by production | Legacy |
| `fertilizer_model.pkl` | `HYBRID TCN + LSTM MODEL/Models/fertilizer_model.pkl` | 1,780,268,545 bytes | Fertilizer recommendation model artifact. It is separate from the irrigation prediction engine and must not be used by irrigation inference. | Fertilizer module only | Unused by irrigation production | Fertilizer Model |

No `.h5`, `.pt`, `.pth`, `.onnx`, or `.joblib` model artifact files were found in the repository inventory. `.h5` appears only as a checkpoint path pattern in training/model-registry code.

## Production Inference Chain

| File Path | Occurrence | Why It Is Used | Training Or Inference | Active Or Unused | Production Or Legacy |
|---|---|---|---|---|---|
| `raspberry_pi/system_orchestrator.py` | `IrrigationPredictor(...)`, `_run_ai_prediction(...)`, `model_name: HybridTCNLSTM` | Main runtime orchestrator initializes the production predictor and calls it for soil moisture, irrigation need, and water requirement. It does not hard-code a model artifact path. | Inference | Active | Production |
| `raspberry_pi/ai/models/registry_metadata.json` | `best_model_v2.keras`, `model_type: hybrid_keras`, `is_active: true` | Active registry metadata selecting the only production artifact. | Inference config | Active | Production |
| `raspberry_pi/ai/models/model_registry.py` | `KerasArtifactModel`, `tf.keras.models.load_model(self.model_path)`, `hybrid_keras` branch | Loads the active full `.keras` artifact selected by registry metadata. | Inference loader | Active | Production |
| `raspberry_pi/ai/models/predictor.py` | `IrrigationPredictor`, `_load_models()`, `get_model("all_targets", horizon)` | Loads registry models and serves prediction APIs used by orchestrator and inference pipeline. | Inference | Active | Production |
| `raspberry_pi/ai/models/inference.py` | `InferencePipeline`, `IrrigationPredictor(registry_dir)`, `predict(...)` | Secondary end-to-end inference service using the same predictor/registry mechanism; also loads normalizer pickle if provided. | Inference | Available, not directly called by orchestrator | Production-capable |

## Verified Project Areas

| Area | Result |
|---|---|
| AI Registry | Uses exactly one active model: `best_model_v2.keras`. |
| Predictor | Registry-driven; no hard-coded model artifact path. |
| Decision Engine | Consumes `AIPrediction`; does not load model artifacts. |
| System Orchestrator | Constructs `IrrigationPredictor` from registry directory; no direct model artifact path. |
| Dashboard | No production model artifact path found; UI labels remain generic Hybrid TCN + LSTM text. |
| Digital Twin | No production model artifact path found; digital twin pickle usage is state restore, not AI model loading. |
| Model Loader | Generic Keras loader loads the registry-selected `.keras` model. |
| Configuration Files | Production registry points only to `best_model_v2.keras`. |
| Deployment Scripts | No hard-coded production model artifact path found outside generated report text. |
| Docker | No hard-coded production model artifact path found. |
| Raspberry Pi Startup | No hard-coded production model artifact path found. |

## Training And Model-Class Code

| File Path | Occurrence | Why It Is Used | Training Or Inference | Active Or Unused | Production Or Legacy |
|---|---|---|---|---|---|
| `raspberry_pi/ai/models/hybrid_model.py` | TensorFlow/Keras imports, `HybridTCNLSTMModel`, `TCNBlock`, LSTM branch, `save_weights`, `load_weights` | Defines trainable hybrid TCN + LSTM architecture and weight-loading path for registry entries of `model_type: hybrid`. | Training and legacy weight inference support | Not selected by current active registry entry | Production architecture code / inactive for current artifact |
| `raspberry_pi/ai/models/tcn_model.py` | TensorFlow/Keras imports, `TCNModel`, `ModelCheckpoint`, `.h5` save/load weights | Standalone TCN model implementation and checkpointing. | Training / model development | Not used by active production registry | Training Artifact |
| `raspberry_pi/ai/models/lstm_model.py` | TensorFlow/Keras imports, `LSTMModel`, `ModelCheckpoint`, `.h5` save/load weights | Standalone LSTM model implementation and checkpointing. | Training / model development | Not used by active production registry | Training Artifact |
| `raspberry_pi/ai/models/trainer.py` | `HybridTCNLSTMModel`, `XGBoostFallbackModel`, checkpoint path `hybrid_horizon_{horizon}.h5`, `register_model(...)` | Training pipeline for creating and registering hybrid and XGBoost fallback models. | Training | Not active during production inference unless explicitly run | Training Artifact |
| `raspberry_pi/ai/models/model_registry.py` | `register_model`, `save_weights(... .h5)`, `model.load_weights(model.h5)`, `XGBoostFallbackModel().load(model.pkl)` | Supports multiple registry model types. The active metadata uses only `hybrid_keras`; other branches are inactive unless metadata changes. | Training registry + inference loader | Hybrid `.keras` branch active; `.h5`/XGBoost branches inactive | Production loader with inactive legacy branches |
| `raspberry_pi/ai/models/xgboost_fallback.py` | `import xgboost`, `XGBoostFallbackModel`, `pickle.load(f)` | Defines XGBoost fallback model and pickle serialization. No active XGBoost entry exists in registry metadata. | Training/fallback inference support | Unused by current production registry | Unused fallback / Training Artifact |

## Pickle / Non-Keras Loader Audit

| File Path | Occurrence | Why It Is Used | Training Or Inference | Active Or Unused | Production Or Legacy |
|---|---|---|---|---|---|
| `raspberry_pi/ai/models/inference.py` | `pickle.load(f)` in `load_normalizer()` | Loads scaler/normalizer metadata, not a predictive model. | Inference preprocessing | Optional | Production support |
| `raspberry_pi/ai/models/xgboost_fallback.py` | `pickle.load(f)` | Loads serialized XGBoost fallback model. No active registry entry points to an XGBoost `.pkl`. | Fallback inference support | Unused by current production pipeline | Unused fallback |
| `raspberry_pi/digital_twin/state_manager.py` | `state_*.pkl`, `pickle.load(f)` | Loads saved digital twin state snapshots, not an AI model. | Digital twin state restore | Active if state restore is called | Production support, not model inference |
| `HYBRID TCN + LSTM MODEL/Models/fertilizer_model.pkl` | artifact file | Fertilizer recommendation model, not irrigation inference. | Fertilizer module only | Unused by irrigation production | Fertilizer Model |

No `torch.load()` usage was found. No PyTorch model artifact was found. No `joblib.load()` usage was found in non-notebook production code.

## Notebook Audit

All notebooks are under the reference-only project: `HYBRID TCN + LSTM MODEL/Notebooks`. They are not imported by the Raspberry Pi production runtime.

| Notebook | Occurrences | Why It Is Used | Training Or Inference | Active Or Unused | Classification |
|---|---|---|---|---|---|
| `04_Decision_Engine.ipynb` | TCN mentions in code cells 10-13 | Reference decision-engine notebook mentioning TCN data/model context. | Reference experimentation | Unused by production | Reference |
| `05_Weather_Integration.ipynb` | TCN mentions in code cells 8-11 | Reference weather integration notebook. | Reference experimentation | Unused by production | Reference |
| `06_Motor_Automation.ipynb` | TCN mention in code cell 9 | Reference automation notebook. | Reference experimentation | Unused by production | Reference |
| `07_Water_Analytics.ipynb` | TCN mention in code cell 7 | Reference analytics notebook. | Reference experimentation | Unused by production | Reference |
| `08_NPK_Recommendation.ipynb` | TCN mentions; RandomForest cells; `.pkl`; `best_model_v2.keras` and `fertilizer_model.pkl` | Reference NPK/fertilizer notebook; includes fertilizer model work and model-file checks. | Training/reference | Unused by production runtime | Reference / Training Artifact |
| `09_Crop_Recommendation.ipynb` | TCN mentions in cells 2, 4 | Reference crop recommendation notebook. | Reference experimentation | Unused by production | Reference |
| `10_Anomaly_Detection.ipynb` | TCN mentions; includes IsolationForest in source output context | Reference anomaly notebook. | Reference experimentation | Unused by production | Reference |
| `11_Digital_Twin.ipynb` | TCN mention in cell 5 | Reference digital twin notebook. | Reference experimentation | Unused by production | Reference |
| `12_Final_System_Test.ipynb` | TCN/LSTM mentions in many cells | Reference final system notebook. | Reference validation | Unused by production | Reference |
| `13_Real_Time_Data_Pipeline.ipynb` and `(1)` | TCN mentions | Reference data pipeline notebooks. | Reference experimentation | Unused by production | Reference |
| `17_Dashboard.ipynb` | TCN mention | Reference dashboard notebook. | Reference experimentation | Unused by production | Reference |
| `19_Digital_Twin_Advanced.ipynb` | TCN mentions | Reference advanced digital twin notebook. | Reference experimentation | Unused by production | Reference |
| `20_Research_Paper_Assets.ipynb` | TCN mentions | Research asset notebook. | Reference/research | Unused by production | Reference |
| `21_Final_Research_System.ipynb` | TCN mention | Research system notebook. | Reference/research | Unused by production | Reference |
| `plant-health-prediction-with-ml.ipynb` in `Models` folder | classical ML notebook content found in broad artifact inventory | Plant health reference notebook, not production irrigation inference. | Reference/training | Unused by production | Reference |

## Classification Of Multiple Models

Exactly one production model is identified:

- Production: `best_model_v2.keras`

Every other model artifact is non-production:

- Archived Backup: `FINAL_TCN_LSTM_MODEL.keras`
- Archived Backup: `tcn_lstm_research_final.keras`
- Legacy: `tcn_lstm_final.keras`
- Fertilizer Model: `fertilizer_model.pkl`
- Reference notebook: `plant-health-prediction-with-ml.ipynb`

## Remaining Software Blockers

No remaining software blocker was found for model selection. Runtime/hardware validation is still required on the target Raspberry Pi/TensorFlow environment to confirm live feature shape and hardware execution.
