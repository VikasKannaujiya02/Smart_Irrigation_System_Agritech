"""Champion-Challenger Model Management."""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum, auto

logger = logging.getLogger(__name__)


class ChallengeStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    WON = auto()
    LOST = auto()
    DRAW = auto()


@dataclass
class ModelEntry:
    """A model in champion-challenger system."""
    model_id: str
    model_type: str
    is_champion: bool = False
    challenge_status: ChallengeStatus = ChallengeStatus.PENDING
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    challenge_metrics: Dict[str, float] = field(default_factory=dict)
    deploy_time: Optional[datetime] = None
    inference_count: int = 0


class ChampionChallengerManager:
    """Manages champion and challenger models."""

    def __init__(
        self,
        selection_metric: str = "mae",
        win_threshold: float = 0.1,
        warmup_samples: int = 100
    ):
        self.selection_metric = selection_metric
        self.win_threshold = win_threshold
        self.warmup_samples = warmup_samples
        self.models: Dict[str, ModelEntry] = {}
        self.champion_id: Optional[str] = None
        self.history: List[Dict[str, Any]] = []

    def register_model(
        self,
        model_id: str,
        model_type: str,
        initial_metrics: Optional[Dict[str, float]] = None,
        is_challenger: bool = False
    ) -> ModelEntry:
        entry = ModelEntry(
            model_id=model_id,
            model_type=model_type,
            performance_metrics=initial_metrics or {},
            is_champion=not is_challenger and not self.champion_id,
            challenge_status=ChallengeStatus.PENDING if is_challenger else ChallengeStatus.WON if not is_challenger else ChallengeStatus.PENDING
        )

        if entry.is_champion and not self.champion_id:
            self.champion_id = model_id
            entry.is_champion = True

        self.models[model_id] = entry
        logger.info(f"Registered model {model_id}, is_champion: {entry.is_champion}")
        return entry

    def update_performance(
        self,
        model_id: str,
        metrics: Dict[str, float]
    ) -> None:
        if model_id in self.models:
            self.models[model_id].performance_metrics.update(metrics)
            self.models[model_id].inference_count += 1
            logger.info(f"Updated {model_id} performance: {metrics}")

    def run_challenge(
        self,
        champion_id: str,
        challenger_id: str,
        comparison_data: Any
    ) -> Dict[str, Any]:
        champion = self.models.get(champion_id)
        challenger = self.models.get(challenger_id)

        if not champion or not challenger:
            raise ValueError("One or both models not registered")

        logger.info(f"Running challenge between {champion_id} (champion) and {challenger_id} (challenger)")

        champion.challenge_status = ChallengeStatus.RUNNING
        challenger.challenge_status = ChallengeStatus.RUNNING

        # Compare based on metric: lower is better for mae/rmse, higher for r2/accuracy
        champ_score = champion.performance_metrics.get(self.selection_metric, float("inf"))
        chall_score = challenger.performance_metrics.get(self.selection_metric, float("inf"))

        if self.selection_metric in ["mae", "rmse", "mse"]:
            # Lower is better
            if chall_score < champ_score * (1 - self.win_threshold):
                result = {
                    "winner": challenger_id,
                    "loser": champion_id,
                    "champ_score": champ_score,
                    "chall_score": chall_score
                }
                challenger.challenge_status = ChallengeStatus.WON
                champion.challenge_status = ChallengeStatus.LOST
                self.promote_challenger(challenger_id)
            elif abs(champ_score - chall_score) < 0.01:
                result = {
                    "winner": "draw",
                    "champ_score": champ_score,
                    "chall_score": chall_score
                }
                champion.challenge_status = ChallengeStatus.DRAW
                challenger.challenge_status = ChallengeStatus.DRAW
            else:
                result = {
                    "winner": champion_id,
                    "loser": challenger_id,
                    "champ_score": champ_score,
                    "chall_score": chall_score
                }
                champion.challenge_status = ChallengeStatus.WON
                challenger.challenge_status = ChallengeStatus.LOST
        else:
            # Higher is better
            if chall_score > champ_score * (1 + self.win_threshold):
                result = {
                    "winner": challenger_id,
                    "loser": champion_id,
                    "champ_score": champ_score,
                    "chall_score": chall_score
                }
                challenger.challenge_status = ChallengeStatus.WON
                champion.challenge_status = ChallengeStatus.LOST
                self.promote_challenger(challenger_id)
            elif abs(champ_score - chall_score) < 0.01:
                result = {
                    "winner": "draw",
                    "champ_score": champ_score,
                    "chall_score": chall_score
                }
                champion.challenge_status = ChallengeStatus.DRAW
                challenger.challenge_status = ChallengeStatus.DRAW
            else:
                result = {
                    "winner": champion_id,
                    "loser": challenger_id,
                    "champ_score": champ_score,
                    "chall_score": chall_score
                }
                champion.challenge_status = ChallengeStatus.WON
                challenger.challenge_status = ChallengeStatus.LOST

        result["timestamp"] = datetime.now().isoformat()
        self.history.append(result)
        logger.info(f"Challenge result: {result}")

        return result

    def promote_challenger(self, challenger_id: str) -> bool:
        if challenger_id not in self.models:
            logger.error(f"Challenger {challenger_id} not registered")
            return False

        old_champion_id = self.champion_id
        if old_champion_id in self.models:
            self.models[old_champion_id].is_champion = False
            self.models[old_champion_id].challenge_status = ChallengeStatus.LOST

        self.models[challenger_id].is_champion = True
        self.models[challenger_id].challenge_status = ChallengeStatus.WON
        self.champion_id = challenger_id
        logger.warning(f"Promoted {challenger_id} to champion")
        return True

    def get_champion(self) -> Optional[ModelEntry]:
        return self.models.get(self.champion_id)

    def get_challengers(self) -> List[ModelEntry]:
        return [m for m in self.models.values() if not m.is_champion]
