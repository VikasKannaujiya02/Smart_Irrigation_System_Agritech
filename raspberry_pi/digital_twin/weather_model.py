"""Weather simulation and impact model for Digital Twin."""

import logging
import math
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, time

logger = logging.getLogger(__name__)


@dataclass
class WeatherState:
    """Current weather state."""
    temperature_c: float = 25.0
    humidity_pct: float = 60.0
    wind_speed_mps: float = 2.0
    solar_radiation_w_m2: float = 500.0
    rainfall_mm: float = 0.0
    pressure_hpa: float = 1013.0
    cloud_cover_pct: float = 30.0
    eto_mm_day: float = 4.0  # Reference evapotranspiration


@dataclass
class WeatherForecast:
    """Weather forecast data."""
    hours_ahead: int = 24
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    wind_speed_mps: Optional[float] = None
    rainfall_mm: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    eto_mm_day: Optional[float] = None


class WeatherModel:
    """
    Weather model for simulating weather conditions and calculating ETo.
    
    Uses FAO Penman-Monteith equation for ETo calculation:
    ETo = (0.408 * Δ * (Rn - G) + γ * (900 / (T + 273)) * u2 * (es - ea)) 
          / (Δ + γ * (1 + 0.34 * u2))
    
    where:
    - ETo = Reference evapotranspiration (mm/day)
    - Δ = Slope of vapor pressure curve (kPa/°C)
    - Rn = Net radiation (MJ/m²/day)
    - G = Soil heat flux (MJ/m²/day)
    - γ = Psychrometric constant (kPa/°C)
    - T = Air temperature (°C)
    - u2 = Wind speed at 2m height (m/s)
    - es = Saturation vapor pressure (kPa)
    - ea = Actual vapor pressure (kPa)
    """

    def __init__(self, initial_state: Optional[WeatherState] = None):
        self.state = initial_state or WeatherState()
        self.forecasts: dict[int, WeatherForecast] = {}
        self._historical_data: list[tuple[datetime, WeatherState]] = []
        self._max_history = 10080  # 7 days at 1-minute intervals
        logger.info("WeatherModel initialized")

    def calculate_saturation_vapor_pressure(self, temp_c: float) -> float:
        """
        Calculate saturation vapor pressure.
        
        Args:
            temp_c: Temperature in °C
            
        Returns:
            Saturation vapor pressure in kPa
        """
        return 0.6108 * math.exp((17.27 * temp_c) / (temp_c + 237.3))

    def calculate_actual_vapor_pressure(self, temp_c: float, rh_pct: float) -> float:
        """
        Calculate actual vapor pressure.
        
        Args:
            temp_c: Temperature in °C
            rh_pct: Relative humidity %
            
        Returns:
            Actual vapor pressure in kPa
        """
        es = self.calculate_saturation_vapor_pressure(temp_c)
        return es * (rh_pct / 100.0)

    def calculate_vapor_pressure_slope(self, temp_c: float) -> float:
        """
        Calculate slope of vapor pressure curve (Δ).
        
        Args:
            temp_c: Temperature in °C
            
        Returns:
            Δ in kPa/°C
        """
        es = self.calculate_saturation_vapor_pressure(temp_c)
        return (4098 * es) / ((temp_c + 237.3) ** 2)

    def calculate_psychrometric_constant(self, pressure_hpa: float) -> float:
        """
        Calculate psychrometric constant (γ).
        
        Args:
            pressure_hpa: Atmospheric pressure in hPa
            
        Returns:
            γ in kPa/°C
        """
        pressure_kpa = pressure_hpa / 10.0
        return 0.000665 * pressure_kpa

    def calculate_net_radiation(
        self,
        solar_rad_w_m2: float,
        temp_c: float,
        cloud_cover_pct: float
    ) -> float:
        """
        Calculate net radiation (Rn).
        
        Args:
            solar_rad_w_m2: Solar radiation (W/m²)
            temp_c: Temperature (°C)
            cloud_cover_pct: Cloud cover %
            
        Returns:
            Rn in MJ/m²/day
        """
        # Convert W/m² to MJ/m²/day
        rs = solar_rad_w_m2 * 0.0864
        
        # Calculate clear sky solar radiation (approximate)
        rso = 30.0  # Approximate for mid-latitudes
        
        # Calculate net shortwave radiation
        albedo = 0.23  # Reference crop albedo (grass)
        rns = (1 - albedo) * rs
        
        # Calculate net longwave radiation
        temp_k = temp_c + 273.15
        sigma = 4.903e-9  # Stefan-Boltzmann constant (MJ/K⁴/m²/day)
        cloud_factor = 1 - 0.0009 * cloud_cover_pct
        rnl = sigma * (temp_k ** 4) * cloud_factor
        
        return rns - rnl

    def calculate_eto(
        self,
        temp_c: float,
        rh_pct: float,
        wind_speed_mps: float,
        solar_rad_w_m2: float,
        pressure_hpa: float = 1013.0,
        cloud_cover_pct: float = 30.0
    ) -> float:
        """
        Calculate reference evapotranspiration using FAO Penman-Monteith.
        
        Args:
            temp_c: Temperature (°C)
            rh_pct: Relative humidity (%)
            wind_speed_mps: Wind speed (m/s)
            solar_rad_w_m2: Solar radiation (W/m²)
            pressure_hpa: Atmospheric pressure (hPa)
            cloud_cover_pct: Cloud cover (%)
            
        Returns:
            ETo in mm/day
        """
        Δ = self.calculate_vapor_pressure_slope(temp_c)
        γ = self.calculate_psychrometric_constant(pressure_hpa)
        es = self.calculate_saturation_vapor_pressure(temp_c)
        ea = self.calculate_actual_vapor_pressure(temp_c, rh_pct)
        rn = self.calculate_net_radiation(solar_rad_w_m2, temp_c, cloud_cover_pct)
        G = 0.0  # Assume soil heat flux is 0 for daily ETo
        u2 = wind_speed_mps
        
        numerator = 0.408 * Δ * (rn - G) + γ * (900 / (temp_c + 273)) * u2 * (es - ea)
        denominator = Δ + γ * (1 + 0.34 * u2)
        
        eto = numerator / denominator
        return max(0.0, eto)

    def update_state(self, new_state: WeatherState, timestamp: Optional[datetime] = None) -> None:
        """
        Update weather state and store in history.
        
        Args:
            new_state: New weather state
            timestamp: Timestamp for state (defaults to now)
        """
        ts = timestamp or datetime.now()
        
        # Calculate ETo
        new_state.eto_mm_day = self.calculate_eto(
            temp_c=new_state.temperature_c,
            rh_pct=new_state.humidity_pct,
            wind_speed_mps=new_state.wind_speed_mps,
            solar_rad_w_m2=new_state.solar_radiation_w_m2,
            pressure_hpa=new_state.pressure_hpa,
            cloud_cover_pct=new_state.cloud_cover_pct
        )
        
        self.state = new_state
        
        # Store in history
        self._historical_data.append((ts, new_state))
        if len(self._historical_data) > self._max_history:
            self._historical_data.pop(0)

    def set_forecast(self, forecast: WeatherForecast) -> None:
        """
        Set a weather forecast.
        
        Args:
            forecast: Weather forecast data
        """
        self.forecasts[forecast.hours_ahead] = forecast

    def get_forecast(self, hours_ahead: int) -> Optional[WeatherForecast]:
        """
        Get weather forecast for specific horizon.
        
        Args:
            hours_ahead: Forecast horizon in hours
            
        Returns:
            Weather forecast or None
        """
        return self.forecasts.get(hours_ahead)

    def simulate_diurnal_cycle(
        self,
        current_time: Optional[time] = None,
        base_temp_c: float = 20.0,
        amplitude_c: float = 10.0
    ) -> WeatherState:
        """
        Simulate diurnal (daily) temperature and solar radiation cycle.
        
        Args:
            current_time: Current time of day (defaults to now)
            base_temp_c: Base temperature (minimum)
            amplitude_c: Temperature amplitude
            
        Returns:
            Simulated weather state
        """
        t = current_time or datetime.now().time()
        hour_of_day = t.hour + t.minute / 60
        
        # Temperature follows a sine wave: peak at 14:00
        temp_phase = (hour_of_day - 10) * (math.pi / 12)
        temp_c = base_temp_c + amplitude_c * (1 + math.sin(temp_phase)) / 2
        
        # Solar radiation: bell curve between 6:00 and 18:00
        if 6 <= hour_of_day < 18:
            solar_phase = (hour_of_day - 6) * (math.pi / 12)
            solar_rad = 1000 * math.sin(solar_phase)
        else:
            solar_rad = 0.0
        
        # Humidity: inversely related to temperature
        humidity_pct = 80 - (temp_c - base_temp_c) * 2
        
        return WeatherState(
            temperature_c=temp_c,
            humidity_pct=max(20, min(95, humidity_pct)),
            solar_radiation_w_m2=solar_rad
        )

    def get_state(self) -> dict:
        """Get weather state as dictionary."""
        return {
            "state": {
                "temperature_c": self.state.temperature_c,
                "humidity_pct": self.state.humidity_pct,
                "wind_speed_mps": self.state.wind_speed_mps,
                "solar_radiation_w_m2": self.state.solar_radiation_w_m2,
                "rainfall_mm": self.state.rainfall_mm,
                "pressure_hpa": self.state.pressure_hpa,
                "cloud_cover_pct": self.state.cloud_cover_pct,
                "eto_mm_day": self.state.eto_mm_day
            },
            "forecast_count": len(self.forecasts)
        }
