"""
Regional weather-based groundwater wetness predictor.

This is INTENTIONALLY SEPARATE from the sensor pipeline (system_orchestrator.py
/ feature_engineering.py). It does not touch, replace, or depend on the
NPK/soil sensor data path in any way.

What it does:
    - Pulls the last ~40 days of NASA POWER daily weather for a fixed
      location (Varanasi, by default) -- no LoRa sensor involved.
    - Reconstructs the exact 22-feature vector the GA_Optimized_Hybrid.keras
      model was trained on (see the training notebook, cell 28).
    - Predicts GWETTOP (surface wetness) and GWETROOT (root-zone wetness)
      for the most recent day.

How it's meant to be used:
    This should run on a SCHEDULE (e.g. once a day, since NASA POWER data is
    daily resolution) -- not per incoming LoRa packet. Call
    WeatherPredictor.predict_regional_wetness() from a daily cron job or a
    simple time-based check in your main loop, and feed the result into the
    Decision Engine as a secondary/contextual signal alongside (not instead
    of) the sensor-based prediction.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

import joblib
import numpy as np
import pandas as pd
import requests
from tensorflow.keras.models import load_model

try:
    from tcn import TCN
except ImportError:  # pragma: no cover
    TCN = None

logger = logging.getLogger(__name__)


class WeatherPredictor:
    """Predicts regional groundwater surface/root-zone wetness from NASA
    POWER weather data using the GA_Optimized_Hybrid TCN-LSTM model.
    """

    NASA_PARAMS = (
        "T2M,T2M_MAX,T2M_MIN,T2MDEW,RH2M,PRECTOTCORR,WS2M,PS,"
        "ALLSKY_SFC_SW_DWN,EVLAND,GWETROOT,GWETTOP"
    )
    TIME_STEPS = 30  # must match training (create_sequences window size)

    # Exact feature order the model was trained on (training notebook, cell 28)
    FEATURE_ORDER = [
        "T2M", "T2M_MAX", "T2M_MIN", "T2MDEW", "RH2M", "PRECTOTCORR",
        "WS2M", "PS", "ALLSKY_SFC_SW_DWN", "EVLAND",
        "TEMP_RANGE", "DAY_OF_YEAR", "MONTH", "YEAR",
        "RAIN_3D", "RAIN_7D", "TEMP_7D", "RH_7D",
        "GWETROOT_LAG1", "GWETTOP_LAG1", "RAIN_LAG1",
        "CITY_ID",
    ]

    def __init__(
        self,
        model_dir: str,
        city_name: str = "Varanasi",
        latitude: float = 25.3176,
        longitude: float = 82.9739,
    ):
        self.city_name = city_name
        self.latitude = latitude
        self.longitude = longitude
        self.model_dir = Path(model_dir)

        self._model = None
        self._feature_scaler = None
        self._target_scaler = None
        self._label_encoder = None
        self._city_id: Optional[int] = None

    def load(self) -> None:
        """Load the model + scalers + label encoder. Call once at startup."""
        custom_objects = {"TCN": TCN} if TCN is not None else {}

        self._model = load_model(
            self.model_dir / "GA_Optimized_Hybrid.keras",
            custom_objects=custom_objects,
            compile=False,
        )
        self._feature_scaler = joblib.load(self.model_dir / "feature_scaler.pkl")
        self._target_scaler = joblib.load(self.model_dir / "target_scaler.pkl")
        self._label_encoder = joblib.load(self.model_dir / "label_encoder.pkl")

        try:
            self._city_id = int(self._label_encoder.transform([self.city_name])[0])
        except ValueError as exc:
            raise ValueError(
                f"'{self.city_name}' was not one of the cities this model "
                f"was trained on. Known cities: "
                f"{list(self._label_encoder.classes_)}"
            ) from exc

        logger.info(
            "WeatherPredictor loaded for %s (CITY_ID=%d)",
            self.city_name, self._city_id
        )

    def _fetch_nasa_power(self, days: int = 45) -> pd.DataFrame:
        """Fetch the last `days` days of NASA POWER daily data for this location."""
        end = datetime.utcnow().date()
        start = end - timedelta(days=days)

        url = "https://power.larc.nasa.gov/api/temporal/daily/point"
        params = {
            "parameters": self.NASA_PARAMS,
            "community": "AG",
            "longitude": self.longitude,
            "latitude": self.latitude,
            "start": start.strftime("%Y%m%d"),
            "end": end.strftime("%Y%m%d"),
            "format": "JSON",
        }
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()["properties"]["parameter"]

        dfs = [
            pd.DataFrame.from_dict(values, orient="index", columns=[param])
            for param, values in data.items()
        ]
        df = pd.concat(dfs, axis=1)
        df.index = pd.to_datetime(df.index, format="%Y%m%d")
        df.index.name = "date"
        df = df.sort_index().reset_index()

        # NASA uses -999 as a missing-value sentinel
        df.replace(-999, np.nan, inplace=True)
        df.ffill(inplace=True)
        df.bfill(inplace=True)
        return df

    def _build_feature_row(self, df: pd.DataFrame) -> pd.DataFrame:
        """Recreate the exact derived features from the training notebook
        (cells 21-23) on top of the raw NASA POWER pull."""
        df = df.copy()
        df["TEMP_RANGE"] = df["T2M_MAX"] - df["T2M_MIN"]
        df["DAY_OF_YEAR"] = df["date"].dt.dayofyear
        df["MONTH"] = df["date"].dt.month
        df["YEAR"] = df["date"].dt.year

        df["RAIN_3D"] = df["PRECTOTCORR"].rolling(3, min_periods=1).sum()
        df["RAIN_7D"] = df["PRECTOTCORR"].rolling(7, min_periods=1).sum()
        df["TEMP_7D"] = df["T2M"].rolling(7, min_periods=1).mean()
        df["RH_7D"] = df["RH2M"].rolling(7, min_periods=1).mean()

        df["GWETROOT_LAG1"] = df["GWETROOT"].shift(1)
        df["GWETTOP_LAG1"] = df["GWETTOP"].shift(1)
        df["RAIN_LAG1"] = df["PRECTOTCORR"].shift(1)

        df["CITY_ID"] = self._city_id

        df.bfill(inplace=True)
        df.ffill(inplace=True)
        return df

    def predict_regional_wetness(self) -> Dict[str, float]:
        """Fetch latest weather, build the 30x22 sequence, and predict
        GWETTOP / GWETROOT for the most recent day. Returns a plain dict --
        call this once a day, not per LoRa packet.
        """
        if self._model is None:
            self.load()

        raw = self._fetch_nasa_power(days=45)
        featured = self._build_feature_row(raw)

        if len(featured) < self.TIME_STEPS:
            raise ValueError(
                f"Not enough NASA POWER history yet: got {len(featured)} "
                f"days, need at least {self.TIME_STEPS}"
            )

        window = featured[self.FEATURE_ORDER].tail(self.TIME_STEPS)
        x_scaled = self._feature_scaler.transform(window)
        x_seq = x_scaled.reshape(1, self.TIME_STEPS, len(self.FEATURE_ORDER))

        pred_scaled = self._model.predict(x_seq, verbose=0)
        pred = self._target_scaler.inverse_transform(pred_scaled)[0]

        result = {
            "city": self.city_name,
            "gwettop_surface_wetness": float(pred[0]),
            "gwetroot_zone_wetness": float(pred[1]),
            "predicted_for_date": featured["date"].iloc[-1].strftime("%Y-%m-%d"),
        }
        logger.info("Regional wetness prediction: %s", result)
        return result


if __name__ == "__main__":
    # Quick manual test: python weather_predictor.py
    logging.basicConfig(level=logging.INFO)
    predictor = WeatherPredictor(
        model_dir="HYBRID TCN + LSTM MODEL/Models",
        city_name="Varanasi",
        latitude=25.3176,
        longitude=82.9739,
    )
    print(predictor.predict_regional_wetness())
