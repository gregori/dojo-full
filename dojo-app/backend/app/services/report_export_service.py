"""Pure rendering of report data to CSV/PDF bytes -- no DB access (REP-05).

Mirrors ``ContractPdfService``'s "no DB writes" discipline: every function
here takes plain data already queried by ``report_service.py`` and returns
bytes. A "section" is ``(title, column_headers, rows)``; a single-section
report is just a one-element list.
"""

import csv
import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

Section = tuple[str, list[str], list[list[str]]]

FORMULA_TRIGGER_CHARS = ("=", "+", "-", "@")


def _neutralize_formula(value: str) -> str:
    """Prefix a cell value with a leading apostrophe if it could be read as a spreadsheet formula (CWE-1236)."""
    if value.startswith(FORMULA_TRIGGER_CHARS):
        return f"'{value}"
    return value


class ReportExportService:
    """Render report sections (title, headers, rows) into CSV or PDF bytes."""

    @staticmethod
    def render_csv(sections: list[Section]) -> bytes:
        """Write each section as a title line, a header row, and data rows, blank-line separated."""
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        for index, (title, headers, rows) in enumerate(sections):
            if index > 0:
                writer.writerow([])
            writer.writerow([title])
            writer.writerow(headers)
            for row in rows:
                writer.writerow([_neutralize_formula(value) for value in row])
        return buffer.getvalue().encode("utf-8")

    @staticmethod
    def render_pdf_table(title: str, sections: list[Section]) -> bytes:
        """Render one table per section under a shared report title (same A4/SimpleDocTemplate scaffold as ContractPdfService)."""
        styles = getSampleStyleSheet()
        story = [Paragraph(escape(title), styles["Title"]), Spacer(1, 12)]

        for section_title, headers, rows in sections:
            story.append(Paragraph(escape(section_title), styles["Heading2"]))
            story.append(Spacer(1, 6))
            table = Table([headers, *rows], hAlign="LEFT")
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 18))

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        doc.build(story)
        return buffer.getvalue()
