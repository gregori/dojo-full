# Requirements — Contract Template Markdown Rendering (CTM)

## Status

Reviewed by `requirements-reviewer` (see `.workflow/runs/contract-markdown-rendering/review-requirements.md`) — NOT APPROVED on one blocking finding (CTM-06 gap), now resolved. CTM-05 and CTM-06 rewritten, CTM-04 fixture reference tightened, two non-blocking boundary questions answered ("Boundary clarifications" under the Markdown-subset table). Per the review's own decision gate, this does not require a second full review round — ready to proceed directly to `tech-analyst`. Standalone, bounded feature — **not** part of Epic 2 (`.workflow/epic-02/handoff.md`), which is fully shipped (PR-5 open, all phases complete). No interview session was re-run on the core technical direction below, since that decision was already made explicitly by the user before this document was written (see "Decision already locked in").

## Context

The dojo's legal contract template system (Epic 2 Phase 4, shipped) stores `ContractTemplateVersion.body` as plain text with Jinja2 placeholders (e.g. `{{ student.contract_name }}`). Today:

- Backend: `ContractPdfService.render_pdf` (`dojo-app/backend/app/services/contract_pdf_service.py`) does `Template(template_body).render(**context)`, then splits on `\n\n` and wraps each chunk in a ReportLab `Paragraph` — blank-line paragraphs only, no formatting.
- Frontend: `ContractTemplatesPage.tsx` authors the body in a plain `<textarea>`; the "view" modal renders it with `whitespace-pre-wrap` — raw text, no formatting.

The dojo admin (non-technical, primary persona for this page) found the rendered contract "cru" (raw/unpolished) and asked for visual hierarchy (headings, bold, lists).

## Decision already locked in (do not re-litigate)

The user was presented three options and explicitly chose **Option A**: Markdown authoring in the existing textarea, `react-markdown` for the frontend preview, and a small Markdown-to-ReportLab-flowables converter on the backend — staying on ReportLab, no new PDF engine, no new native/system dependency. Option B (WeasyPrint/HTML+CSS) and Option C (WYSIWYG editor) are rejected for this feature. The user also raised that Reports pages might get similar treatment later — that is explicitly **out of scope** for this feature (future work, no decision made here).

This document resolves the smaller product-level specifics Option A left open: exact Markdown subset, backward compatibility, malformed-input behavior, and the authoring UI's helper text.

## User Persona

**Dojo admin** (non-technical) — authors and maintains the legal contract template body via `ContractTemplatesPage.tsx`. Does not know Markdown syntax by convention; needs simple, visible guidance in the UI. Does not touch code or the PDF-rendering internals.

## Business Outcome

Generated contract PDFs (and their in-app preview) look professionally formatted — with headings, emphasis, and lists — without requiring the admin to learn a new tool, without introducing a heavier PDF pipeline, and without breaking any contract template already in production.

## In Scope — Markdown subset

Only the following Markdown syntax is supported, matching exactly what the backend converter and the frontend preview must handle:

| Element | Syntax | Notes |
|---|---|---|
| Heading level 1 | `# Heading text` | Maps to ReportLab `Heading1` style |
| Heading level 2 | `## Heading text` | Maps to ReportLab `Heading2` style |
| Bold | `**text**` | Maps to ReportLab inline `<b>` tag inside a `Paragraph` |
| Italic | `_text_` | Maps to ReportLab inline `<i>` tag. `*text*` is **not** supported for italics — `*` is reserved as a list-item marker, and supporting both would create ambiguity for a hand-authored, non-technical-user-facing subset |
| Unordered list | `- item` or `* item`, one per line | Single level only — no nested/indented sub-lists |
| Ordered list | `1. item`, one per line | Single level only; marker must be `N.` (dot, not paren) |
| Horizontal rule | A line containing only `---` | Renders as a thin visual rule (e.g. `HRFlowable` or a 1-row `Table`) |
| Paragraph | Blank-line-separated text blocks | Existing behavior, unchanged |

