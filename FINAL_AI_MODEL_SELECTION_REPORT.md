# Final AI Model Selection Report

Date: 2026-07-03
Repository: `C:\Users\lenovo\al\AI-Smart-Irrigation-Digital-Twin`

## Production Model

`best_model_v2.keras` is the only primary production AI model.

Production registry entry:

- File: `raspberry_pi/ai/models/registry_metadata.json`
- Target: `all_targets`
- Horizon: `24`
- Model type: `hybrid_keras`
- Active artifact: `HYBRID TCN + LSTM MODEL/Models/best_model_v2.keras`
- Runtime loader: `raspberry_pi/ai/models/model_registry.py` via `KerasArtifactModel`
- Runtime predictor: `raspberry_pi/ai/models/predictor.py` via `IrrigationPredictor`
- Runtime orchestrator: `raspberry_pi/system_orchestrator.py`

## Backup Models

- `FINAL_TCN_LSTM_MODEL.keras` is an archived backup only. It is not used for production inference.
- `tcn_lstm_research_final.keras` is an archived research backup only. It is not used for production inference.

## Legacy Models

- `tcn_lstm_final.keras` is a legacy fallback artifact only if explicitly required. It is not used in normal execution because it uses a different input shape.

## Fertilizer Model

- `fertilizer_model.pkl` belongs only to the Fertilizer Recommendation module/reference workflow.
- It is separate from the irrigation prediction engine.
- It is not registered in `raspberry_pi/ai/models/registry_metadata.json` and must never be used by irrigation inference.

## Files Updated

- `raspberry_pi/ai/models/registry_metadata.json`
- `MODEL_AUDIT_REPORT.md`
- `FINAL_AI_MODEL_SELECTION_REPORT.md`
- `BUG_FIX_REPORT.md`
- `PROJECT_HEALTH_REPORT.md`
- `SOFTWARE_COMPLETENESS_REPORT.md`
- `FINAL_PROJECT_VERIFICATION.md`

## Verified Areas

| Area | Verification Result |
|---|---|
| AI Registry | Exactly one active production entry, `best_model_v2.keras`. |
| Predictor | Uses registry lookup; no hard-coded artifact path found. |
| Decision Engine | Consumes predictions only; no model artifact load found. |
| System Orchestrator | Uses `IrrigationPredictor` with registry directory; no hard-coded artifact path found. |
| Dashboard | No hard-coded production model artifact path found. |
| Digital Twin | No irrigation model artifact path found; pickle use is state restore, not model inference. |
| Model Loader | Loads the registry-selected `.keras` artifact. |
| Configuration Files | Production registry references only `best_model_v2.keras`. |
| Deployment Scripts | No hard-coded production model artifact path found. |
| Docker | No hard-coded production model artifact path found. |
| Raspberry Pi Startup | No hard-coded production model artifact path found. |

## Remaining Software Blocker

None for production model selection.

Runtime/hardware validation remains required on the target deployment environment to confirm TensorFlow availability and live feature-shape compatibility.
