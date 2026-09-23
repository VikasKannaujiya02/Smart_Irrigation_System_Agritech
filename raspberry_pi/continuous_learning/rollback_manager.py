"""Model rollback manager."""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum, auto

logger = logging.getLogger(__name__)


class RollbackReason(Enum):
    VALIDATION_FAILED = auto()
    PERFORMANCE_DEGRADED = auto()
    DRIFT_DETECTED = auto()
    MANUAL = auto()
    CRASH = auto()


@dataclass
class RollbackEvent:
    """Record of a rollback event."""
    model_id: str
    from_version: str
    to_version: str
    reason: RollbackReason
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)


class RollbackManager:
    """Manages model rollbacks."""

    def __init__(
        self,
        max_history: int = 100,
        auto_rollback_on_failure: bool = True
    ):
        self.max_history = max_history
        self.auto_rollback_on_failure = auto_rollback_on_failure
        self.rollback_history: List[RollbackEvent] = []
        self.version_stack: Dict[str, List[str]] = {}  # key: model_id, value: list of versions

    def register_version(self, model_id: str, version: str) -> None:
        """Register a new version for rollback purposes."""
        if model_id not in self.version_stack:
            self.version_stack[model_id] = []
        self.version_stack[model_id].append(version)
        logger.info(f"Registered version {version} for model {model_id}")

    def rollback(
        self,
        model_id: str,
        reason: RollbackReason,
        target_version: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Optional[RollbackEvent]:
        """Perform a rollback."""
        if model_id not in self.version_stack or len(self.version_stack[model_id]) < 2:
            logger.error(f"Cannot rollback model {model_id}: not enough versions")
            return None

        versions = self.version_stack[model_id]
        current_version = versions[-1]

        if target_version:
            if target_version not in versions:
                logger.error(f"Target version {target_version} not found for {model_id}")
                return None
            target_idx = versions.index(target_version)
        else:
            target_idx = len(versions) - 2  # Previous version

        to_version = versions[target_idx]

        # Remove versions after target
        self.version_stack[model_id] = versions[:target_idx + 1]

        event = RollbackEvent(
            model_id=model_id,
            from_version=current_version,
            to_version=to_version,
            reason=reason,
            timestamp=datetime.now(),
            details=details or {}
        )

        self.rollback_history.append(event)
        if len(self.rollback_history) > self.max_history:
            self.rollback_history.pop(0)

        logger.warning(f"Rolled back {model_id} from {current_version} to {to_version}, reason: {reason.name}")
        return event

    def get_rollback_history(self, model_id: Optional[str] = None) -> List[RollbackEvent]:
        """Get rollback history."""
        if model_id:
            return [e for e in self.rollback_history if e.model_id == model_id]
        return self.rollback_history.copy()

    def get_available_versions(self, model_id: str) -> List[str]:
        """Get available versions to rollback to."""
        return self.version_stack.get(model_id, []).copy()
