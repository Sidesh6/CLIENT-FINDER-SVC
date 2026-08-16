"""
Excel & Spreadsheet Exporter for Direct Freelance Clients.
Exports and automatically syncs high-value freelance leads into formatted Excel (.xlsx) and CSV files.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.database.connection import SessionLocal
from src.database.models import ProjectModel
from src.intelligence.client_contact import GLOBAL_CONTACT_EXTRACTOR, ClientContactDetails
from src.processors.freelance_classifier import (
    GLOBAL_FREELANCE_CLASSIFIER,
    FreelanceClassificationResult,
)


logger = logging.getLogger("ExcelExporter")


class FreelanceExcelExporter:
    """
    Manages persistent Excel workbook for high-priority freelance opportunities.
    """

    DEFAULT_EXCEL_PATH = Path("data/freelance_clients.xlsx")
    DEFAULT_CSV_PATH = Path("data/freelance_clients.csv")

    HEADERS = [
        "ID",
        "Score",
        "Client Type",
        "Engagement",
        "Title",
        "Budget / Rate",
        "Contact Channel",
        "Direct Email",
        "Calendly / Booking",
        "Telegram / Handles",
        "Action Link",
        "Skills",
        "Source",
        "Discovered At",
    ]

    def export(
        self,
        excel_path: Path | str | None = None,
        csv_path: Path | str | None = None,
        min_score: float = 0.0,
        direct_clients_only: bool = True,
    ) -> int:
        """
        Export all matching stored opportunities to Excel and CSV spreadsheets.
        Returns total count of exported records.
        """
        excel_target = Path(excel_path or self.DEFAULT_EXCEL_PATH)
        csv_target = Path(csv_path or self.DEFAULT_CSV_PATH)
        excel_target.parent.mkdir(parents=True, exist_ok=True)
        csv_target.parent.mkdir(parents=True, exist_ok=True)

        with SessionLocal() as session:
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            query = (
                select(ProjectModel)
                .options(selectinload(ProjectModel.opportunity))
                .order_by(ProjectModel.score.desc().nullslast(), ProjectModel.created_at.desc())
            )
            if min_score > 0:
                query = query.where(ProjectModel.score >= min_score)

            projects = session.scalars(query).all()

        rows: list[dict[str, Any]] = []
        for p in projects:
            cls_res: FreelanceClassificationResult = GLOBAL_FREELANCE_CLASSIFIER.classify({
                "title": p.title,
                "description": p.description,
                "source": p.source,
                "is_direct_client": p.source in ("Client Leads", "Upwork", "Hacker News"),
            })


            if direct_clients_only and not cls_res.is_direct_client:
                continue

            contact: ClientContactDetails = GLOBAL_CONTACT_EXTRACTOR.extract(
                p.description, default_url=p.source_url
            )

            budget_str = f"${p.budget:,.0f} {p.currency or 'USD'}" if p.budget else "Milestone Quote"
            skills_str = ", ".join(p.skills or [])
            score_val = round(p.score, 1) if p.score is not None else 0.0
            emails_str = ", ".join(contact.emails) if contact.emails else ""
            calendly_str = ", ".join(contact.calendly_links) if contact.calendly_links else ""
            telegram_str = ", ".join(contact.telegram_handles) if contact.telegram_handles else ""
            action_url = contact.primary_action_url or p.source_url

            created_str = (
                p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else datetime.now().strftime("%Y-%m-%d %H:%M")
            )

            rows.append({
                "ID": p.id,
                "Score": score_val,
                "Client Type": cls_res.client_type.value,
                "Engagement": cls_res.engagement_type.value,
                "Title": p.title,
                "Budget / Rate": budget_str,
                "Contact Channel": contact.primary_channel,
                "Direct Email": emails_str,
                "Calendly / Booking": calendly_str,
                "Telegram / Handles": telegram_str,
                "Action Link": action_url,
                "Skills": skills_str,
                "Source": p.source,
                "Discovered At": created_str,
            })

        self._write_excel(excel_target, rows)
        self._write_csv(csv_target, rows)
        logger.info("Exported %d freelance leads to %s and %s", len(rows), excel_target, csv_target)
        return len(rows)

    def _write_excel(self, file_path: Path, rows: list[dict[str, Any]]) -> None:
        """Write formatted Excel workbook."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Freelance Clients"

        # Styling definitions
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

        data_font = Font(name="Segoe UI", size=10)
        data_align = Alignment(vertical="center")

        score_high_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")  # light green
        score_med_fill = PatternFill(start_color="FEF9C3", end_color="FEF9C3", fill_type="solid")  # light yellow
        score_high_font = Font(name="Segoe UI", size=10, bold=True, color="166534")
        score_med_font = Font(name="Segoe UI", size=10, bold=True, color="854D0E")

        # 1. Write headers
        for col_idx, header in enumerate(self.HEADERS, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align

        ws.row_dimensions[1].height = 28

        # 2. Write data rows
        for row_idx, r in enumerate(rows, 2):
            ws.row_dimensions[row_idx].height = 22
            for col_idx, key in enumerate(self.HEADERS, 1):
                val = r.get(key, "")
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.font = data_font
                cell.alignment = data_align

                # Score styling
                if key == "Score":
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    score_num = float(val) if isinstance(val, (int, float)) else 0.0
                    if score_num >= 75:
                        cell.fill = score_high_fill
                        cell.font = score_high_font
                    elif score_num >= 50:
                        cell.fill = score_med_fill
                        cell.font = score_med_font

                # Hyperlinks
                if key == "Action Link" and val and str(val).startswith("http"):
                    cell.hyperlink = str(val)
                    cell.font = Font(name="Segoe UI", size=10, color="2563EB", underline="single")
                elif key == "Direct Email" and val and "@" in str(val):
                    first_email = str(val).split(",")[0].strip()
                    cell.hyperlink = f"mailto:{first_email}"
                    cell.font = Font(name="Segoe UI", size=10, color="2563EB", underline="single")

        # 3. Auto-fit column widths
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 45)

        ws.freeze_panes = "A2"
        wb.save(file_path)

    def _write_csv(self, file_path: Path, rows: list[dict[str, Any]]) -> None:
        """Write standard CSV export."""
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.HEADERS)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)


GLOBAL_EXCEL_EXPORTER = FreelanceExcelExporter()
