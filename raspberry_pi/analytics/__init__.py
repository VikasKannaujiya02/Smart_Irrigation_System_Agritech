"""Analytics Module for AI Smart Irrigation Digital Twin.

This module provides comprehensive analytics capabilities including:
- Water Consumption & Savings Tracking
- Prediction Accuracy Analysis
- Pump & Battery Statistics
- Sensor Health & Crop Performance
- Weather Impact Analysis
- Monthly Reports
- CSV/PDF Exports
- Trend Analysis
"""

from .analytics_engine import AnalyticsEngine
from .export import CSVExporter, PDFExporter
from .reports import MonthlyReportGenerator
from .trends import TrendAnalyzer

__all__ = [
    "AnalyticsEngine",
    "CSVExporter",
    "PDFExporter",
    "MonthlyReportGenerator",
    "TrendAnalyzer"
]
