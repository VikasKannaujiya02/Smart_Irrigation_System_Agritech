"""
Continuous learning + rain-gated irrigation decision.

This is a SEPARATE, ADD-ON module. It does not modify system_orchestrator.py,
feature_engineering.py, or anything already working -- it's meant to be
wired in as two small optional calls once you're ready:

  1. DataLogger.log_reading(...)   -- call this every time the 8-feature
     window gets a new row (in _update_feature_window). It just appends to
     a CSV -- harmless, doesn't affect the live buffer or predictions.

  2. ContinuousTrainer.maybe_retrain()  -- call this periodically (e.g. once
     a day, or every N new logged readings). It fine-tunes the EXISTING
     irrigation model on the newly collected real data for a few epochs,
     and saves a new .keras file + bumps registry_metadata.json. This is
     "incremental learning", not a full retrain from scratch -- fast, and
     the model gets a little more tailored to your actual field over time.

  3. RainGate.should_suppress_irrigation(...) -- call this right before
     sending a MOTOR_ON command. If a rain-forecast model says rain is
     likely in the next 6h-7d, this returns True and the command should be
     changed to OFF regardless of what the soil/irrigation model said.
     Requires the separately-trained rain_forecast_tcn_lstm.keras (Model B
     from the training notebook) -- if you haven't trained/deployed that
     yet, RainGate.should_suppress_irrigation() just returns False (no
     rain data => don't block irrigation on a guess).
"""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import joblib

try:
    from raspberry_pi.ai.models.gat_tcn_lstm import FinalPyTorchModel
except ImportError:
    FinalPyTorchModel = None

logger = logging.getLogger(__name__)


