# Deployment Checklist

## Completed Software Items

- [x] Register production Hybrid TCN + LSTM artifact path.
- [x] Wire orchestrator AI prediction to `IrrigationPredictor`.
- [x] Replace mock LoRa class with configured SX1278 serial transport.
- [x] Implement command send, ACK tracking, and command persistence.
- [x] Implement dashboard manual pump command through safety layer and command executor.
- [x] Implement repository-backed dashboard alert/config/history paths.
- [x] Implement analytics runtime hook and repository refresh.
- [x] Add adapters for README-only Raspberry Pi module folders.
- [x] Remove reported TODO/placeholder/NotImplemented blockers.
- [x] Run Python compile check with bundled runtime.

## Hardware / Runtime Validation Required

- [ ] Configure `SX1278_SERIAL_PORT` on Raspberry Pi.
- [ ] Verify SX1278 transmit/receive with real LoRa peer.
- [ ] Verify pump controller ACK round trip.
- [ ] Verify sensor node and NPK node live packets.
- [ ] Install target Python dependencies, including TensorFlow and pytest.
- [ ] Run pytest in Docker/Pi runtime.
- [ ] Validate registered `.keras` artifact input shape against live engineered features.
- [ ] Run frontend dependency install and production build in target CI/runtime.

Current decision: no remaining known software blockers from the generated reports; deployment is ready for hardware/runtime validation.
