"""Convert Jinja2-merged Markdown text (CTM subset) into ReportLab flowables.

Supports exactly the eight-element subset from the CTM requirements: headings
1-2, bold, italic, single-level unordered/ordered lists, a horizontal rule,
and blank-line-separated paragraphs. No ``try/except`` is used anywhere in
this module -- crash-safety (CTM-05) is achieved by construction: every
block/inline classifier is a total function that falls through to a plain
paragraph by default, so malformed or unsupported Markdown can never raise.
"""

import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Flowable, HRFlowable, ListFlowable, ListItem, Paragraph, Spacer

_HEADING_RE = re.compile(r"^#{1,2}(?!#)\s+(.+)$")
_UNORDERED_ITEM_RE = re.compile(r"^[-*]\s+(.+)$")
_ORDERED_ITEM_RE = re.compile(r"^\d+\.\s+(.+)$")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"_(.+?)_")

# CTM-06(b): each Markdown-special character is replaced, in escape_context, by a
# distinct Private Use Area sentinel code point -- never a bare backslash + the
# literal character, since the literal character surviving the escape step is
# exactly what let a merged field's special character pair with a real,
# admin-authored delimiter of the same type (see review.md finding 1). A merged
# field's text therefore contains zero raw "*"/"_"/"#"/leading-"-" characters by
# the time the block/inline classifiers and _BOLD_RE/_ITALIC_RE run, so pairing
# with real Markdown syntax elsewhere in the document is structurally impossible,
# not merely guarded against. These sentinels survive Jinja2's Template.render()
# unchanged (no Jinja2-special meaning), are not touched by
# xml.sax.saxutils.escape() (which only touches "&"/"<"/">"), and do not match
# any block/inline classifier regex in this module.
_SENTINELS = {"*": "", "_": "", "#": "", "-": ""}
_SENTINEL_TO_LITERAL = tuple((sentinel, literal) for literal, sentinel in _SENTINELS.items())


def _inline(text: str) -> str:
    """XML-escape a text run, apply bold/italic markup, then restore escaped literals."""
    escaped = escape(text)
    escaped = _BOLD_RE.sub(r"<b>\1</b>", escaped)
    escaped = _ITALIC_RE.sub(r"<i>\1</i>", escaped)
    for sentinel, literal in _SENTINEL_TO_LITERAL:
        escaped = escaped.replace(sentinel, literal)
    return escaped


class MarkdownPdfConverter:
    """Convert Jinja2-merged Markdown text (CTM subset) into ReportLab flowables."""

    MARKDOWN_SPECIAL_CHARS = ("*", "_", "#")

    @staticmethod
    def escape_context(context: dict) -> dict:
        """Recursively replace Markdown-special characters with sentinels in every leaf string.

        Uses a distinct Private Use Area sentinel per special character (see
        ``_SENTINELS``) rather than a backslash prefix, so the merged text
        contains no raw ``*``/``_``/``#``/leading-``-`` for the Markdown
        classifiers to ever pair with real syntax elsewhere in the document.
        """

        def escape_value(value):
            if isinstance(value, dict):
                return {key: escape_value(val) for key, val in value.items()}
            if isinstance(value, list):
                return [escape_value(item) for item in value]
            if isinstance(value, str):
                escaped = value
                for char in MarkdownPdfConverter.MARKDOWN_SPECIAL_CHARS:
                    escaped = escaped.replace(char, _SENTINELS[char])
                if escaped.startswith("-"):
                    escaped = _SENTINELS["-"] + escaped[1:]
                return escaped
            return value

        return escape_value(context)

    @staticmethod
    def to_flowables(text: str) -> list[Flowable]:
        """Parse Jinja2-merged text (already rendered) into a list of ReportLab flowables."""
        styles = getSampleStyleSheet()
        story: list[Flowable] = []
        for raw_block in re.split(r"\n\s*\n+", text):
            block = raw_block.strip()
            if not block:
                continue
            lines = [line.strip() for line in block.splitlines()]
            story.extend(MarkdownPdfConverter._block_flowables(lines, styles))
        return story

    @staticmethod
    def _block_flowables(lines: list[str], styles) -> list[Flowable]:
        """Classify a single block's lines into the matching flowable(s), defaulting to a paragraph."""
        if len(lines) == 1 and lines[0] == "---":
            return [HRFlowable(width="100%", thickness=1, color=colors.grey), Spacer(1, 12)]

        if len(lines) == 1:
            heading_match = _HEADING_RE.match(lines[0])
            if heading_match:
                level = len(lines[0]) - len(lines[0].lstrip("#"))
                style_name = "Heading1" if level == 1 else "Heading2"
                return [
                    Paragraph(_inline(heading_match.group(1)), styles[style_name]),
                    Spacer(1, 12),
                ]

        if all(_UNORDERED_ITEM_RE.match(line) for line in lines):
            items = [
                ListItem(Paragraph(_inline(_UNORDERED_ITEM_RE.match(line).group(1)), styles["Normal"]))
                for line in lines
            ]
            return [ListFlowable(items, bulletType="bullet"), Spacer(1, 12)]

        if all(_ORDERED_ITEM_RE.match(line) for line in lines):
            items = [
                ListItem(Paragraph(_inline(_ORDERED_ITEM_RE.match(line).group(1)), styles["Normal"])) for line in lines
            ]
            return [ListFlowable(items, bulletType="1"), Spacer(1, 12)]

        paragraph_text = "<br/>".join(lines)
        return [Paragraph(_inline(paragraph_text), styles["Normal"]), Spacer(1, 12)]
