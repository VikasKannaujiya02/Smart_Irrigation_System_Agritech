"""Gateway service orchestration for communication foundation."""

from __future__ import annotations

import logging

from .gateway import Gateway


class GatewayManager:
    """Owns gateway lifecycle without implementing business decisions."""

    def __init__(self, gateway: Gateway, logger: logging.Logger | None = None) -> None:
        self.gateway = gateway
        self.logger = logger or logging.getLogger(__name__)
        self._running = False

    def start(self) -> None:
        """Mark gateway service as running."""
        self._running = True
        self.logger.info("Gateway manager started")

    def stop(self) -> None:
        """Stop gateway service lifecycle."""
        self._running = False
        self.gateway.lora_interface.close()
        self.logger.info("Gateway manager stopped")

    @property
    def is_running(self) -> bool:
        """Return whether the gateway service is running."""
        return self._running
