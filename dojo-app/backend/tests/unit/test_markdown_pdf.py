"""Unit tests for MarkdownPdfConverter (CTM Markdown-to-ReportLab-flowables)."""

from reportlab.platypus import HRFlowable, ListFlowable, Paragraph, Spacer

from app.services.markdown_pdf import MarkdownPdfConverter


def _paragraphs(flowables):
    return [f for f in flowables if isinstance(f, Paragraph)]


class TestToFlowablesSupportedElements:
    def test_heading_level_1(self):
        flowables = MarkdownPdfConverter.to_flowables("# Título")

        paragraph = _paragraphs(flowables)[0]
        assert paragraph.style.name == "Heading1"
        assert paragraph.text == "Título"

    def test_heading_level_2(self):
        flowables = MarkdownPdfConverter.to_flowables("## Subtítulo")

        paragraph = _paragraphs(flowables)[0]
        assert paragraph.style.name == "Heading2"
        assert paragraph.text == "Subtítulo"

    def test_bold_inline(self):
        flowables = MarkdownPdfConverter.to_flowables("Texto com **negrito** aqui.")

        paragraph = _paragraphs(flowables)[0]
        assert "<b>negrito</b>" in paragraph.text

    def test_italic_inline(self):
        flowables = MarkdownPdfConverter.to_flowables("Texto com _itálico_ aqui.")

        paragraph = _paragraphs(flowables)[0]
        assert "<i>itálico</i>" in paragraph.text

    def test_unordered_list(self):
        flowables = MarkdownPdfConverter.to_flowables("- item um\n- item dois")

        list_flowables = [f for f in flowables if isinstance(f, ListFlowable)]
        assert len(list_flowables) == 1
        list_flowable = list_flowables[0]
        assert list_flowable._bulletType == "bullet"
        assert len(list_flowable._content) == 2
        assert list_flowable._content[0]._flowable.text == "item um"
        assert list_flowable._content[1]._flowable.text == "item dois"

    def test_ordered_list(self):
        flowables = MarkdownPdfConverter.to_flowables("1. item um\n2. item dois")

        list_flowables = [f for f in flowables if isinstance(f, ListFlowable)]
        assert len(list_flowables) == 1
        list_flowable = list_flowables[0]
        assert list_flowable._bulletType == "1"
        assert len(list_flowable._content) == 2

    def test_horizontal_rule(self):
        flowables = MarkdownPdfConverter.to_flowables("---")

        hr_flowables = [f for f in flowables if isinstance(f, HRFlowable)]
        assert len(hr_flowables) == 1

    def test_two_plain_paragraphs_unchanged(self):
        flowables = MarkdownPdfConverter.to_flowables("Primeiro parágrafo.\n\nSegundo parágrafo.")

        paragraphs = _paragraphs(flowables)
        assert len(paragraphs) == 2
        assert paragraphs[0].text == "Primeiro parágrafo."
        assert paragraphs[1].text == "Segundo parágrafo."
        assert not any(isinstance(f, ListFlowable | HRFlowable) for f in flowables)

    def test_leading_and_trailing_blank_lines_produce_no_empty_blocks(self):
        flowables = MarkdownPdfConverter.to_flowables("\n\nCorpo do contrato.\n\n")

        paragraphs = _paragraphs(flowables)
        assert len(paragraphs) == 1
        assert paragraphs[0].text == "Corpo do contrato."


class TestToFlowablesMalformedInput:
    """CTM-05 -- malformed/out-of-subset admin-authored Markdown never crashes."""

    def test_unclosed_bold_renders_as_literal_text(self):
        flowables = MarkdownPdfConverter.to_flowables("**bold sem fechar")

        paragraph = _paragraphs(flowables)[0]
        assert "**bold sem fechar" in paragraph.text
        assert "<b>" not in paragraph.text

    def test_heading_level_three_or_deeper_renders_as_plain_paragraph(self):
        flowables = MarkdownPdfConverter.to_flowables("### Cabeçalho nível 3")

        paragraph = _paragraphs(flowables)[0]
        assert paragraph.style.name != "Heading1"
        assert paragraph.style.name != "Heading2"
        assert "###" in paragraph.text

    def test_indented_list_item_renders_flat_top_level(self):
        flowables = MarkdownPdfConverter.to_flowables("  - item indentado")

        list_flowables = [f for f in flowables if isinstance(f, ListFlowable)]
        assert len(list_flowables) == 1
        list_flowable = list_flowables[0]
        assert len(list_flowable._content) == 1
        assert not isinstance(list_flowable._content[0]._flowable, ListFlowable)

    def test_stray_unclosed_italic_marker_renders_as_literal_text(self):
        flowables = MarkdownPdfConverter.to_flowables("_itálico sem fechar")

        paragraph = _paragraphs(flowables)[0]
        assert "itálico sem fechar" in paragraph.text
        assert "<i>" not in paragraph.text

    def test_combined_bold_italic_never_raises_and_keeps_text(self):
        flowables = MarkdownPdfConverter.to_flowables("***texto***")

        paragraph = _paragraphs(flowables)[0]
        assert "texto" in paragraph.text
        # Not rendered as combined bold+italic emphasis (out of scope, CTM-05 fallback).
        assert not ("<b>" in paragraph.text and "<i>" in paragraph.text)


