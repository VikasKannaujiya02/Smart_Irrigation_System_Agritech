
"""Data validator for sensor and NPK data, including range checking."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Literal, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ValidationRule:
    """Defines a validation rule for a feature."""
    feature: str
    rule_type: Literal["range", "non_negative", "positive"]
    min_value: Optional[float] = None
    max_value: Optional[float] = None


class Validator:
    """Validates sensor and NPK data for correctness."""

    def __init__(self, rules: Optional[List[ValidationRule]] = None):
        self.rules = rules or self._get_default_rules()
        self._validation_report: Optional[pd.DataFrame] = None

    def _get_default_rules(self) -> List[ValidationRule]:
        """Get default validation rules for irrigation system data."""
        return [
            # Sensor node rules
            ValidationRule("soil_moisture", "range", 0, 100),
            ValidationRule("temperature", "range", -40, 80),
            ValidationRule("humidity", "range", 0, 100),
            ValidationRule("battery_voltage", "range", 0, 5.5),
            # NPK node rules
            ValidationRule("nitrogen", "non_negative"),
            ValidationRule("phosphorus", "non_negative"),
            ValidationRule("potassium", "non_negative"),
            ValidationRule("ec", "non_negative"),
            ValidationRule("ph", "range", 0, 14),
            ValidationRule("soil_temp", "range", -40, 80),
            ValidationRule("soil_moisture_npk", "range", 0, 100)
        ]

    def validate(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate data and return a validation report."""
        logger.info("Starting data validation")
        report = []
        data = data.copy()
        
        for rule in self.rules:
            if rule.feature not in data.columns:
                continue
            mask = self._apply_rule(data[rule.feature], rule)
            invalid_count = (~mask).sum()
            report.append({
                "feature": rule.feature,
                "rule_type": rule.rule_type,
                "total_values": len(data),
                "invalid_count": invalid_count,
                "invalid_percent": (invalid_count / len(data)) * 100 if len(data) > 0 else 0
            })
            data[f"{rule.feature}_is_valid"] = mask
        
        self._validation_report = pd.DataFrame(report)
        return data

    def _apply_rule(self, series: pd.Series, rule: ValidationRule) -> pd.Series:
        """Apply a single validation rule."""
        if rule.rule_type == "range":
            return series.between(rule.min_value, rule.max_value, inclusive="both")
        elif rule.rule_type == "non_negative":
            return series >= 0
        elif rule.rule_type == "positive":
            return series > 0
        return pd.Series([True] * len(series), index=series.index)

    def get_validation_report(self) -> Optional[pd.DataFrame]:
        """Get the last validation report."""
        return self._validation_report

    def add_rule(self, rule: ValidationRule) -> None:
        """Add a new validation rule."""
        self.rules.append(rule)

    def remove_rule(self, feature: str) -> None:
        """Remove all rules for a specific feature."""
        self.rules = [r for r in self.rules if r.feature != feature]

    def get_invalid_rows(self, data: pd.DataFrame) -> pd.DataFrame:
        """Get rows that failed any validation."""
        validated_data = self.validate(data)
        valid_cols = [col for col in validated_data.columns if col.endswith("_is_valid")]
        if not valid_cols:
            return pd.DataFrame()
        invalid_mask = ~validated_data[valid_cols].all(axis=1)
        return validated_data[invalid_mask]
