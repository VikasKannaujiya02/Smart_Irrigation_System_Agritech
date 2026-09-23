"""Dataset validator for irrigation system data."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of dataset validation."""

    is_valid: bool
    issues: List[str]
    statistics: Dict[str, Any]
    sample_size: int


@dataclass
class RangeRule:
    """Defines a range validation rule for a feature."""

    feature: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allow_null: bool = True


class DatasetValidator:
    """Validates the merged irrigation dataset for completeness and correctness."""

    def __init__(self, custom_rules: Optional[List[RangeRule]] = None) -> None:
        """
        Initialize the dataset validator.

        Args:
            custom_rules: Optional list of custom validation rules.
        """
        self.custom_rules = custom_rules or []
        self._validation_report: Optional[pd.DataFrame] = None
        self._statistics: Optional[Dict[str, Any]] = None

    def validate(
        self,
        data: pd.DataFrame,
        required_columns: Optional[List[str]] = None,
    ) -> ValidationResult:
        """
        Validate the dataset.

        Args:
            data: DataFrame to validate.
            required_columns: List of required column names.

        Returns:
            ValidationResult with issues and statistics.
        """
        logger.info("Starting dataset validation")
        issues: List[str] = []
        statistics: Dict[str, Any] = {}

        # Basic dataset stats
        statistics["row_count"] = len(data)
        statistics["column_count"] = len(data.columns)
        statistics["missing_values"] = data.isnull().sum().to_dict()
        statistics["missing_values_total"] = int(data.isnull().sum().sum())

        # Check required columns
        if required_columns:
            missing_cols = [col for col in required_columns if col not in data.columns]
            if missing_cols:
                issues.append(f"Missing required columns: {missing_cols}")

        # Check for empty dataset
        if len(data) == 0:
            issues.append("Dataset is empty")
            return ValidationResult(
                is_valid=False,
                issues=issues,
                statistics=statistics,
                sample_size=0,
            )

        # Check time column if present
        if "timestamp" in data.columns:
            if not pd.api.types.is_datetime64_any_dtype(data["timestamp"]):
                issues.append("timestamp column is not datetime type")
            else:
                statistics["time_range"] = {
                    "start": data["timestamp"].min().isoformat(),
                    "end": data["timestamp"].max().isoformat(),
                }
                if data["timestamp"].is_monotonic_increasing:
                    statistics["time_monotonic"] = True
                else:
                    issues.append("timestamps are not monotonically increasing")
                    statistics["time_monotonic"] = False

        # Check for duplicates
        duplicate_count = data.duplicated().sum()
        if duplicate_count > 0:
            issues.append(f"Found {duplicate_count} duplicate rows")
        statistics["duplicate_count"] = int(duplicate_count)

        # Apply range rules
        all_rules = self._get_default_rules() + self.custom_rules
        rule_issues = self._apply_range_rules(data, all_rules)
        issues.extend(rule_issues)

        # Generate feature statistics
        statistics["feature_stats"] = self._calculate_feature_statistics(data)

        self._statistics = statistics
        self._validation_report = self._generate_report(data, all_rules)

        is_valid = len(issues) == 0
        logger.info(f"Validation complete: {'PASS' if is_valid else 'FAIL'} with {len(issues)} issues")

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            statistics=statistics,
            sample_size=len(data),
        )

    def _get_default_rules(self) -> List[RangeRule]:
        """Get default validation rules for irrigation system features."""
        return [
            # Sensor node features
            RangeRule("soil_moisture_percent", 0, 100, allow_null=True),
            RangeRule("temperature_c", -40, 80, allow_null=True),
            RangeRule("humidity_percent", 0, 100, allow_null=True),
            RangeRule("battery_voltage", 0, 5.5, allow_null=True),
            RangeRule("battery_percent", 0, 100, allow_null=True),
            # NPK features
            RangeRule("nitrogen_mg_kg", 0, None, allow_null=True),
            RangeRule("phosphorus_mg_kg", 0, None, allow_null=True),
            RangeRule("potassium_mg_kg", 0, None, allow_null=True),
            RangeRule("ph", 0, 14, allow_null=True),
            RangeRule("electrical_conductivity", 0, None, allow_null=True),
            # Weather features
            RangeRule("rainfall_mm", 0, None, allow_null=True),
            RangeRule("wind_speed_mps", 0, None, allow_null=True),
            RangeRule("pressure_hpa", 800, 1100, allow_null=True),
        ]

    def _apply_range_rules(
        self,
        data: pd.DataFrame,
        rules: List[RangeRule],
    ) -> List[str]:
        """Apply range validation rules."""
        issues: List[str] = []
        for rule in rules:
            if rule.feature not in data.columns:
                continue

            series = data[rule.feature]

            # Check nulls
            if not rule.allow_null and series.isnull().any():
                null_count = series.isnull().sum()
                issues.append(f"{rule.feature} has {null_count} null values but nulls not allowed")

            # Check range on non-null values
            non_null = series.dropna()
            if len(non_null) == 0:
                continue

            if rule.min_value is not None:
                below_min = (non_null < rule.min_value).sum()
                if below_min > 0:
                    issues.append(f"{rule.feature}: {below_min} values below min ({rule.min_value})")

            if rule.max_value is not None:
                above_max = (non_null > rule.max_value).sum()
                if above_max > 0:
                    issues.append(f"{rule.feature}: {above_max} values above max ({rule.max_value})")

        return issues

    def _calculate_feature_statistics(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate statistics for numeric features."""
        stats: Dict[str, Any] = {}
        numeric_cols = data.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            series = data[col].dropna()
            if len(series) > 0:
                stats[col] = {
                    "mean": float(series.mean()),
                    "std": float(series.std()),
                    "min": float(series.min()),
                    "max": float(series.max()),
                    "median": float(series.median()),
                    "count": int(len(series)),
                    "missing": int(data[col].isnull().sum()),
                }

        return stats

    def _generate_report(
        self,
        data: pd.DataFrame,
        rules: List[RangeRule],
    ) -> pd.DataFrame:
        """Generate a detailed validation report DataFrame."""
        report_data = []

        for col in data.columns:
            col_stats = {
                "column": col,
                "dtype": str(data[col].dtype),
                "count": int(len(data[col])),
                "missing": int(data[col].isnull().sum()),
                "missing_percent": float((data[col].isnull().sum() / len(data)) * 100),
            }

            # Numeric stats
            if pd.api.types.is_numeric_dtype(data[col]):
                col_stats.update({
                    "mean": float(data[col].mean()) if not data[col].isnull().all() else None,
                    "std": float(data[col].std()) if not data[col].isnull().all() else None,
                    "min": float(data[col].min()) if not data[col].isnull().all() else None,
                    "max": float(data[col].max()) if not data[col].isnull().all() else None,
                })

            # Check if rule exists
            rule = next((r for r in rules if r.feature == col), None)
            if rule:
                col_stats["has_rule"] = True
                col_stats["rule_min"] = rule.min_value
                col_stats["rule_max"] = rule.max_value
            else:
                col_stats["has_rule"] = False

            report_data.append(col_stats)

        return pd.DataFrame(report_data)

    def get_validation_report(self) -> Optional[pd.DataFrame]:
        """Get the detailed validation report."""
        return self._validation_report

    def get_statistics(self) -> Optional[Dict[str, Any]]:
        """Get the dataset statistics."""
        return self._statistics

    def export_report(self, output_path: str | Path) -> None:
        """Export the validation report to a file."""
        if self._validation_report is not None:
            self._validation_report.to_csv(output_path, index=False)
            logger.info(f"Exported validation report to {output_path}")
