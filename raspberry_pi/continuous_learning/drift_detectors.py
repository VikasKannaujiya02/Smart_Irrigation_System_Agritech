"""Drift detection for models, data, and sensors."""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum, auto
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


class DriftType(Enum):
    MODEL = auto()
    DATA = auto()
    SENSOR = auto()


class DriftSeverity(Enum):
    NONE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class DriftResult:
    """Result of a drift detection."""
    drift_type: DriftType
    severity: DriftSeverity
    is_detected: bool
    score: float
    timestamp: datetime
    details: Dict[str, Any]


class DriftDetector:
    """Base class for drift detectors."""

    def __init__(self, name: str, threshold: float = 0.5):
        self.name = name
        self.threshold = threshold
        self.history: List[DriftResult] = []

    def detect(self, *args, **kwargs) -> DriftResult:
        """Return a safe no-drift result for the base detector interface."""
        return self._record_result(DriftResult(
            drift_type=DriftType.DATA,
            severity=DriftSeverity.NONE,
            is_detected=False,
            score=0.0,
            timestamp=datetime.now(),
            details={"message": f"{self.name} base detector has no concrete drift signal"},
        ))

    def _record_result(self, result: DriftResult) -> DriftResult:
        self.history.append(result)
        if len(self.history) > 1000:
            self.history.pop(0)
        return result


class ModelDriftDetector(DriftDetector):
    """Detector for model performance drift."""

    def __init__(
        self, 
        threshold: float = 0.3,
        metric: str = "mae"
    ):
        super().__init__("ModelDriftDetector", threshold)
        self.metric = metric
        self.baseline_metrics: Dict[str, float] = {}
        self.recent_metrics: List[Dict[str, float]] = []

    def set_baseline(self, metrics: Dict[str, float]) -> None:
        self.baseline_metrics = metrics.copy()
        logger.info(f"Model drift baseline set: {metrics}")

    def add_recent_metric(self, metrics: Dict[str, float]) -> None:
        self.recent_metrics.append(metrics)
        if len(self.recent_metrics) > 50:
            self.recent_metrics.pop(0)

    def detect(self, current_metrics: Optional[Dict[str, float]] = None) -> DriftResult:
        metrics = current_metrics or self.recent_metrics[-1] if self.recent_metrics else None
        
        if not metrics or not self.baseline_metrics:
            return self._record_result(DriftResult(
                drift_type=DriftType.MODEL,
                severity=DriftSeverity.NONE,
                is_detected=False,
                score=0.0,
                timestamp=datetime.now(),
                details={"message": "Insufficient data for drift detection"}
            ))

        # Calculate drift score
        drift_score = 0.0
        if self.metric in metrics and self.metric in self.baseline_metrics:
            base_val = self.baseline_metrics[self.metric]
            curr_val = metrics[self.metric]
            if base_val > 0:
                drift_score = abs((curr_val - base_val) / base_val)
            else:
                drift_score = abs(curr_val - base_val)

        # Determine severity
        severity = DriftSeverity.NONE
        if drift_score > self.threshold * 2:
            severity = DriftSeverity.CRITICAL
        elif drift_score > self.threshold * 1.5:
            severity = DriftSeverity.HIGH
        elif drift_score > self.threshold:
            severity = DriftSeverity.MEDIUM
        elif drift_score > self.threshold * 0.5:
            severity = DriftSeverity.LOW

        logger.info(f"Model drift detection score: {drift_score:.3f}, severity: {severity.name}")

        return self._record_result(DriftResult(
            drift_type=DriftType.MODEL,
            severity=severity,
            is_detected=drift_score > self.threshold,
            score=drift_score,
            timestamp=datetime.now(),
            details={
                "baseline": self.baseline_metrics,
                "current": metrics,
                "metric_used": self.metric
            }
        ))


class DataDriftDetector(DriftDetector):
    """Detector for data distribution drift."""

    def __init__(
        self,
        threshold: float = 0.2,
        method: str = "ks"
    ):
        super().__init__("DataDriftDetector", threshold)
        self.method = method
        self.baseline_stats: Dict[str, Dict[str, float]] = {}

    def set_baseline_stats(self, stats: Dict[str, Dict[str, float]]) -> None:
        self.baseline_stats = stats.copy()
        logger.info("Data drift baseline statistics set")

    def detect(
        self, 
        current_stats: Dict[str, Dict[str, float]]
    ) -> DriftResult:
        if not self.baseline_stats:
            return self._record_result(DriftResult(
                drift_type=DriftType.DATA,
                severity=DriftSeverity.NONE,
                is_detected=False,
                score=0.0,
                timestamp=datetime.now(),
                details={"message": "No baseline set for data drift detection"}
            ))

        # Calculate drift score for each feature
        total_score = 0.0
        feature_count = 0
        drift_details: Dict[str, Any] = {}

        for feature, base_stats in self.baseline_stats.items():
            if feature in current_stats:
                curr_stats = current_stats[feature]
                if "mean" in base_stats and "mean" in curr_stats:
                    # Simple mean-based drift score
                    base_mean = base_stats["mean"]
                    curr_mean = curr_stats["mean"]
                    base_std = base_stats.get("std", 1.0)
                    
                    if base_std > 0:
                        score = abs((curr_mean - base_mean) / base_std)
                        total_score += score
                        feature_count += 1
                        drift_details[feature] = {
                            "baseline_mean": base_mean,
                            "current_mean": curr_mean,
                            "score": score
                        }

        avg_score = total_score / max(feature_count, 1)

        severity = DriftSeverity.NONE
        if avg_score > self.threshold * 2:
            severity = DriftSeverity.CRITICAL
        elif avg_score > self.threshold * 1.5:
            severity = DriftSeverity.HIGH
        elif avg_score > self.threshold:
            severity = DriftSeverity.MEDIUM
        elif avg_score > self.threshold * 0.5:
            severity = DriftSeverity.LOW

        logger.info(f"Data drift detection: score {avg_score:.3f}, severity {severity.name}")

        return self._record_result(DriftResult(
            drift_type=DriftType.DATA,
            severity=severity,
            is_detected=avg_score > self.threshold,
            score=avg_score,
            timestamp=datetime.now(),
            details=drift_details
        ))


