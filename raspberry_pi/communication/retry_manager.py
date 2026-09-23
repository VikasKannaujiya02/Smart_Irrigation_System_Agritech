"""Retry policy for packets waiting on ACK."""

from __future__ import annotations

from dataclasses import dataclass

from .ack_manager import PendingAck
from .protocol_constants import DEFAULT_MAX_RETRIES


@dataclass(frozen=True)
class RetryDecision:
    """Decision returned for a packet whose ACK timed out."""

    should_retry: bool
    attempts: int
    reason: str


class RetryManager:
    """Applies bounded retry behavior for reliable command delivery."""

    def __init__(self, max_retries: int = DEFAULT_MAX_RETRIES) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be zero or greater")
        self._max_retries = max_retries

    def decide(self, pending_ack: PendingAck) -> RetryDecision:
        """Return whether the pending packet should be retransmitted."""
        if pending_ack.attempts <= self._max_retries:
            return RetryDecision(
                should_retry=True,
                attempts=pending_ack.attempts + 1,
                reason="ACK timeout; retry allowed",
            )
        return RetryDecision(
            should_retry=False,
            attempts=pending_ack.attempts,
            reason="ACK timeout; retry limit reached",
        )