class TestToFlowablesMergeFieldLiteralRendering:
    """CTM-06 -- merge-field values render literally (ReportLab-XML and Markdown syntax)."""

    def test_xml_special_chars_escaped_and_coexist_with_admin_authored_bold(self):
        context = MarkdownPdfConverter.escape_context({"student": {"contract_name": "A & B <Corp>"}})
        rendered = "Contrato de **{{ student.contract_name }}**."
        from jinja2 import Template

        merged = Template(rendered).render(**context)
        flowables = MarkdownPdfConverter.to_flowables(merged)

        paragraph = _paragraphs(flowables)[0]
        assert "&amp;" in paragraph.text
        assert "&lt;Corp&gt;" in paragraph.text
        assert "<b>" in paragraph.text and "</b>" in paragraph.text

    def _render_merged(self, contract_name: str, template: str) -> str:
        from jinja2 import Template

        context = MarkdownPdfConverter.escape_context({"student": {"contract_name": contract_name}})
        return Template(template).render(**context)

    def test_merged_asterisk_renders_literally_and_does_not_bleed_into_other_bold(self):
        merged = self._render_merged(
            "*Nome", "Contrato de {{ student.contract_name }}.\n\nCláusula em **negrito** normal."
        )
        flowables = MarkdownPdfConverter.to_flowables(merged)
        paragraphs = _paragraphs(flowables)

        assert "*Nome" in paragraphs[0].text
        assert "<b>" not in paragraphs[0].text
        assert "<b>negrito</b>" in paragraphs[1].text

    def test_merged_underscore_renders_literally_and_does_not_bleed_into_other_italic(self):
        merged = self._render_merged(
            "_Nome", "Contrato de {{ student.contract_name }}.\n\nCláusula em _itálico_ normal."
        )
        flowables = MarkdownPdfConverter.to_flowables(merged)
        paragraphs = _paragraphs(flowables)

        assert "_Nome" in paragraphs[0].text
        assert "<i>" not in paragraphs[0].text
        assert "<i>itálico</i>" in paragraphs[1].text

    def test_merged_hash_does_not_become_a_heading(self):
        merged = self._render_merged("#Nome", "Contrato de {{ student.contract_name }}.")
        flowables = MarkdownPdfConverter.to_flowables(merged)
        paragraph = _paragraphs(flowables)[0]

        assert "#Nome" in paragraph.text
        assert paragraph.style.name not in ("Heading1", "Heading2")

    def test_merged_leading_hyphen_does_not_become_a_list_item(self):
        merged = self._render_merged("-Nome", "{{ student.contract_name }}")
        flowables = MarkdownPdfConverter.to_flowables(merged)

        assert not any(isinstance(f, ListFlowable) for f in flowables)
        paragraph = _paragraphs(flowables)[0]
        assert "-Nome" in paragraph.text

    def test_merged_asterisk_wrapped_directly_in_real_bold_renders_correctly(self):
        """Review.md finding 1 repro: contract_name ending in '*', wrapped by real **{{ field }}**."""
        merged = self._render_merged("Silva*", "**{{ student.contract_name }}**")
        flowables = MarkdownPdfConverter.to_flowables(merged)
        paragraph = _paragraphs(flowables)[0]

        assert paragraph.text == "<b>Silva*</b>"
        assert "\\" not in paragraph.text

    def test_merged_underscore_same_block_as_unrelated_real_italic_span(self):
        """Review.md finding 1 repro: a stray merged underscore, not adjacent to a real _..._ span."""
        merged = self._render_merged("Silva_", "Nome: {{ student.contract_name }} texto _italico_ fim.")
        flowables = MarkdownPdfConverter.to_flowables(merged)
        paragraph = _paragraphs(flowables)[0]

        assert paragraph.text == "Nome: Silva_ texto <i>italico</i> fim."

    def test_xml_special_chars_and_markdown_special_char_coexist_inside_real_bold(self):
        context = MarkdownPdfConverter.escape_context({"student": {"contract_name": "A & B <Corp>*"}})
        rendered = "**{{ student.contract_name }}**"
        from jinja2 import Template

        merged = Template(rendered).render(**context)
        flowables = MarkdownPdfConverter.to_flowables(merged)
        paragraph = _paragraphs(flowables)[0]

        assert paragraph.text == "<b>A &amp; B &lt;Corp&gt;*</b>"


class TestEscapeContext:
    def test_escapes_special_characters_in_every_nested_leaf(self):
        context = {
            "student": {"contract_name": "A*B", "address": "_Rua_ # 1"},
            "plan_tier": {"name": "-Plano"},
        }

        escaped = MarkdownPdfConverter.escape_context(context)

        # Sentinel-escaped: no raw Markdown-special characters survive in the leaf.
        for char in ("*", "_", "#"):
            assert char not in escaped["student"]["contract_name"]
            assert char not in escaped["student"]["address"]
        assert not escaped["plan_tier"]["name"].startswith("-")

        # Round-tripping through Jinja2 render + _inline restores the literal text.
        from jinja2 import Template

        from app.services.markdown_pdf import _inline

        rendered = Template("{{ student.contract_name }}|{{ student.address }}|{{ plan_tier.name }}").render(**escaped)
        assert _inline(rendered) == "A*B|_Rua_ # 1|-Plano"

    def test_non_string_leaf_values_pass_through_unmodified(self):
        context = {"plan_tier": {"weekly_frequency": 3, "active": True, "extra": None}}

        escaped = MarkdownPdfConverter.escape_context(context)

        assert escaped["plan_tier"]["weekly_frequency"] == 3
        assert escaped["plan_tier"]["active"] is True
        assert escaped["plan_tier"]["extra"] is None

    def test_list_leaf_values_are_escaped(self):
        """Finding 2 (LOW, folded in): a list of dict/str leaves is escaped, not skipped."""
        context = {"plan_tier": {"features": [{"name": "A*B"}, "C_D"]}}

        escaped = MarkdownPdfConverter.escape_context(context)

        assert "*" not in escaped["plan_tier"]["features"][0]["name"]
        assert "_" not in escaped["plan_tier"]["features"][1]
