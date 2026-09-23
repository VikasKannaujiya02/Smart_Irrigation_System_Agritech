"""Watchdog and Recovery module for Safety Layer."""

import logging
import threading
import time
from datetime import datetime
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Optional, Callable, List

logger = logging.getLogger(__name__)


class WatchdogStatus(Enum):
    """Watchdog status."""
    IDLE = auto()
    RUNNING = auto()
    TRIGGERED = auto()
    RECOVERING = auto()


class RecoveryAction(Enum):
    """Recovery actions to take."""
    LOG_ONLY = auto()
    RESTART_SERVICE = auto()
    RESTART_GATEWAY = auto()
    EMERGENCY_STOP = auto()


@dataclass
class WatchdogEntry:
    """Single watchdog entry."""
    name: str
    timeout_seconds: float
    last_heartbeat: Optional[datetime] = None
    status: WatchdogStatus = WatchdogStatus.IDLE
    recovery_action: RecoveryAction = RecoveryAction.LOG_ONLY
    trigger_count: int = 0
    on_trigger: Optional[Callable[[], None]] = None
    on_recover: Optional[Callable[[], None]] = None


@dataclass
class DeviceTimeoutEntry:
    """Device timeout tracking."""
    device_id: str
    last_seen: Optional[datetime] = None
    timeout_seconds: float = 300.0
    is_offline: bool = False
    offline_since: Optional[datetime] = None


class WatchdogManager:
    """Manages system watchdogs and recovery."""

    def __init__(self, check_interval_seconds: float = 1.0):
        self.watchdogs: Dict[str, WatchdogEntry] = {}
        self.devices: Dict[str, DeviceTimeoutEntry] = {}
        self.check_interval = check_interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        logger.info("WatchdogManager initialized")

    def register_watchdog(
        self,
        name: str,
        timeout_seconds: float,
        recovery_action: RecoveryAction = RecoveryAction.LOG_ONLY,
        on_trigger: Optional[Callable[[], None]] = None,
        on_recover: Optional[Callable[[], None]] = None
    ) -> None:
        """
        Register a new watchdog.

        Args:
            name: Watchdog name
            timeout_seconds: Timeout duration
            recovery_action: Action to take on trigger
            on_trigger: Callback when triggered
            on_recover: Callback when recovered
        """
        with self._lock:
            self.watchdogs[name] = WatchdogEntry(
                name=name,
                timeout_seconds=timeout_seconds,
                recovery_action=recovery_action,
                on_trigger=on_trigger,
                on_recover=on_recover
            )
            logger.info(f"Registered watchdog: {name} (timeout: {timeout_seconds}s)")

    def register_device(
        self,
        device_id: str,
        timeout_seconds: float = 300.0
    ) -> None:
        """
        Register a device for timeout monitoring.

        Args:
            device_id: Device identifier
            timeout_seconds: Timeout before marking as offline
        """
        with self._lock:
            self.devices[device_id] = DeviceTimeoutEntry(
                device_id=device_id,
                timeout_seconds=timeout_seconds
            )
            logger.info(f"Registered device for timeout: {device_id}")

    def heartbeat(self, name: str) -> None:
        """
        Send a heartbeat to reset a watchdog.

        Args:
            name: Watchdog name
        """
        with self._lock:
            if name in self.watchdogs:
                entry = self.watchdogs[name]
                was_triggered = entry.status == WatchdogStatus.TRIGGERED
                entry.last_heartbeat = datetime.now()
                entry.status = WatchdogStatus.RUNNING

                if was_triggered and entry.on_recover:
                    try:
                        entry.on_recover()
                    except Exception as e:
                        logger.error(f"Recovery callback failed for {name}: {e}")

    def device_heartbeat(self, device_id: str) -> None:
        """
        Record a device heartbeat.

        Args:
            device_id: Device identifier
        """
        with self._lock:
            if device_id in self.devices:
                entry = self.devices[device_id]
                entry.last_seen = datetime.now()
                if entry.is_offline:
                    entry.is_offline = False
                    entry.offline_since = None
                    logger.info(f"Device {device_id} came back online")

    def start(self) -> None:
        """Start watchdog monitoring."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Watchdog manager started")

    def stop(self) -> None:
        """Stop watchdog monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("Watchdog manager stopped")

    def _monitor_loop(self) -> None:
        """Internal monitoring loop."""
        while self._running:
            self._check_watchdogs()
            self._check_devices()
            time.sleep(self.check_interval)

    def _check_watchdogs(self) -> None:
        """Check all watchdogs."""
        now = datetime.now()

        with self._lock:
            for name, entry in self.watchdogs.items():
                if entry.status != WatchdogStatus.RUNNING:
                    continue

                if entry.last_heartbeat:
                    elapsed = (now - entry.last_heartbeat).total_seconds()
                    if elapsed > entry.timeout_seconds:
                        self._trigger_watchdog(entry)

    def _trigger_watchdog(self, entry: WatchdogEntry) -> None:
        """Trigger a watchdog."""
        entry.status = WatchdogStatus.TRIGGERED
        entry.trigger_count += 1
        logger.critical(f"WATCHDOG TRIGGERED: {entry.name}")

        if entry.on_trigger:
            try:
                entry.on_trigger()
            except Exception as e:
                logger.error(f"Trigger callback failed for {entry.name}: {e}")

        # Handle recovery action
        self._handle_recovery_action(entry)

    def _handle_recovery_action(self, entry: WatchdogEntry) -> None:
        """Execute recovery action."""
        if entry.recovery_action == RecoveryAction.LOG_ONLY:
            pass
        elif entry.recovery_action == RecoveryAction.EMERGENCY_STOP:
            logger.critical(f"Recovery action: EMERGENCY STOP for {entry.name}")
        elif entry.recovery_action == RecoveryAction.RESTART_SERVICE:
            logger.warning(f"Recovery action: RESTART SERVICE for {entry.name}")
        elif entry.recovery_action == RecoveryAction.RESTART_GATEWAY:
            logger.critical(f"Recovery action: RESTART GATEWAY for {entry.name}")

    def _check_devices(self) -> None:
        """Check all devices for timeout."""
        now = datetime.now()

        with self._lock:
            for device_id, entry in self.devices.items():
                if entry.last_seen is None:
                    continue

                elapsed = (now - entry.last_seen).total_seconds()
                if elapsed > entry.timeout_seconds and not entry.is_offline:
                    entry.is_offline = True
                    entry.offline_since = now
                    logger.warning(f"Device {device_id} OFFLINE (timeout)")

    def get_watchdog_status(self, name: str) -> Optional[WatchdogStatus]:
        """Get status of a watchdog."""
        with self._lock:
            if name in self.watchdogs:
                return self.watchdogs[name].status
        return None

    def is_device_offline(self, device_id: str) -> bool:
        """Check if a device is offline."""
        with self._lock:
            if device_id in self.devices:
                return self.devices[device_id].is_offline
        return False

    def get_offline_devices(self) -> List[str]:
        """Get list of offline devices."""
        with self._lock:
            return [did for did, d in self.devices.items() if d.is_offline]
