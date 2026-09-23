"""Water productivity calculator.

Integrates with the existing pump runtime / water-usage data.

Units: all water in LITRES (consistent with existing analytics_engine.py).
       yield in kg.

Data provenance
───────────────
water_used_liters   SOURCE = pump_records (irrigation history)
actual_yield_kg     SOURCE = harvest_measurement / farmer_input
water_productivity  SOURCE = calculated (actual_yield / total_water_used)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class WaterProductivityCalculator:
    """Compute water productivity metrics when real data is available.

    Internal unit convention:
        Water  → litres (L)
        Yield  → kilograms (kg)
        Result → kg/L  (water productivity)
                 L/kg  (water cost per unit yield)
    """

    def calculate(
        self,
        actual_yield_kg: Optional[float],
        water_used_liters: Optional[float],
    ) -> Dict[str, Any]:
        """Compute water productivity report.

        All results have explicit SOURCE annotations.
        Returns ``"Not Available"`` strings when inputs are missing; never
        fabricates values.
        """
        result: Dict[str, Any] = {
            "actual_yield_kg": actual_yield_kg,
            "water_used_liters": water_used_liters,
            "actual_yield_source": (
                "harvest_measurement / farmer_input" if actual_yield_kg is not None
                else "not_available — awaiting harvest entry"
            ),
            "water_used_source": (
                "pump_records / irrigation_history" if water_used_liters is not None
                else "not_available — awaiting irrigation records"
            ),
            "water_productivity_kg_per_liter": None,
            "water_cost_liters_per_kg": None,
            "calculation_available": False,
            "unit_note": "Water: litres (L) | Yield: kilograms (kg)",
        }

        if actual_yield_kg is None and water_used_liters is None:
            result["summary"] = (
                "Water productivity cannot be calculated: neither yield nor water data available."
            )
            return result

        if actual_yield_kg is not None and water_used_liters is not None:
            if water_used_liters > 0 and actual_yield_kg >= 0:
                wp = actual_yield_kg / water_used_liters
                result["water_productivity_kg_per_liter"] = round(wp, 6)
                result["water_productivity_kg_per_liter_source"] = (
                    "calculated (actual_yield_kg / water_used_liters)"
                )
                if actual_yield_kg > 0:
                    wc = water_used_liters / actual_yield_kg
                    result["water_cost_liters_per_kg"] = round(wc, 3)
                    result["water_cost_liters_per_kg_source"] = (
                        "calculated (water_used_liters / actual_yield_kg)"
                    )
                result["calculation_available"] = True
                result["summary"] = (
                    f"Water Productivity: {wp:.4f} kg/L | "
                    f"Water used per kg: {result.get('water_cost_liters_per_kg', 'N/A')} L/kg"
                )
            elif water_used_liters == 0:
                result["summary"] = "Water used is zero — cannot compute productivity."
            else:
                result["summary"] = "Invalid input values for water productivity calculation."

        elif actual_yield_kg is not None:
            result["summary"] = (
                f"Actual yield available ({actual_yield_kg:.2f} kg). "
                "Awaiting irrigation records for water productivity calculation."
            )
        else:
            result["summary"] = (
                f"Water used available ({water_used_liters:.1f} L). "
                "Awaiting harvest entry for water productivity calculation."
            )

        return result

    def from_pump_records(
        self,
        actual_yield_kg: Optional[float],
        pump_records: list,
    ) -> Dict[str, Any]:
        """Convenience method — sums volume from existing pump records.

        Uses the same volume extraction logic as analytics_engine.py.
        SOURCE: pump_records from existing PumpStatus database table.
        """
        total_liters: float = 0.0
        for rec in pump_records:
            vol = getattr(rec, "volume_pumped_liters", None)
            if vol is not None:
                total_liters += float(vol)

        water_used: Optional[float] = total_liters if total_liters > 0 else None
        return self.calculate(actual_yield_kg, water_used)
