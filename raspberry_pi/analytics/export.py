"""Export utilities for Analytics: CSV and PDF."""

import logging
import csv
from io import StringIO, BytesIO

from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class CSVExporter:
    """Export analytics data to CSV format."""

    @staticmethod
    def export_dict_list(data: List[Dict[str, Any]], filename: Optional[str] = None) -> StringIO:
        """
        Export a list of dictionaries to CSV.
        
        Args:
            data: List of dictionaries to export
            filename: Optional filename (for saving to disk)
            
        Returns:
            StringIO buffer with CSV content
        """
        if not data:
            return StringIO()
        
        output = StringIO()
        fieldnames = list(data[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        
        if filename:
            file_path = Path(filename)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                f.write(output.getvalue())
            logger.info(f"CSV saved to {file_path}")
        
        output.seek(0)
        return output

    @staticmethod
    def export_water_consumption(records, filename: Optional[str] = None):
        """Export water consumption records."""
        data = [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "volume_liters": r.volume_liters,
                "source": r.source,
                "field_id": r.field_id
            }
            for r in records
        ]
        return CSVExporter.export_dict_list(data, filename)

    @staticmethod
    def export_pump_statistics(records, filename: Optional[str] = None):
        """Export pump runtime records."""
        data = [
            {
                "id": r.id,
                "pump_id": r.pump_id,
                "start_time": r.start_time.isoformat(),
                "end_time": r.end_time.isoformat() if r.end_time else None,
                "runtime_seconds": r.total_runtime_seconds,
                "volume_pumped_liters": r.volume_pumped_liters
            }
            for r in records
        ]
        return CSVExporter.export_dict_list(data, filename)


class PDFExporter:
    """Export analytics reports to PDF."""

    @staticmethod
    def export_report(data: Dict[str, Any], filename: str, title: str = "Irrigation Analytics Report") -> BytesIO:
        """
        Generate a simple PDF report.
        
        Args:
            data: Analytics data to include
            filename: Output filename
            title: Report title
            
        Returns:
            BytesIO buffer with PDF content
        """
        try:
            # We'll use fpdf2 for PDF generation
            from fpdf import FPDF
            
            class PDF(FPDF):
                def header(self):
                    self.set_font("Arial", "B", 12)
                    self.cell(200, 10, title, align="C", ln=True)
                    self.ln(5)
                
                def footer(self):
                    self.set_y(-15)
                    self.set_font("Arial", "I", 8)
                    self.cell(0, 10, f"Page {self.page_no()}", align="C")
            
            pdf = PDF()
            pdf.add_page()
            pdf.set_font("Arial", size=10)
            
            def add_section(title_text, content):
                pdf.set_font("Arial", "B", 11)
                pdf.cell(200, 8, title_text, align="L", ln=True)
                pdf.set_font("Arial", "", 10)
                
                if isinstance(content, dict):
                    for key, val in content.items():
                        if isinstance(val, dict):
                            pdf.multi_cell(0, 6, f"{key}: {val}")
                        elif isinstance(val, list):
                            pdf.multi_cell(0, 6, f"{key}: {len(val)} items")
                        else:
                            pdf.cell(0, 6, f"{key}: {val}", ln=True)
                else:
                    pdf.multi_cell(0, 6, str(content))
                pdf.ln(5)
            
            for section_name, section_data in data.items():
                add_section(section_name.replace("_", " ").title(), section_data)
            
            output = BytesIO()
            pdf.output(output)
            output.seek(0)
            
            if filename:
                file_path = Path(filename)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, "wb") as f:
                    f.write(output.getvalue())
                logger.info(f"PDF saved to {file_path}")
            
            return output
        except ImportError:
            logger.error("fpdf2 library not found. Please install it with: pip install fpdf2")
            raise
