"""Unit tests for pure CSV/PDF report rendering (REP-05)."""

import csv
import io

from app.services.report_export_service import ReportExportService


class TestRenderPdfTable:
    def test_produces_non_empty_pdf_bytes(self):
        sections = [("Presenças", ["Evento", "Data"], [["Aula 1", "10/01/2026"]])]

        content = ReportExportService.render_pdf_table("Relatório", sections)

        # Same magic-byte assertion style as test_contract_pdf_service.py.
        assert content.startswith(b"%PDF-")
        assert len(content) > 0

    def test_multi_section_input_produces_one_table_per_section(self):
        sections = [
            ("Pagamentos", ["Aluno", "Valor"], [["Fulano", "R$ 150,00"]]),
            ("Inadimplência", ["Aluno", "Valor Devido"], [["Beltrano", "R$ 50,00"]]),
            ("Projeção", ["Total Mensal"], [["R$ 200,00"]]),
        ]

        content = ReportExportService.render_pdf_table("Relatório Financeiro", sections)

        assert content.startswith(b"%PDF-")
        assert len(content) > 0

    def test_section_with_zero_rows_still_renders(self):
        sections = [("Presenças", ["Evento", "Data"], [])]

        content = ReportExportService.render_pdf_table("Relatório", sections)

        assert content.startswith(b"%PDF-")

    def test_title_with_markup_special_characters_does_not_raise(self):
        """Regression: unescaped '<', '>', '&' in a title/section title crashed ReportLab's Paragraph parser."""
        sections = [
            (
                "Presenças - Aula <Avançado>",
                ["Evento", "Data"],
                [["<b>unclosed & bold", "10/01/2026"]],
            )
        ]

        content = ReportExportService.render_pdf_table("Exame de Faixa - <b>unclosed bold", sections)

        assert content.startswith(b"%PDF-")
        assert len(content) > 0


class TestRenderCsv:
    def test_single_section_emits_title_header_and_rows(self):
        sections = [("Presenças", ["Evento", "Data"], [["Aula 1", "10/01/2026"], ["Aula 2", "12/01/2026"]])]

        content = ReportExportService.render_csv(sections)
        text = content.decode("utf-8")

        assert "Presenças" in text
        assert "Evento,Data" in text
        assert "Aula 1,10/01/2026" in text
        assert "Aula 2,12/01/2026" in text

    def test_multi_section_input_produces_one_title_header_data_block_per_section(self):
        sections = [
            ("Pagamentos", ["Aluno", "Valor"], [["Fulano", "150.00"]]),
            ("Inadimplência", ["Aluno", "Valor Devido"], [["Beltrano", "50.00"]]),
            ("Projeção", ["Total Mensal", "Meses", "Total Projetado"], [["150.00", "3", "450.00"]]),
        ]

        content = ReportExportService.render_csv(sections)
        text = content.decode("utf-8")

        assert "Pagamentos" in text
        assert "Inadimplência" in text
        assert "Projeção" in text
        # Blank-line separated: at least two blank lines between the three sections.
        assert text.count("\r\n\r\n") >= 2 or text.count("\n\n") >= 2

    def test_section_with_zero_rows_still_emits_its_header_row(self):
        sections = [("Presenças", ["Evento", "Data"], [])]

        content = ReportExportService.render_csv(sections)
        text = content.decode("utf-8")

        assert "Evento,Data" in text

    def test_cell_values_starting_with_formula_trigger_characters_are_neutralized(self):
        """Regression: cell values starting with =, +, -, @ are prefixed with a leading apostrophe (CWE-1236)."""
        sections = [
            (
                "Pagamentos",
                ["Método"],
                [
                    ["=cmd|'/c calc'!A1"],
                    ["+1234"],
                    ["-5 students"],
                    ["@SUM(A1:A2)"],
                    ["Pix"],
                ],
            )
        ]

        content = ReportExportService.render_csv(sections)
        rows = list(csv.reader(io.StringIO(content.decode("utf-8"))))
        data_rows = [row[0] for row in rows if row and row[0] not in ("Pagamentos", "Método")]

        assert data_rows == [
            "'=cmd|'/c calc'!A1",
            "'+1234",
            "'-5 students",
            "'@SUM(A1:A2)",
            # Legitimate text is left untouched -- it doesn't start with a trigger character.
            "Pix",
        ]
