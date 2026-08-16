"""
Unit tests for FreelanceExcelExporter.
"""

from pathlib import Path

from src.analytics.excel_exporter import FreelanceExcelExporter


def test_excel_and_csv_export(tmp_path: Path):
    excel_file = tmp_path / "test_freelance.xlsx"
    csv_file = tmp_path / "test_freelance.csv"

    exporter = FreelanceExcelExporter()
    count = exporter.export(excel_path=excel_file, csv_path=csv_file, min_score=0.0)

    assert count >= 0
    assert excel_file.exists()
    assert csv_file.exists()
    assert excel_file.stat().st_size > 0
    assert csv_file.stat().st_size > 0