class SensorDriftDetector(DriftDetector):
    """Detector for individual sensor drift."""

    def __init__(
        self,
        threshold: float = 0.4
    ):
        super().__init__("SensorDriftDetector", threshold)
        self.sensor_baselines: Dict[str, Dict[str, float]] = {}
        self.sensor_measurements: Dict[str, List[float]] = {}

    def register_sensor(
        self, 
        sensor_id: str, 
        min_val: Optional[float] = None, 
        max_val: Optional[float] = None, 
        mean_val: Optional[float] = None
    ) -> None:
        self.sensor_baselines[sensor_id] = {
            "min": min_val,
            "max": max_val,
            "mean": mean_val
        }
        self.sensor_measurements[sensor_id] = []
        logger.info(f"Registered sensor {sensor_id} for drift detection")

    def add_measurement(self, sensor_id: str, value: float) -> None:
        if sensor_id in self.sensor_measurements:
            self.sensor_measurements[sensor_id].append(value)
            if len(self.sensor_measurements[sensor_id]) > 100:
                self.sensor_measurements[sensor_id].pop(0)

    def detect(self, sensor_id: Optional[str] = None) -> DriftResult:
        if not sensor_id:
            all_scores = []
            all_severities = []
            all_details = {}

            for sid in self.sensor_baselines:
                res = self._detect_single_sensor(sid)
                all_scores.append(res.score)
                all_severities.append(res.severity)
                all_details[sid] = res.details

            max_severity = max(all_severities, key=lambda s: s.value) if all_severities else DriftSeverity.NONE
            avg_score = np.mean(all_scores) if all_scores else 0.0

            return self._record_result(DriftResult(
                drift_type=DriftType.SENSOR,
                severity=max_severity,
                is_detected=avg_score > self.threshold,
                score=avg_score,
                timestamp=datetime.now(),
                details=all_details
            ))
        else:
            return self._detect_single_sensor(sensor_id)

    def _detect_single_sensor(self, sensor_id: str) -> DriftResult:
        if sensor_id not in self.sensor_baselines:
            return DriftResult(
                drift_type=DriftType.SENSOR,
                severity=DriftSeverity.NONE,
                is_detected=False,
                score=0.0,
                timestamp=datetime.now(),
                details={"message": f"Sensor {sensor_id} not registered"}
            )

        if len(self.sensor_measurements.get(sensor_id, [])) < 10:
            return DriftResult(
                drift_type=DriftType.SENSOR,
                severity=DriftSeverity.NONE,
                is_detected=False,
                score=0.0,
                timestamp=datetime.now(),
                details={"message": "Insufficient sensor measurements"}
            )

        baseline = self.sensor_baselines[sensor_id]
        measurements = self.sensor_measurements[sensor_id]
        curr_mean = np.mean(measurements)
        curr_std = np.std(measurements)

        # Calculate drift score
        score = 0.0
        if baseline.get("mean") is not None:
            base_mean = baseline["mean"]
            base_std = baseline.get("std", 1.0)
            if base_std > 0:
                score = abs((curr_mean - base_mean) / base_std)
            else:
                score = abs(curr_mean - base_mean)

        # Check bounds
        if baseline.get("min") is not None and any(m < baseline["min"] for m in measurements[-5:]):
            score += 0.2
        if baseline.get("max") is not None and any(m > baseline["max"] for m in measurements[-5:]):
            score += 0.2

        severity = DriftSeverity.NONE
        if score > self.threshold * 2:
            severity = DriftSeverity.CRITICAL
        elif score > self.threshold * 1.5:
            severity = DriftSeverity.HIGH
        elif score > self.threshold:
            severity = DriftSeverity.MEDIUM
        elif score > self.threshold * 0.5:
            severity = DriftSeverity.LOW

        return DriftResult(
            drift_type=DriftType.SENSOR,
            severity=severity,
            is_detected=score > self.threshold,
            score=score,
            timestamp=datetime.now(),
            details={
                "sensor_id": sensor_id,
                "mean_current": curr_mean,
                "mean_baseline": baseline.get("mean"),
                "std_current": curr_std
            }
        )

