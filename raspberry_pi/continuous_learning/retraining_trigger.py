"""Retraining trigger system for continuous learning."""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum, auto

from .drift_detectors import DriftResult, DriftType

logger = logging.getLogger(__name__)


class TriggerReason(Enum):
    MODEL_DRIFT = auto()
    DATA_DRIFT = auto()
    SENSOR_DRIFT = auto()
    PERIODIC = auto()
    MANUAL = auto()
    DATASET_GROWTH = auto()


@dataclass
class TriggerEvent:
    """Event that triggers retraining."""
    reason: TriggerReason
    timestamp: datetime
    severity: float
    details: Dict[str, Any] = field(default_factory=dict)
    should_retrain: bool = False


class RetrainingTrigger:
    """Manages retraining triggers."""

    def __init__(
        self,
        model_drift_threshold: float = 0.3,
        data_drift_threshold: float = 0.2,
        sensor_drift_threshold: float = 0.4,
        periodic_interval_days: int = 30,
        min_new_samples: int = 1000,
        cooldown_hours: int = 24
    ):
        self.model_drift_threshold = model_drift_threshold
        self.data_drift_threshold = data_drift_threshold
        self.sensor_drift_threshold = sensor_drift_threshold
        self.periodic_interval = timedelta(days=periodic_interval_days)
        self.min_new_samples = min_new_samples
        self.cooldown = timedelta(hours=cooldown_hours)
        
        self.last_retrain_time: Optional[datetime] = None
        self.trigger_history: List[TriggerEvent] = []
        self.new_sample_count: int = 0

    def check_drift(self, drift_result: DriftResult) -> TriggerEvent:
        """Check drift result and determine if retrain is needed."""
        event = TriggerEvent(
            reason=self._map_drift_type(drift_result.drift_type),
            timestamp=drift_result.timestamp,
            severity=drift_result.score,
            details={"drift_details": drift_result.details}
        )

        threshold = self._get_threshold(drift_result.drift_type)
        event.should_retrain = drift_result.is_detected and drift_result.score > threshold

        if event.should_retrain:
            logger.warning(f"Retrain triggered by {event.reason.name}, severity: {event.severity:.3f}")

        self.trigger_history.append(event)
        return event

    def check_periodic(self) -> TriggerEvent:
        """Check if periodic retraining is due."""
        now = datetime.now()
        event = TriggerEvent(
            reason=TriggerReason.PERIODIC,
            timestamp=now,
            severity=0.5,
            details={"last_retrain": self.last_retrain_time.isoformat() if self.last_retrain_time else None}
        )

        if not self.last_retrain_time:
            event.should_retrain = True
        else:
            event.should_retrain = (now - self.last_retrain_time) > self.periodic_interval

        if event.should_retrain:
            logger.info("Periodic retrain triggered")

        self.trigger_history.append(event)
        return event

    def check_dataset_growth(self, new_samples: int) -> TriggerEvent:
        """Check if dataset has grown enough to trigger retraining."""
        self.new_sample_count += new_samples
        event = TriggerEvent(
            reason=TriggerReason.DATASET_GROWTH,
            timestamp=datetime.now(),
            severity=0.3,
            details={
                "new_samples_since_last": self.new_sample_count,
                "threshold": self.min_new_samples
            }
        )
        event.should_retrain = self.new_sample_count >= self.min_new_samples

        if event.should_retrain:
            logger.info(f"Dataset growth triggered retrain: {self.new_sample_count} new samples")

        self.trigger_history.append(event)
        return event

    def manual_trigger(self, reason: str = "Manual") -> TriggerEvent:
        """Manually trigger retraining."""
        event = TriggerEvent(
            reason=TriggerReason.MANUAL,
            timestamp=datetime.now(),
            severity=1.0,
            details={"manual_reason": reason},
            should_retrain=True
        )
        logger.warning(f"Manual retrain triggered: {reason}")
        self.trigger_history.append(event)
        return event

    def can_retrain(self) -> bool:
        """Check if retraining is allowed (cooldown period)."""
        if not self.last_retrain_time:
            return True
        return (datetime.now() - self.last_retrain_time) > self.cooldown

    def record_retrain(self) -> None:
        """Record that a retraining has occurred."""
        self.last_retrain_time = datetime.now()
        self.new_sample_count = 0
        logger.info(f"Retraining completed, recorded at {self.last_retrain_time.isoformat()}")

    def _map_drift_type(self, drift_type: DriftType) -> TriggerReason:
        mapping = {
            DriftType.MODEL: TriggerReason.MODEL_DRIFT,
            DriftType.DATA: TriggerReason.DATA_DRIFT,
            DriftType.SENSOR: TriggerReason.SENSOR_DRIFT
        }
        return mapping.get(drift_type, TriggerReason.MODEL_DRIFT)

    def _get_threshold(self, drift_type: DriftType) -> float:
        mapping = {
            DriftType.MODEL: self.model_drift_threshold,
            DriftType.DATA: self.data_drift_threshold,
            DriftType.SENSOR: self.sensor_drift_threshold
        }
        return mapping.get(drift_type, 0.3)