Jinja2 placeholders (`{{ student.contract_name }}` etc.) remain embedded in the Markdown exactly as today. **Merge order does not change**: Jinja2 substitution happens first against the raw template source; the fully-merged text is then parsed as Markdown and converted to PDF flowables. This is a hard constraint, not a design suggestion — the eventual implementation must not substitute placeholders after or during Markdown parsing.

### Boundary clarifications

- **Combined bold+italic (e.g. `***text***`, or `**_text_**`-style nesting) is out of scope.** It is not part of the eight-element subset and is not specially recognized or rendered as combined emphasis. When an admin writes it, it falls under CTM-05's graceful-degradation rule for out-of-subset/unsupported markup (render as literal text, never crash) — the same as any other unsupported syntax, not a distinct feature to design for.
- **There is no admin-facing escape mechanism for literal `*`, `#`, or leading `-` characters in this feature.** An admin who wants to type a literal `*`, `#`, or a line that legitimately starts with `-` (not intending Markdown syntax) has no way to prevent it from being interpreted as such — this is an accepted limitation of the deliberately small, non-technical-facing subset (consistent with CTM-09's "avoid overengineering" constraint) and can be revisited as follow-up work if it proves to be a real problem for admins. This is distinct from CTM-06 below, which governs *Jinja2-merged field values only* (student/plan data), not text the admin types directly into the template body.

## Explicit Non-Goals

- Heading levels 3 and deeper (`###`+) — not supported; see CTM-05 for how they degrade.
- Nested/multi-level lists (indented sub-items) — not supported; see CTM-05.
- Links, images, tables, inline/fenced code, blockquotes, strikethrough, task lists, footnotes — no business need identified, explicitly excluded.
- Any new PDF rendering engine (e.g. WeasyPrint) or new system/native dependency — the ReportLab-only constraint from Option A is unchanged.
- Any change to the Reports pages (`ReportsPage.tsx`, `report_export_service.py`) — explicitly future/out-of-scope work, not touched by this feature even though the same visual-formatting need may apply there later.
- Live/inline Markdown preview while typing in the authoring `<textarea>` — the textarea stays plain text; formatted preview is only available via the existing "view" modal after a version is saved, unchanged from today's interaction pattern.
- Client-side placeholder substitution — the preview modal shows placeholders as literal text (e.g. the reader sees `{{ student.contract_name }}` verbatim, formatted around by any surrounding Markdown), never substituted; real substitution only happens server-side at actual PDF-generation time.

## Acceptance Criteria

**CTM-01 — Authoring.** The dojo admin can write a template body in the existing `ContractTemplatesPage.tsx` `<textarea>` using the supported Markdown subset (headings 1-2, bold, italic, single-level unordered/ordered lists, horizontal rule, blank-line paragraphs) exactly as they do today for plain paragraphs; no new authoring control (e.g. toolbar buttons) is required.

**CTM-02 — Preview rendering.** The "view" modal renders `viewVersion.body` using `react-markdown`, visually applying the supported subset (heading sizes, bold/italic, bulleted/numbered list markers, a horizontal rule) instead of today's `whitespace-pre-wrap` raw text. Jinja2 placeholders remain visible as literal, unsubstituted text within this preview.

**CTM-03 — PDF rendering.** At PDF-generation time (`ContractPdfService.render_pdf` or an equivalent converter it calls), the merge order is: (1) Jinja2-render the raw Markdown source against the context, exactly as today; (2) parse the fully-merged text as Markdown and convert it to ReportLab flowables — headings to `Heading1`/`Heading2` paragraph styles, bold/italic to inline `<b>`/`<i>` tags inside a `Paragraph`, unordered/ordered lists to `ListFlowable`/`ListItem`, a horizontal rule to a visual rule flowable, and blank-line-separated blocks to `Paragraph` (preserving today's plain-paragraph behavior exactly).

**CTM-04 — Backward compatibility.** Every `ContractTemplateVersion` row already in the database (plain text, no Markdown syntax) continues to render identically to its current behavior, in both the preview modal and the generated PDF — paragraphs only, no unexpected headings/bold/lists/rules are introduced by the new parser for text that contains no Markdown syntax. Covered by a regression test using at least one real existing template body: the two plain-text fixture bodies already present in `dojo-app/backend/tests/unit/test_contract_pdf_service.py`'s `TestRenderPdf` class are sufficient and do not need to be replaced or newly sourced from the database — `"Contrato de {{ student.contract_name }}.\n\nPlano: {{ plan_tier.name }}."` (used in `test_produces_non_empty_pdf_bytes`) and `"Corpo do contrato."` (used in `test_signature_image_increases_output_size`). Extending the assertions on these existing bodies (or adding an equivalent new test in the same style) to check that output is unchanged — paragraphs only, no headings/bold/lists/rules introduced — is sufficient to satisfy this criterion.

**CTM-05 — Graceful degradation (required, not a nice-to-have).** Malformed or out-of-subset Markdown input, written directly by the admin in the template body, never raises an exception and never causes PDF generation to fail. The converter must handle at least the following cases without crashing, using the specified fallback rendering — this is the required, testable minimum, not an open-ended "best effort":

1. An unclosed/unbalanced `**bold` or `_italic` marker: renders with the literal marker characters visible (e.g. `**bold` renders as the literal text `**bold`), never applied as if it were balanced.
2. A `###`-or-deeper heading marker: renders as an ordinary paragraph, with the literal `#` characters kept as plain text.
3. An indented/nested list item: renders as a flat, top-level list item (no indentation applied).
4. Any other unbalanced or unsupported markup not covered by 1-3: renders as literal plain text.

In every case, the offending text must still appear in the rendered output as literal content — it must never be silently dropped/omitted, and it must never cause an exception. This mirrors the existing defensive precedent in `report_export_service.py`, which needed a HIGH-severity fix for exactly this class of bug (unescaped/unexpected characters breaking a ReportLab `Paragraph`) — that class of failure must not recur here.

**CTM-06 — Merge-field literal rendering (ReportLab markup AND Markdown syntax).** Jinja2-merged student/plan data must render as literal text with respect to **both** of the following, and both are required:

(a) **ReportLab-XML markup.** Literal ReportLab-markup-special characters (e.g. `<`, `>`, `&`) present in merged data (for example a `contract_name` containing an ampersand) are escaped before ReportLab inline markup (`<b>`/`<i>`) is applied, so merged field values can never break `Paragraph` rendering. `ContractPdfService.render_pdf` does not currently escape merged text before constructing its `Paragraph` (unlike `report_export_service.py`'s `render_pdf_table`, which already escapes titles) — this is a pre-existing gap that Markdown rendering must not inherit or worsen, and this feature is the vehicle for closing it.

(b) **Markdown syntax.** Because CTM-03 mandates that the fully Jinja2-merged text is parsed as Markdown, any merged field value (e.g. `student.contract_name`, `student.address` — itself a concatenation of `address_street`/`address_neighborhood`/`address_city`/`address_zip`, all free-text DB columns, per `ContractPdfService.build_context` — `plan_tier.name`, etc.) that itself contains a Markdown-special character (`*`, `_`, `#`, or a leading `-`, `1.`, or `---` at the start of a line after merge) must render as literal text. It must never be interpreted by the Markdown parser as bold/italic/heading/list-item/horizontal-rule syntax, and it must never combine with Markdown syntax located elsewhere in the document to produce unintended formatting (e.g. a stray `*` inside a merged field must not pair with a `*` elsewhere in the template body to open an unintended bold/italic span). This closes a content-corruption risk distinct from (a): a merge field colliding with Markdown syntax would not raise an exception and would not be caught by CTM-05's crash-safety criterion, but could silently misformat a signed legal contract. At least one dedicated test case is required covering a merge value containing `*`, `_`, `#`, or a leading `-`, asserting both that (1) the character renders literally rather than as formatting, and (2) it does not alter the rendering of any other paragraph in the document.

The exact mechanism for (b) — e.g. escaping Markdown-special characters within merged values before or independently of the Jinja2 render, or otherwise preventing the Markdown parser from recognizing merged-in text as syntax — is a technical design decision left to `tech-analyst`; this criterion states the required outcome, not the implementation.

**CTM-05 / CTM-06 interaction.** These are two distinct, both-required acceptance criteria covering two distinct failure classes, and neither substitutes for the other: CTM-06 is a **content-integrity** guarantee over Jinja2-merged data — a merge field's Markdown-special characters must never even reach the Markdown parser's syntax-detection in the first place, so CTM-06's literal-rendering guarantee takes precedence over, and effectively runs prior to, CTM-05's fallback path. CTM-05 is a **crash-safety** guarantee over the admin's own hand-authored Markdown in the template body — genuinely malformed or out-of-subset syntax the admin typed themselves, which must degrade gracefully rather than crash PDF generation. A correctly implemented CTM-06 means a merge field's stray `*` should never trigger CTM-05's "unbalanced markup" fallback at all, because CTM-06 has already neutralized it as literal text before the parser sees it as a candidate for Markdown syntax.

**CTM-07 — Authoring UI guidance.** The helper text above the textarea in `ContractTemplatesPage.tsx` (today only listing available Jinja2 placeholders) is updated to also state the supported Markdown syntax in plain language for a non-technical admin, e.g. "Você pode usar **negrito**, _itálico_, # e ## para títulos, - para listas, e --- para uma linha divisória."

**CTM-08 — Frontend dependency.** `react-markdown` is an approved new npm dependency, used only for the preview-modal rendering described in CTM-02. No other new frontend dependency is required for this feature.

**CTM-09 — Backend dependency constraint.** This is a small, fixed-subset feature (8 elements, no nesting, no links/tables/code). Any backend Markdown-parsing approach must avoid an unjustifiably heavy new dependency given that subset. Whether to hand-roll a minimal line-based parser or pull in a light existing package (e.g. Python's `markdown`) is a technical design decision left to `tech-analyst` — this requirement states the constraint ("small feature, avoid heavy dependencies") the design must satisfy, not the implementation choice itself.

**CTM-10 — Scope boundary.** No change to `ReportsPage.tsx`, `report_export_service.py`, or any other report-rendering surface; no new PDF engine or native/system dependency (WeasyPrint remains explicitly rejected for this feature); no change to when or where Jinja2 merge happens (still exclusively server-side, at actual PDF-generation time — never client-side, never in the preview modal).

## Constraints

- Stay on ReportLab; no new PDF engine, no new native/system dependency (carried over from the Option A decision).
- Backend: prefer a lightweight solution given the deliberately small Markdown subset (CTM-09).
- Never let malformed admin-authored input crash PDF generation (CTM-05) — this is a required, crash-safety acceptance criterion, tested, not an implicit assumption.
- Jinja2-merged field values must never be interpretable as ReportLab markup or as Markdown syntax (CTM-06) — this is a required, content-integrity acceptance criterion, distinct from and in addition to CTM-05, tested separately (see "CTM-05 / CTM-06 interaction" note under CTM-06).
- Merge order (Jinja2 first, then Markdown → PDF) must not change (CTM-03).
- Per `CLAUDE.md`'s repository-wide testing mandate, every acceptance criterion above must be covered by automated tests: backend unit tests for the Markdown→flowables converter (each supported element, the CTM-04 backward-compat fixture, the CTM-05 malformed-admin-input cases, and the CTM-06 merge-field literal-rendering cases for both ReportLab markup and Markdown syntax) and a frontend test for the preview modal rendering Markdown via `react-markdown`. Exact test file/case breakdown is left to `tech-analyst`'s implementation plan, consistent with how Phase 5's plan documented its own "### Test plan" subsection (see `.workflow/runs/epic-02-plan/plan.md`).

## Open Questions

None blocking. The core technical direction (Option A) was already decided by the user before this document was written; the specifics above (Markdown subset, backward compatibility, degrade-gracefully behavior, helper text, dependency posture) are written as explicit, reasonable defaults per this task's own guidance, rather than re-opening an interview. The one blocking gap found by `requirements-reviewer` (CTM-06 not covering Markdown-syntax injection from merged fields) has been resolved in this revision — see "Status" above and `review-requirements.md`. If `tech-analyst` surfaces a genuine scope-changing ambiguity while designing the converter, route it back to the user at that point rather than treating any of the above as re-litigable without cause.

## Next Agent

Next Agent: tech-analyst
