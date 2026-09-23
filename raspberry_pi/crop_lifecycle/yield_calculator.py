"""Yield intelligence calculator.

Compares expected vs actual yield and computes performance metrics.

Data provenance
───────────────
expected_yield_kg   SOURCE = ml_prediction (unavailable until validated model exists)
actual_yield_kg     SOURCE = harvest_measurement / farmer_input
yield_difference    SOURCE = calculated
yield_achievement   SOURCE = calculated
prediction_error    SOURCE = calculated
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class YieldCalculator:
    """Safe comparison of expected vs actual yield.

    Rules
    ─────
    - Never fabricate expected yield.
    - Never copy expected → actual.
    - Never compute percentages when either value is None/zero.
    - Always label which values are unavailable instead of showing '--'.
    """

    def compare(
        self,
        expected_yield_kg: Optional[float],
        actual_yield_kg: Optional[float],
    ) -> Dict[str, Any]:
        """Return a yield comparison report.

        All calculated fields have explicit SOURCE labels.
        Returns ``"Not Available"`` strings when inputs are missing.
        """
        result: Dict[str, Any] = {
            "expected_yield_kg": expected_yield_kg,
            "actual_yield_kg": actual_yield_kg,
            "expected_yield_source": (
                "ml_prediction" if expected_yield_kg is not None
                else "not_available — awaiting validated yield prediction model"
            ),
            "actual_yield_source": (
                "harvest_measurement / farmer_input" if actual_yield_kg is not None
                else "not_available — awaiting harvest entry"
            ),
            "yield_difference_kg": None,
            "yield_achievement_pct": None,
            "prediction_error_pct": None,
            "comparison_available": False,
            "source": "calculated",
        }

        if expected_yield_kg is None and actual_yield_kg is None:
            result["summary"] = "Neither expected nor actual yield is available."
            return result

        if expected_yield_kg is not None and actual_yield_kg is not None:
            diff = actual_yield_kg - expected_yield_kg
            result["yield_difference_kg"] = round(diff, 3)
            result["yield_difference_kg_source"] = "calculated (actual - expected)"

            if expected_yield_kg > 0:
                result["yield_achievement_pct"] = round(
                    (actual_yield_kg / expected_yield_kg) * 100, 2
                )
                result["yield_achievement_pct_source"] = "calculated (actual / expected × 100)"

            if actual_yield_kg > 0:
                result["prediction_error_pct"] = round(
                    abs(expected_yield_kg - actual_yield_kg) / actual_yield_kg * 100, 2
                )
                result["prediction_error_pct_source"] = (
                    "calculated (|expected - actual| / actual × 100)"
                )

            result["comparison_available"] = True
            result["summary"] = (
                f"Yield achievement: {result.get('yield_achievement_pct', 'N/A')}% | "
                f"Difference: {diff:+.2f} kg"
            )

        elif actual_yield_kg is not None:
            result["summary"] = (
                f"Actual yield recorded: {actual_yield_kg:.2f} kg. "
                "Expected yield not yet available (no validated prediction model)."
            )

        else:
            result["summary"] = (
                f"Expected yield: {expected_yield_kg:.2f} kg (AI prediction). "
                "Actual yield awaiting harvest entry."
            )

        return result
