"""Monthly and periodic report generation."""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, Optional

from .models import AnalyticsReport
from .analytics_engine import AnalyticsEngine

logger = logging.getLogger(__name__)


class MonthlyReportGenerator:
    """
    Generate monthly analytics reports.
    """

    def __init__(self, engine: AnalyticsEngine):
        self.engine = engine
        self.reports: Dict[str, AnalyticsReport] = {}

    def generate_monthly_report(self, year: int, month: int) -> AnalyticsReport:
        """
        Generate a monthly analytics report.
        
        Args:
            year: Year
            month: Month (1-12)
            
        Returns:
            Complete AnalyticsReport
        """
        start_date = date(year, month, 1)
        
        if month == 12:
            next_month_year = year + 1
            next_month = 1
        else:
            next_month_year = year
            next_month = month + 1
        
        end_date = date(next_month_year, next_month, 1) - timedelta(days=1)
        
        analytics_summary = self.engine.get_full_analytics_summary(start_date, end_date)
        
        report_id = f"report_monthly_{year}_{month:02d}"
        
        report = AnalyticsReport(
            report_id=report_id,
            report_type="monthly",
            start_date=start_date,
            end_date=end_date,
            generated_at=datetime.now(),
            data=analytics_summary
        )
        
        self.reports[report_id] = report
        
        logger.info(f"Generated monthly report for {year}-{month:02d}")
        return report

    def generate_weekly_report(self, start_date: Optional[date] = None) -> AnalyticsReport:
        """
        Generate weekly analytics report.
        """
        if start_date is None:
            start_date = date.today() - timedelta(days=date.today().weekday())
        
        end_date = start_date + timedelta(days=6)
        analytics_summary = self.engine.get_full_analytics_summary(start_date, end_date)
        
        report_id = f"report_weekly_{start_date.isoformat()}"
        report = AnalyticsReport(
            report_id=report_id,
            report_type="weekly",
            start_date=start_date,
            end_date=end_date,
            generated_at=datetime.now(),
            data=analytics_summary
        )
        
        self.reports[report_id] = report
        logger.info("Generated weekly report")
        return report

    def generate_daily_report(self, report_date: Optional[date] = None) -> AnalyticsReport:
        """Generate daily report."""
        if report_date is None:
            report_date = date.today()
        
        analytics_summary = self.engine.get_full_analytics_summary(report_date, report_date)
        
        report_id = f"report_daily_{report_date.isoformat()}"
        report = AnalyticsReport(
            report_id=report_id,
            report_type="daily",
            start_date=report_date,
            end_date=report_date,
            generated_at=datetime.now(),
            data=analytics_summary
        )
        
        self.reports[report_id] = report
        logger.info("Generated daily report")
        return report

    def get_report(self, report_id: str) -> Optional[AnalyticsReport]:
        """Get a previously generated report by ID."""
        return self.reports.get(report_id)

    def list_reports(self) -> list:
        """List all generated reports."""
        return list(self.reports.values())
