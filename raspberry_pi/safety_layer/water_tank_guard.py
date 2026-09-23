"""Water Tank Guard module for Safety Layer."""

import logging
from datetime import datetime
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

logger = logging.getLogger(__name__)


class TankStatus(Enum):
    """Water tank status."""
    FULL = auto()
    NORMAL = auto()
    LOW = auto()
    EMPTY = auto()
    UNKNOWN = auto()


@dataclass
class WaterTankState:
    """Water tank state."""
    tank_id: str
    level_percent: Optional[float] = None
    level_raw: Optional[float] = None
    status: TankStatus = TankStatus.UNKNOWN
    last_updated: Optional[datetime] = None
    capacity_liters: Optional[float] = None
    low_threshold_percent: float = 20.0
    empty_threshold_percent: float = 5.0


class WaterTankGuard:
    """Monitors water tank levels."""

    def __init__(self):
        self.tanks: dict[str, WaterTankState] = {}
        logger.info("WaterTankGuard initialized")

    def register_tank(
        self,
        tank_id: str,
        capacity_liters: Optional[float] = None,
        low_threshold_percent: float = 20.0,
        empty_threshold_percent: float = 5.0
    ) -> None:
        """
        Register a water tank for monitoring.

        Args:
            tank_id: Unique tank identifier
            capacity_liters: Total tank capacity in liters
            low_threshold_percent: Low level threshold (%)
            empty_threshold_percent: Empty threshold (%)
        """
        self.tanks[tank_id] = WaterTankState(
            tank_id=tank_id,
            capacity_liters=capacity_liters,
            low_threshold_percent=low_threshold_percent,
            empty_threshold_percent=empty_threshold_percent
        )
        logger.info(f"Registered water tank: {tank_id}")

    def update_level(
        self,
        tank_id: str,
        level_percent: Optional[float] = None,
        level_raw: Optional[float] = None
    ) -> TankStatus:
        """
        Update tank level reading.

        Args:
            tank_id: Which tank
            level_percent: Tank level (%)
            level_raw: Raw level (e.g., sensor voltage)

        Returns:
            Current tank status
        """
        if tank_id not in self.tanks:
            logger.warning(f"Tank {tank_id} not registered")
            return TankStatus.UNKNOWN

        state = self.tanks[tank_id]
        state.level_percent = level_percent
        state.level_raw = level_raw
        state.last_updated = datetime.now()

        if level_percent is not None:
            if level_percent <= state.empty_threshold_percent:
                state.status = TankStatus.EMPTY
                logger.critical(f"Tank {tank_id} is EMPTY: {level_percent}%")
            elif level_percent <= state.low_threshold_percent:
                state.status = TankStatus.LOW
                logger.warning(f"Tank {tank_id} is LOW: {level_percent}%")
            elif level_percent >= 95.0:
                state.status = TankStatus.FULL
            else:
                state.status = TankStatus.NORMAL
        else:
            state.status = TankStatus.UNKNOWN

        return state.status

    def get_tank_status(self, tank_id: str) -> Optional[TankStatus]:
        """Get status of a tank."""
        if tank_id in self.tanks:
            return self.tanks[tank_id].status
        return None

    def is_tank_empty(self, tank_id: str) -> bool:
        """Check if tank is empty."""
        status = self.get_tank_status(tank_id)
        return status == TankStatus.EMPTY

    def is_tank_low(self, tank_id: str) -> bool:
        """Check if tank is low or empty."""
        status = self.get_tank_status(tank_id)
        return status in (TankStatus.LOW, TankStatus.EMPTY)

    def can_irrigate(self, tank_id: str) -> tuple[bool, str]:
        """
        Check if irrigation is allowed based on tank level.

        Args:
            tank_id: Which tank

        Returns:
            (can_irrigate, reason)
        """
        status = self.get_tank_status(tank_id)

        if status == TankStatus.EMPTY:
            return False, "Tank is empty"

        if status == TankStatus.LOW:
            return True, "Tank is low, irrigation allowed but monitor closely"

        if status == TankStatus.UNKNOWN:
            return True, "Tank status unknown, proceed with caution"

        return True, "Tank level OK"

    def get_state(self, tank_id: str) -> Optional[WaterTankState]:
        """Get full tank state."""
        return self.tanks.get(tank_id)
