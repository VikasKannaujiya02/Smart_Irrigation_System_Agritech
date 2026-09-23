"""Pump simulation model for Digital Twin."""

import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum, auto
from datetime import datetime

logger = logging.getLogger(__name__)


class PumpState(Enum):
    """Pump operational state."""
    OFF = auto()
    ON = auto()
    FAULT = auto()
    DRY_RUN = auto()


@dataclass
class PumpProperties:
    """Pump physical properties."""
    max_flow_rate_lps: float = 2.0  # Liters per second
    max_pressure_bar: float = 3.0
    power_kw: float = 1.5
    efficiency: float = 0.85
    min_voltage_v: float = 210.0
    max_voltage_v: float = 250.0


@dataclass
class PumpStateData:
    """Current pump state."""
    state: PumpState = PumpState.OFF
    current_flow_rate_lps: float = 0.0
    current_pressure_bar: float = 0.0
    current_power_kw: float = 0.0
    voltage_v: float = 230.0
    temperature_c: float = 25.0
    runtime_s: int = 0
    total_runtime_today_s: int = 0
    cycles_today: int = 0
    last_start_time: Optional[datetime] = None
    last_stop_time: Optional[datetime] = None


class PumpModel:
    """
    Model for simulating pump behavior.
    
    Simulates:
    - Pump ON/OFF state
    - Flow rate and pressure
    - Power consumption
    - Temperature rise
    - Runtime tracking
    - Dry run detection
    """

    def __init__(self, properties: Optional[PumpProperties] = None):
        self.properties = properties or PumpProperties()
        self.state = PumpStateData()
        logger.info("PumpModel initialized")

    def turn_on(self) -> bool:
        """
        Turn the pump ON.
        
        Returns:
            True if pump turned on successfully
        """
        if self.state.state in (PumpState.FAULT, PumpState.DRY_RUN):
            logger.warning(f"Cannot turn pump on, state: {self.state.state.name}")
            return False

        if self.state.state == PumpState.ON:
            logger.debug("Pump already ON")
            return True

        self.state.state = PumpState.ON
        self.state.last_start_time = datetime.now()
        self.state.cycles_today += 1
        self.state.current_flow_rate_lps = self.properties.max_flow_rate_lps
        self.state.current_pressure_bar = self.properties.max_pressure_bar
        logger.info("Pump turned ON")
        return True

    def turn_off(self) -> bool:
        """
        Turn the pump OFF.
        
        Returns:
            True if pump turned off successfully
        """
        if self.state.state == PumpState.OFF:
            logger.debug("Pump already OFF")
            return True

        self.state.state = PumpState.OFF
        self.state.last_stop_time = datetime.now()
        self.state.current_flow_rate_lps = 0.0
        self.state.current_pressure_bar = 0.0
        self.state.current_power_kw = 0.0
        logger.info("Pump turned OFF")
        return True

    def set_fault(self, fault_type: str = "general") -> None:
        """Set pump to FAULT state."""
        self.state.state = PumpState.FAULT
        self.state.current_flow_rate_lps = 0.0
        self.state.current_pressure_bar = 0.0
        self.state.current_power_kw = 0.0
        logger.error(f"Pump FAULT: {fault_type}")

    def set_dry_run(self) -> None:
        """Set pump to DRY_RUN state."""
        self.state.state = PumpState.DRY_RUN
        self.state.current_flow_rate_lps = 0.0
        self.state.current_pressure_bar = 0.0
        logger.error("Pump DRY RUN detected")

    def clear_fault(self) -> bool:
        """Clear pump fault/dry run state."""
        if self.state.state not in (PumpState.FAULT, PumpState.DRY_RUN):
            return False

        self.state.state = PumpState.OFF
        logger.info("Pump fault cleared")
        return True

    def update(self, time_step_s: float, flow_rate_lps: Optional[float] = None) -> None:
        """
        Update pump state for a time step.
        
        Args:
            time_step_s: Time step in seconds
            flow_rate_lps: Optional override for flow rate
        """
        if self.state.state == PumpState.ON:
            self.state.runtime_s += int(time_step_s)
            self.state.total_runtime_today_s += int(time_step_s)

            if flow_rate_lps is not None:
                self.state.current_flow_rate_lps = flow_rate_lps
            else:
                self.state.current_flow_rate_lps = self.properties.max_flow_rate_lps

            # Calculate power consumption
            load_factor = self.state.current_flow_rate_lps / self.properties.max_flow_rate_lps
            self.state.current_power_kw = self.properties.power_kw * load_factor

            # Simulate temperature rise (simple model)
            temp_rise = 0.01 * time_step_s  # 0.01°C per second
            self.state.temperature_c = min(80.0, self.state.temperature_c + temp_rise)
        else:
            # Cool down when off
            self.state.temperature_c = max(20.0, self.state.temperature_c - 0.005 * time_step_s)

    def get_water_delivered(self, time_step_s: float) -> float:
        """
        Calculate water delivered in a time step.
        
        Args:
            time_step_s: Time step in seconds
            
        Returns:
            Water delivered in liters
        """
        if self.state.state != PumpState.ON:
            return 0.0
        return self.state.current_flow_rate_lps * time_step_s

    def reset_daily_counters(self) -> None:
        """Reset daily runtime and cycle counters."""
        self.state.total_runtime_today_s = 0
        self.state.cycles_today = 0
        self.state.runtime_s = 0
        logger.info("Pump daily counters reset")

    def get_state(self) -> dict:
        """Get complete pump state as dictionary."""
        return {
            "properties": {
                "max_flow_rate_lps": self.properties.max_flow_rate_lps,
                "max_pressure_bar": self.properties.max_pressure_bar,
                "power_kw": self.properties.power_kw,
                "efficiency": self.properties.efficiency
            },
            "state": {
                "state": self.state.state.name,
                "current_flow_rate_lps": self.state.current_flow_rate_lps,
                "current_pressure_bar": self.state.current_pressure_bar,
                "current_power_kw": self.state.current_power_kw,
                "voltage_v": self.state.voltage_v,
                "temperature_c": self.state.temperature_c,
                "runtime_s": self.state.runtime_s,
                "total_runtime_today_s": self.state.total_runtime_today_s,
                "cycles_today": self.state.cycles_today
            }
        }
