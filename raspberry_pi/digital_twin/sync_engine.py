"""Real-time sync and historical replay for Digital Twin."""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, Dict
from datetime import datetime
from queue import Queue, Empty

from .field_model import FieldModel
from .soil_model import SoilModel
from .pump_model import PumpModel
from .crop_model import CropModel
from .weather_model import WeatherModel, WeatherState
from .state_manager import StateManager, DigitalTwinState

logger = logging.getLogger(__name__)


@dataclass
class SyncConfig:
    """Configuration for sync engine."""
    sync_interval_s: float = 1.0  # Real-time sync interval
    replay_speed: float = 1.0  # Replay speed multiplier
    enable_auto_sync: bool = True
    max_sync_queue_size: int = 1000


class SyncEngine:
    """
    Sync engine for Digital Twin.
    
    Features:
    - Real-time synchronization with physical system
    - Historical replay
    - Data buffering
    - Callback hooks for sync events
    - Communication failure handling
    - Offline mode support
    """

    def __init__(
        self,
        field: FieldModel,
        soil: SoilModel,
        pump: PumpModel,
        crop: CropModel,
        weather: WeatherModel,
        state_manager: StateManager,
        config: Optional[SyncConfig] = None
    ):
        self.field = field
        self.soil = soil
        self.pump = pump
        self.crop = crop
        self.weather = weather
        self.state_manager = state_manager
        self.config = config or SyncConfig()
        
        self._sync_thread: Optional[threading.Thread] = None
        self._replay_thread: Optional[threading.Thread] = None
        self._running = False
        self._replaying = False
        
        self._sync_queue: Queue = Queue(maxsize=self.config.max_sync_queue_size)
        self._callbacks: Dict[str, list[Callable]] = {
            "pre_sync": [],
            "post_sync": [],
            "sync_error": [],
            "state_update": []
        }
        
        self.last_sync_time: Optional[datetime] = None
        self.sync_count = 0
        self.error_count = 0
        
        logger.info("SyncEngine initialized")

    def register_callback(self, event: str, callback: Callable) -> None:
        """
        Register a callback for sync events.
        
        Args:
            event: Event name ("pre_sync", "post_sync", "sync_error", "state_update")
            callback: Callback function
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _trigger_callbacks(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Trigger registered callbacks for an event."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")

    def queue_sync_data(self, data: dict) -> None:
        """
        Queue data for synchronization.
        
        Args:
            data: Data dict with sensor readings, etc.
        """
        try:
            self._sync_queue.put(data, block=False)
        except Exception as e:
            logger.warning(f"Sync queue full, dropping data: {e}")

    def _apply_sync_data(self, data: dict) -> None:
        """
        Apply sync data to Digital Twin models.
        
        Args:
            data: Sync data dict
        """
        # Weather data
        if "weather" in data:
            w_data = data["weather"]
            weather_state = WeatherState(
                temperature_c=w_data.get("temperature_c", self.weather.state.temperature_c),
                humidity_pct=w_data.get("humidity_pct", self.weather.state.humidity_pct),
                wind_speed_mps=w_data.get("wind_speed_mps", self.weather.state.wind_speed_mps),
                solar_radiation_w_m2=w_data.get("solar_radiation_w_m2", self.weather.state.solar_radiation_w_m2),
                rainfall_mm=w_data.get("rainfall_mm", 0.0)
            )
            self.weather.update_state(weather_state)
        
        # Soil data
        if "soil" in data:
            s_data = data["soil"]
            if "moisture_vwc" in s_data:
                self.soil.state.current_vwc = s_data["moisture_vwc"]
            if "temperature_c" in s_data:
                self.soil.state.temperature_c = s_data["temperature_c"]
        
        # Pump data
        if "pump" in data:
            p_data = data["pump"]
            if "state" in p_data:
                from .pump_model import PumpState
                try:
                    pump_state = PumpState[p_data["state"]]
                    if pump_state == PumpState.ON:
                        self.pump.turn_on()
                    else:
                        self.pump.turn_off()
                except KeyError:
                    pass
        
        # Field data
        if "field" in data:
            f_data = data["field"]
            if "irrigation_active" in f_data:
                if f_data["irrigation_active"]:
                    self.field.start_irrigation()
                else:
                    self.field.stop_irrigation()

    def _sync_loop(self) -> None:
        """Internal real-time sync loop."""
        while self._running:
            try:
                self._trigger_callbacks("pre_sync")
                
                # Process queued sync data
                while not self._sync_queue.empty():
                    try:
                        data = self._sync_queue.get_nowait()
                        self._apply_sync_data(data)
                    except Empty:
                        break
                
                # Take state snapshot
                self.state_manager.snapshot(
                    field=self.field,
                    soil=self.soil,
                    pump=self.pump,
                    crop=self.crop,
                    weather=self.weather
                )
                
                self.last_sync_time = datetime.now()
                self.sync_count += 1
                
                self._trigger_callbacks("post_sync")
                
            except Exception as e:
                self.error_count += 1
                logger.error(f"Sync error: {e}")
                self._trigger_callbacks("sync_error", error=e)
            
            time.sleep(self.config.sync_interval_s)

    def start_sync(self) -> None:
        """Start real-time synchronization."""
        if self._running:
            logger.warning("Sync already running")
            return
            
        self._running = True
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
        logger.info("Real-time sync started")

    def stop_sync(self) -> None:
        """Stop real-time synchronization."""
        self._running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=5.0)
        logger.info("Real-time sync stopped")

    def start_replay(
        self,
        history: list[DigitalTwinState],
        speed: Optional[float] = None,
        on_complete: Optional[Callable] = None
    ) -> None:
        """
        Start historical replay.
        
        Args:
            history: List of states to replay
            speed: Replay speed (1.0 = real-time)
            on_complete: Callback when replay completes
        """
        if self._replaying:
            logger.warning("Replay already in progress")
            return
            
        self._replaying = True
        replay_speed = speed or self.config.replay_speed
        
        def _replay_loop():
            nonlocal on_complete
            try:
                for i, state in enumerate(history):
                    if not self._replaying:
                        break
                        
                    # Apply state to models
                    logger.info(f"Replaying state {i+1}/{len(history)}")
                    
                    self._trigger_callbacks("state_update", state=state)
                    
                    # Wait according to replay speed
                    if i < len(history) - 1:
                        next_state = history[i+1]
                        time_delta = (next_state.timestamp - state.timestamp).total_seconds()
                        time.sleep(time_delta / replay_speed)
                        
                logger.info("Replay complete")
                if on_complete:
                    on_complete()
                    
            except Exception as e:
                logger.error(f"Replay error: {e}")
            finally:
                self._replaying = False
                
        self._replay_thread = threading.Thread(target=_replay_loop, daemon=True)
        self._replay_thread.start()

    def stop_replay(self) -> None:
        """Stop historical replay."""
        self._replaying = False
        if self._replay_thread:
            self._replay_thread.join(timeout=5.0)
        logger.info("Replay stopped")

    def get_sync_stats(self) -> dict:
        """Get synchronization statistics."""
        return {
            "sync_count": self.sync_count,
            "error_count": self.error_count,
            "last_sync_time": self.last_sync_time,
            "is_syncing": self._running,
            "is_replaying": self._replaying,
            "queue_size": self._sync_queue.qsize()
        }