class DataLogger:
    """Appends every real 8-feature reading (with a label filled in later,
    or none yet) to a CSV so it accumulates into genuine field-training data.
    """

    FEATURE_ORDER = [
        "node_1_soil_moisture", "node_2_soil_moisture", "temperature",
        "humidity", "rainfall", "wind_speed", "solar_radiation",
    ]

    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path)
        if not self.csv_path.exists():
            self.csv_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp"] + self.FEATURE_ORDER)

    def log_reading(self, latest_sensor_state: Dict[str, float]) -> None:
        row = [datetime.utcnow().isoformat()] + [
            latest_sensor_state.get(key, 0.0) for key in self.FEATURE_ORDER
        ]
        with open(self.csv_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(row)

    def count_rows(self) -> int:
        if not self.csv_path.exists():
            return 0
        with open(self.csv_path) as f:
            return sum(1 for _ in f) - 1  # minus header


class ContinuousTrainer:
    """Periodically fine-tunes the existing irrigation model on newly
    collected real field data. This is incremental (a few epochs on top of
    the current weights), not a from-scratch retrain -- quick, and keeps
    the model improving as real data accumulates.
    """

    WINDOW = 24
    HORIZONS = [240, 1440, 2880, 5760, 40320]  # Exact targets from model (1, 6, 12, 24, 168 hours in 15s steps)

    def __init__(
        self,
        csv_path: str,
        model_path: str,
        scaler_path: str,
        retrain_every_n_new_rows: int = 200,
        fine_tune_epochs: int = 5,
    ):
        self.csv_path = Path(csv_path)
        self.model_path = Path(model_path)
        self.scaler_path = Path(scaler_path)
        self.retrain_every_n_new_rows = retrain_every_n_new_rows
        self.fine_tune_epochs = fine_tune_epochs
        self._rows_at_last_retrain = 0

    def _load_rows(self) -> np.ndarray:
        import pandas as pd
        df = pd.read_csv(self.csv_path)
        return df[DataLogger.FEATURE_ORDER].to_numpy(dtype=np.float32)

    def _build_sequences(self, data: np.ndarray):
        X, y = [], []
        # Max horizon is 40320 steps (7 days in 15s intervals)
        max_hz = max(self.HORIZONS)
        for i in range(len(data) - max_hz - self.WINDOW):
            X.append(data[i:i + self.WINDOW])
            # targets: node 1 (idx 0) and node 2 (idx 1) for each horizon
            t_vals = []
            for hz in self.HORIZONS:
                t_vals.extend(data[i + self.WINDOW + hz, [0, 1]])
            y.append(t_vals)
        return np.array(X), np.array(y)

    def maybe_retrain(self) -> bool:
        """Call this periodically (e.g. once a day). Returns True if a
        fine-tune actually ran, False if not enough new data yet.
        """
        current_rows = DataLogger(str(self.csv_path)).count_rows()
        new_rows = current_rows - self._rows_at_last_retrain

        if new_rows < self.retrain_every_n_new_rows:
            logger.info(
                "Continuous learning: %d new readings since last retrain "
                "(need %d) -- skipping for now",
                new_rows, self.retrain_every_n_new_rows
            )
            return False

        if current_rows < self.WINDOW + 10:
            logger.info("Continuous learning: not enough total data yet (%d rows)", current_rows)
            return False

        if FinalPyTorchModel is None:
            logger.warning("Continuous learning: PyTorch Model class not found, skipping")
            return False

        logger.info("Continuous learning: loading data...")
        data = self._load_rows()
        X, y = self._build_sequences(data)
        if len(X) == 0:
            logger.info("Continuous learning: not enough sequences yet (max horizon needs ~7 days data)")
            return False

        if X.shape[-1] != 7:
            logger.warning("Continuous learning skipped: model expects 7 features, got %s", X.shape[-1])
            self._rows_at_last_retrain = current_rows
            return False

        logger.info("Continuous learning: fine-tuning on %d real readings...", current_rows)
        # Load scaler
        scaler = joblib.load(self.scaler_path)
        X_scaled = np.array([scaler.transform(w) for w in X])
        
        # Load PyTorch Model
        model = FinalPyTorchModel()
        model.load_state_dict(torch.load(self.model_path, weights_only=False))
        model.train()
        
        train_loader = DataLoader(
            TensorDataset(torch.tensor(X_scaled, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)), 
            batch_size=16, shuffle=True
        )
        
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
        criterion = nn.MSELoss()
        
        for _ in range(self.fine_tune_epochs):
            for batch_x, batch_y in train_loader:
                optimizer.zero_grad()
                out = model(batch_x)
                loss = criterion(out, batch_y)
                loss.backward()
                optimizer.step()

        torch.save(model.state_dict(), self.model_path)
        self._rows_at_last_retrain = current_rows
        logger.info("Continuous learning: fine-tune complete, model updated in place")
        return True


class RainGate:
    """Checks a separately-trained rain-forecast model (Model B from the
    training notebook) before allowing a MOTOR_ON command. If rain is
    likely within the given horizons, irrigation is suppressed to save
    water. If no rain model is configured/available, this never blocks
    irrigation (fails open, not closed).
    """

    def __init__(self, rain_model_path: Optional[str] = None, rain_probability_threshold: float = 0.5):
        self.rain_model_path = Path(rain_model_path) if rain_model_path else None
        self.threshold = rain_probability_threshold
        self._model = None

    def _load(self):
        if self._model is not None or self.rain_model_path is None or load_model is None:
            return
        if not self.rain_model_path.exists():
            logger.info("RainGate: no rain-forecast model found at %s, gate disabled", self.rain_model_path)
            return
        custom_objects = {"TCN": TCN} if TCN is not None else {}
        self._model = load_model(self.rain_model_path, custom_objects=custom_objects, compile=False)
        logger.info("RainGate: rain-forecast model loaded")

    def should_suppress_irrigation(self, weather_window: np.ndarray, city_id: int) -> bool:
        """weather_window: shape (1, WINDOW_B, n_weather_features), matching
        how rain_forecast_tcn_lstm.keras was trained (see the earlier
        Model B notebook). Returns True if irrigation should be withheld.
        """
        self._load()
        if self._model is None:
            return False  # no rain model configured -- don't block on nothing

        city_arr = np.array([[city_id]])
        prob = float(self._model.predict([weather_window, city_arr], verbose=0)[0][0])
        suppress = prob >= self.threshold
        logger.info(
            "RainGate: rain probability=%.2f (threshold=%.2f) -> %s",
            prob, self.threshold, "SUPPRESS irrigation" if suppress else "allow irrigation"
        )
        return suppress
