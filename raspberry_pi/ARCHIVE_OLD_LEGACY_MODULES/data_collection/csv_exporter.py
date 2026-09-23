"""CSV side-output for live telemetry and prediction records."""

from __future__ import annotations

import csv
from pathlib import Path
from threading import Lock
from typing import Any


class LiveCSVExporter:
    """Append repository-ready records to per-source CSV files."""

    def __init__(self, output_dir: str | Path = "data/csv_exports") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def append_sensor_node(self, row: dict[str, Any]) -> None:
        self._append("sensor_node.csv", row)

    def append_npk_node(self, row: dict[str, Any]) -> None:
        self._append("npk_node.csv", row)

    def append_pump_controller(self, row: dict[str, Any]) -> None:
        self._append("pump_controller.csv", row)

    def append_ai_prediction(self, row: dict[str, Any]) -> None:
        self._append("ai_prediction_history.csv", row)

    def append_weather(self, row: dict[str, Any]) -> None:
        self._append("weather_history.csv", row)

    def _append(self, filename: str, row: dict[str, Any]) -> None:
        path = self.output_dir / filename
        fieldnames = list(row.keys())
        with self._lock:
            write_header = not path.exists() or path.stat().st_size == 0
            with path.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
                if write_header:
                    writer.writeheader()
                writer.writerow(row)
