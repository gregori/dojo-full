# Implementation Plan — Contract Template Markdown Rendering (CTM)

## Status

Design complete (2026-07-26). Source of truth is `requirements.md` (CTM-01–CTM-10, post-fix-pass, approved). This is a standalone, bounded feature — not part of Epic 2. House style follows `.workflow/runs/epic-02-plan/plan.md`'s phase-plan sections (Requirements review / Autocrítica / Intended design / Test plan), scaled down to a single-phase feature.

## Requirements review / ground truth re-confirmed

Re-verified directly against the current codebase before designing (2026-07-26):

- `ContractPdfService.render_pdf` (`dojo-app/backend/app/services/contract_pdf_service.py:65-87`) does `Template(template_body).render(**context)`, splits on `\n\n`, and wraps each chunk in a plain `Paragraph(paragraph_text.replace("\n", "<br/>"), styles["Normal"])` — no escaping of merged text at all today (confirms the CTM-06(a) pre-existing gap named in requirements.md).
- `test_contract_pdf_service.py`'s `TestRenderPdf` class has exactly the two fixture bodies CTM-04 names: `"Contrato de {{ student.contract_name }}.\n\nPlano: {{ plan_tier.name }}."` and `"Corpo do contrato."` — both still used as the backward-compat regression base.
- `report_export_service.py` escapes via `xml.sax.saxutils.escape()` (stdlib, already imported there) and has its own `_neutralize_formula`/`FORMULA_TRIGGER_CHARS` pattern for a different (CSV-formula-injection) concern — the `escape()` precedent is reused here for ReportLab-XML safety, but the CTM-06(b) Markdown-syntax-literal problem is genuinely new and has no existing precedent in this codebase.
- `ContractTemplatesPage.tsx`'s view modal (`ContractTemplatesPage.tsx:202-204`) renders `viewVersion.body` inside a `whitespace-pre-wrap` `<div>` — to be replaced with `react-markdown`. The authoring `<textarea>` (`ContractTemplatesPage.tsx:89-96`) and its helper text (`ContractTemplatesPage.tsx:74-80`) are unchanged in structure; only the helper text copy gains a Markdown-syntax sentence (CTM-07).
- `dojo-app/backend/pyproject.toml` has no Markdown-parsing dependency of any kind; `reportlab` is already `^5.0.0` (fine — no version bump needed).
- `dojo-app/frontend/package.json` has no Markdown dependency; React is `^19.0.0`. `react-markdown@10.1.0` (latest, `npm view` confirmed 2026-07-26) declares `peerDependencies: { react: ">=18", "@types/react": ">=18" }` — compatible, no downgrade needed (satisfies "use latest APIs").
- **New finding, not anticipated by requirements.md:** `dojo-app/frontend/jest.config.cjs` runs `ts-jest` with `module: 'commonjs'` and a transform regex matching only `.tsx?` files. `react-markdown@10.1.0` (and all versions ≥ v6, confirmed via `npm view ... type` = `"module"`) is **ESM-only**, as are its transitive deps (`unified`, `micromark`, `mdast-util-*`, `vfile`, `unist-util-*`, `hast-util-*`, etc. — a large transitive tree). Loading the real package under this Jest config will throw `SyntaxError: Cannot use import statement outside a module` unless Jest is reconfigured. See "Frontend design" below for how this is resolved without adding a new dependency (CTM-08's "no other new frontend dependency" constraint).

## Autocrítica (self-review, performed before committing the design below)

- **Considered using Python's `markdown` package (Python-Markdown) and converting its HTML output to ReportLab flowables.** Rejected: (1) it reintroduces exactly the kind of extra translation layer (Markdown → HTML → ReportLab-XML) that Phase 4's own autocrítica rejected WeasyPrint for — an unneeded intermediate representation for an 8-element, non-nested subset; (2) `*text*` is standard-Markdown italic by default in every general-purpose parser, but CTM's subset deliberately reserves `*` for list markers and only supports `_italic_` — bending a general library to a non-standard subset (suppressing `*`-emphasis, disabling headings 3+, disabling links/tables/code) would need more configuration/output-filtering code than a hand-rolled parser, while still leaving an HTML round-trip to reconcile with ReportLab's own inline-markup dialect (`<b>`/`<i>`, not HTML `<strong>`/`<em>`); (3) it does not close CTM-06(b) for free — the literal-escaping mechanism has to be hand-built regardless of parser choice, since no general Markdown library knows which spans came from Jinja2 merge vs. admin-authored text. **Fixed:** a hand-rolled, line-based parser (CTM-09 explicitly leaves this choice open and flags "avoid unjustifiably heavy dependency given the subset" — a general CommonMark-family parser is unjustified for 8 flat elements).
- **Considered a blanket `try/except Exception` around the whole converter to satisfy CTM-05's "never raise."** Rejected per CLAUDE.md's "do not program defensively; exception handlers only when needed" — swallowing exceptions here would hide real bugs (e.g. a genuine ReportLab API misuse) behind a false sense of safety, and CTM-05's four enumerated cases are all deterministically classifiable by regex with no code path that can raise. **Fixed:** the converter's block/inline classifiers are total functions (every input matches some branch, falling through to the plain-paragraph default) — crash-safety is achieved *by construction*, not by catching exceptions. No `try/except` is added anywhere in the new module. (`render_pdf`'s existing `SimpleDocTemplate.build()` call is unchanged and untouched — a real ReportLab-internal failure there would still surface, which is correct: that's not the CTM-05 "malformed admin Markdown" failure class.)
- **Considered doing CTM-06(b) escaping as a post-Jinja2, whole-document regex pass that tries to detect "template-authored" vs. "merged" spans by diffing rendered output against the raw template.** Rejected: fragile (a diff-based approach breaks the moment a merged value happens to equal a substring of surrounding template text) and re-implements essentially the same backslash-escaping idea with far more complexity and no additional benefit. **Fixed:** escape at the context-leaf level, before Jinja2 substitution (see "CTM-06 escaping design" below) — simpler, deterministic, and exactly the mechanism the requirements doc itself floats as an example ("escaping Markdown-special characters in the context dict's leaf string values before Jinja2 render").
- **Considered mocking nothing and just getting Jest to load real `react-markdown`.** Rejected as the *only* test path: fixing Jest's ESM handling for `react-markdown`'s full transitive tree would require either a new dependency (`babel-jest` + `@babel/preset-env`, to transform node_modules ESM `.js` files that `ts-jest`'s `.tsx?`-only transform regex does not touch) or an ever-growing, fragile `transformIgnorePatterns` allow-list that must be hand-maintained across every future `react-markdown` upgrade. Both conflict with CTM-08's "no other new frontend dependency" constraint and with "avoid overengineering." **Fixed:** `ContractTemplatesPage.test.tsx` mocks `react-markdown` (same `jest.mock(...)` convention already used for `../services/api` in this exact file), which tests *our own* wiring code with zero new tooling; genuine confidence that the real library actually renders headings/bold/lists in a browser is obtained via one added Cypress scenario (real Vite bundle, real ESM, no Jest involved) rather than by fighting Jest's CommonJS transform. This is documented as a real, load-bearing test-layering decision below, not a shortcut — see "Test plan."
- **Considered escaping only `*`/`_`/`#` in merged leaf values and leaving leading `-`/`1.`/`---` unhandled** (reasoning: CTM-06's *required* test list only names "a leading `-`" alongside `*`/`_`/`#`). Rejected as incomplete against CTM-06(b)'s main body text, which also names `1.` and `---` as things a merged value must never be interpreted as. **Fixed:** the leaf-escaping helper also backslash-escapes a leaf value's *leading* `-` (covering both the unordered-list case and, combined with per-character `-` escaping, the `---` rule case, since three literal, unescaped hyphens can no longer appear contiguously at a line start once the first is escaped). A merged value that happens to start with digits followed by `. ` (e.g., a hypothetical `"1. some text"`) remains a known, documented residual gap — out of the required test set, not silently ignored (see "Risk assessment").
- **Checked testability:** every new function (`MarkdownPdfConverter.to_flowables`, `MarkdownPdfConverter.escape_context`) is a plain function taking/returning primitives or ReportLab flowables/dicts — no new abstraction layer, straightforward to unit test with plain string fixtures, no DB/service dependency, matching `ContractPdfService`/`ReportExportService`'s existing "pure rendering" discipline exactly.

## Intended design — backend

### Module structure

New module `dojo-app/backend/app/services/markdown_pdf.py` (separate from `contract_pdf_service.py`, mirroring the existing `report_service.py` / `report_export_service.py` split-by-concern precedent: pure Markdown-to-flowables rendering lives in its own module rather than growing `contract_pdf_service.py` into two responsibilities).

```python
class MarkdownPdfConverter:
    """Convert Jinja2-merged Markdown text (CTM subset) into ReportLab flowables."""

    @staticmethod
    def escape_context(context: dict) -> dict:
        """Backslash-escape Markdown-special characters in every leaf string value."""
        ...

    @staticmethod
    def to_flowables(text: str) -> list:
        """Parse text (already Jinja2-merged) into a list of ReportLab flowables."""
        ...
```

`contract_pdf_service.py` changes to:

```python
rendered = Template(template_body).render(**MarkdownPdfConverter.escape_context(context))
story = MarkdownPdfConverter.to_flowables(rendered)
```

— replacing the current `for paragraph_text in rendered.split("\n\n"): ...` loop. The signature/`Image`/`Spacer` appending after the loop is unchanged.

### Block-level algorithm (`to_flowables`)

1. Split `text` on one-or-more blank lines (`re.split(r"\n\s*\n+", text)`), same granularity as today's `"\n\n"` split — this alone preserves CTM-04 exactly for any block with no Markdown syntax.
2. For each non-empty (stripped) block, classify by inspecting its lines (each line first has *only* trailing/leading whitespace stripped — deliberately not used to detect "indentation," so nested list items flatten to top-level by construction, satisfying CTM-05 case 3):
   - **Horizontal rule:** the block is a single line and, stripped, equals exactly `---` (three hyphens, nothing else) → append `HRFlowable(width="100%", thickness=1, color=colors.grey)` (`reportlab.platypus.HRFlowable`).
   - **Heading:** the block is a single line and matches `^#{1,2}(?!#)\s+(.+)$` — the negative lookahead `(?!#)` excludes `###`+ (CTM-05 case 2: a 3+ `#` line simply fails this match and falls through to the plain-paragraph branch below, keeping its literal `#` characters). Group count of leading `#` selects `styles["Heading1"]` or `styles["Heading2"]`; the heading text runs through the same inline-formatting/escaping pipeline as a paragraph (bold/italic still apply inside a heading, matching CTM-03's "headings to Heading1/Heading2 ... bold/italic to inline tags" wording, which does not say headings are plain-text-only).
   - **Unordered list:** every line in the block matches `^[-*]\s+(.+)$` → one `ListItem(Paragraph(_inline(text), styles["Normal"]))` per line, wrapped in `ListFlowable(items, bulletType="bullet")`.
   - **Ordered list:** every line in the block matches `^\d+\.\s+(.+)$` → same construction with `ListFlowable(items, bulletType="1")` (ReportLab's built-in auto-numbering bullet type).
   - **Default (paragraph):** everything else, including CTM-05 case 4 (any other unbalanced/unsupported markup) and case 2's `###`+ fallthrough — `Paragraph(_inline(block.replace("\n", "<br/>")), styles["Normal"])`, i.e. today's exact existing behavior, now routed through `_inline()` instead of being used raw.
   - A `Spacer(1, 12)` follows each appended flowable, unchanged from today's per-paragraph spacing.
3. `_inline(text) -> str` (module-private helper, applied to every literal text run before it becomes ReportLab `Paragraph`/`ListItem` content):
   - First, XML-escape the *entire* string via `xml.sax.saxutils.escape()` (same stdlib helper `report_export_service.py` already uses) — this closes CTM-06(a) unconditionally, for every text run, admin-authored or merged, with no special-casing needed.
   - Then apply bold: `re.sub(r"\*\*(?<!\\\*\*)(.+?)\*\*", r"<b>\1</b>", text)` (paired, non-greedy; an unpaired `**bold` simply never matches and is left as literal escaped text — CTM-05 case 1).
   - Then apply italic: `re.sub(r"_(.+?)_", r"<i>\1</i>", text)` on the bold-substituted result (paired, non-greedy; unpaired `_italic` likewise falls through unchanged).
   - Finally, un-escape the CTM-06(b) backslash-marker sequences produced by `escape_context` (`\*` → `*`, `\_` → `_`, `\#` → `#`, `\-` → `-`) so the reader sees the intended literal character, not a backslash. This step runs *after* bold/italic substitution specifically because the backslash prevents those regexes from pairing across an escaped character in the first place (a literal `*` from merged data can never pair with a `*` elsewhere in the document — this is what makes CTM-06(b)'s "must not bleed into unrelated formatting" guarantee hold).
   - Order note: XML-escaping first is safe because `\`, `*`, `_`, `#`, `-` are not among `<`, `>`, `&` — the two escaping passes touch disjoint character sets and cannot interfere with each other.

### CTM-06 escaping design (the crux)

**Mechanism: backslash-escape Markdown-special characters in the Jinja2 context's leaf string values, before `Template.render()` is called** — exactly the example the requirements doc itself names as an acceptable approach, and the one chosen here.

```python
MARKDOWN_SPECIAL_CHARS = ("*", "_", "#")

@staticmethod
def escape_context(context: dict) -> dict:
    """Recursively backslash-escape Markdown-special characters in every leaf string."""
    def escape_value(value):
        if isinstance(value, dict):
            return {k: escape_value(v) for k, v in value.items()}
        if isinstance(value, str):
            escaped = value
            for char in MarkdownPdfConverter.MARKDOWN_SPECIAL_CHARS:
                escaped = escaped.replace(char, f"\\{char}")
            if escaped.startswith("-"):
                escaped = f"\\{escaped}"
            return escaped
        return value
    return escape_value(context)
```

Why this satisfies the locked merge order (CTM-03) and both CTM-06 sub-parts:

- **Merge order is unchanged.** `escape_context` runs on the *context dict* (student/plan display strings), not on the template body and not on the already-merged output. `Template(template_body).render(**escaped_context)` is still "Jinja2-render the raw template against the context" — the only difference from today is which strings are substituted in, not when substitution happens or what gets parsed after. Markdown parsing (`to_flowables`) still runs strictly after the (now-escaped) Jinja2 render, exactly as CTM-03 requires.
- **CTM-06(b) — Markdown-syntax literal rendering.** Once a leaf value like `student.contract_name = "J. * Silva"` is escaped to `"J. \* Silva"`, that backslash survives the Jinja2 substitution verbatim (Jinja2 does not interpret backslashes) and lands in the fully-merged text exactly where the placeholder was. `to_flowables`'s bold/italic regexes require an *unescaped* `*`/`_` pair to fire, so this stray `*` can never pair with a real `**...**`/`_..._` written elsewhere in the admin's template — it is inert with respect to the parser's syntax detection from the moment Jinja2 finishes rendering. The final backslash-stripping step in `_inline()` then turns `\*` back into a plain, visible `*` in the rendered output — literal, as required, never formatting, never bleeding into other paragraphs.
- **CTM-06(a) — ReportLab-XML literal rendering.** `_inline()`'s XML-escape pass runs over *every* text run unconditionally (not merge-value-specific), so a merged `<`, `>`, or `&` (e.g. an address or CPF containing one, however unlikely) can never be interpreted as ReportLab markup, closing the pre-existing gap named in the requirements doc without any extra merge-value-specific code path.
- **Independence from CTM-05.** Because CTM-06 neutralizes merge-field special characters *before* the Markdown parser ever sees them as syntax candidates, a stray `*` in merged data never reaches CTM-05's "unbalanced marker" fallback path at all — it was never a candidate in the first place. This matches the "CTM-05 / CTM-06 interaction" note in requirements.md exactly: CTM-06 runs prior to, and takes precedence over, CTM-05.

### CTM-05 crash-safety design

No exception handling is added; crash-safety is a property of the classifiers being total functions (every possible input string falls into exactly one branch, with a plain-paragraph default that can never fail to match). Walking through the four required cases:

1. **Unclosed `**bold` / `_italic`:** the bold/italic regexes in `_inline()` only substitute when a *matching pair* is found (non-greedy, requires both delimiters). An unpaired `**bold` produces zero regex matches, so the string passes through `_inline()` unchanged except for XML-escaping — rendered as the literal text `**bold`, never interpreted as opened-but-unclosed formatting.
2. **`###`+ heading:** the heading classifier's regex `^#{1,2}(?!#)\s+(.+)$` structurally cannot match a line with three or more leading `#` characters (the negative lookahead excludes it). The block therefore falls to the default paragraph branch, where `_inline()` XML-escapes but does not strip `#` characters — rendered as an ordinary paragraph with the literal `#`s visible.
3. **Indented/nested list item:** block lines are stripped of leading/trailing whitespace before the list-item regex is evaluated, and `ListFlowable`/`ListItem` construction never inspects or reproduces original indentation — an indented `  - subitem` is `.strip()`'d to `- subitem`, matches the flat unordered-list regex, and renders as a normal top-level list item. There is no code path that constructs nested `ListFlowable`s, so "no indentation applied" holds by omission, not by a special case.
4. **Any other unbalanced/unsupported markup:** anything not matching the HR/heading/unordered-list/ordered-list classifiers (all of which require the *entire* block, or every line in it, to match) falls to the default paragraph branch — the same catch-all used for cases 1-2 above. Since this branch is the same one today's code already uses for every paragraph (just now routed through `_inline()`), it can never raise: `_inline()` only calls `xml.sax.saxutils.escape()` (pure string transform, cannot raise on any `str` input) and `re.sub()` with fixed patterns (cannot raise on any `str` input). No offending text is ever dropped — it always ends up inside some `Paragraph`'s content string.

Because every branch is reachable only via a successful regex match or the unconditional default, and `_inline()`/`escape_context()` only call total string operations (`str.replace`, `str.startswith`, `re.sub`, `xml.sax.saxutils.escape`, none of which raise on arbitrary `str` input), there is no code path in `MarkdownPdfConverter` that can raise `Exception`. `render_pdf`'s final `doc.build(story)` call is unchanged and outside this guarantee's scope (a genuine ReportLab-internal error there is not a CTM-05 "malformed admin Markdown" failure — it would indicate a bug in flowable construction itself, which should surface, not be swallowed).

## Intended design — frontend

- **Dependency:** add `"react-markdown": "^10.1.0"` to `dojo-app/frontend/package.json` `dependencies` (latest stable, confirmed React-19-compatible peer range). No other new frontend dependency (CTM-08).
- **`ContractTemplatesPage.tsx` view modal (`ContractTemplatesPage.tsx:202-204`):** replace the `whitespace-pre-wrap` `<div>{viewVersion.body}</div>` with:
  ```tsx
  <div className="overflow-y-auto text-sm text-gray-800 border rounded-md p-4 mb-4 prose prose-sm max-w-none">
    <ReactMarkdown>{viewVersion.body}</ReactMarkdown>
  </div>
  ```
  `import ReactMarkdown from 'react-markdown'` added to the top imports. No `remark-*`/`rehype-*` plugins are added — `react-markdown`'s default (CommonMark-ish) parsing already recognizes headings/bold/italic/lists/thematic breaks out of the box, which covers the CTM subset for *preview* purposes; `_italic_`, `**bold**`, `#`/`##`, `-`/`*`/`1.` lists, and `---` are all default-supported. (`*text*`-as-italic is also enabled by default in `react-markdown`, which is a minor, accepted preview/PDF asymmetry — see "Risk assessment.") Jinja2 placeholders remain untouched literal text since no substitution ever happens client-side (CTM-10) — `react-markdown` has no knowledge of `{{ ... }}` and will render it as plain text within whatever surrounding Markdown context it sits in, satisfying CTM-02 directly.
- **Helper text (CTM-07):** the existing placeholder-list paragraph (`ContractTemplatesPage.tsx:74-80`) gains a second sentence: `"Você pode usar **negrito**, _itálico_, # e ## para títulos, - para listas, e --- para uma linha divisória."` (verbatim example already given in requirements.md), rendered as plain text (not itself Markdown-rendered — it's UI copy, not content).
- **Jest/ESM note:** no Jest configuration change is needed for the app to work at runtime (Vite handles ESM natively); the only place this surfaces is unit testing `ContractTemplatesPage.test.tsx`, addressed in "Test plan" below by mocking `react-markdown` rather than reconfiguring Jest's transform pipeline.

## Test plan

### Pytest (backend) — new `dojo-app/backend/tests/unit/test_markdown_pdf.py`

**`MarkdownPdfConverter.to_flowables` — one supported element per test, mirroring `test_contract_pdf_service.py`'s flat `TestX` class style:**
- `# Título` → produces a flowable using `styles["Heading1"]` (assert via `flowable.style.name == "Heading1"` or equivalent identifiable attribute) with text `"Título"`.
- `## Subtítulo` → `styles["Heading2"]`.
- `**negrito**` inside a paragraph → resulting `Paragraph.text`/frag content contains `<b>negrito</b>`.
- `_itálico_` inside a paragraph → contains `<i>itálico</i>`.
- `- item um\n- item dois` → one `ListFlowable` with two `ListItem`s, `bulletType="bullet"`.
- `1. item um\n2. item dois` → one `ListFlowable`, `bulletType="1"`.
- `---` alone in a block → one `HRFlowable`.
- Two blank-line-separated plain-text blocks → two separate `Paragraph`s, unchanged from today's behavior (CTM-04 direct assertion, independent of the DB-fixture-based test below).

**CTM-04 backward compatibility (extends existing `TestRenderPdf` in `test_contract_pdf_service.py`, per requirements.md's named fixtures):**
- `test_produces_non_empty_pdf_bytes`'s body (`"Contrato de {{ student.contract_name }}.\n\nPlano: {{ plan_tier.name }}."`) — extend the assertion to confirm the output is still exactly two plain paragraphs (e.g. by calling `MarkdownPdfConverter.to_flowables` directly on the merged text and asserting two `Paragraph` flowables, no `Heading1`/`Heading2`/`ListFlowable`/`HRFlowable` instances), in addition to the existing `%PDF-`/non-empty checks.
- `test_signature_image_increases_output_size`'s body (`"Corpo do contrato."`) — same style of extended assertion (one plain `Paragraph`, no formatting introduced).

**CTM-05 malformed-input cases (one test per enumerated case):**
- `"**bold sem fechar"` → rendered flowable's text contains the literal substring `**bold sem fechar`, no `<b>` tag present.
- `"### Cabeçalho nível 3"` → rendered as a plain paragraph containing the literal `###` characters, not a `Heading` style.
- `"  - item indentado"` (leading spaces) → a `ListFlowable` with one flat, top-level `ListItem` (no nested `ListFlowable`).
- An arbitrary other malformed case, e.g. `"_itálico sem fechar"` or a lone stray `*`, → renders as literal plain-paragraph text; assert no exception is raised and the offending substring is present in the output (never dropped).
- A combined-bold+italic input (`"***texto***"`, boundary case from requirements.md) → renders as literal text (not combined emphasis), consistent with the "out of scope, falls under CTM-05" boundary clarification.

**CTM-06 merge-field literal-rendering cases (both sub-parts, each independently asserted):**
- (a) A context value containing `<`, `>`, and `&` (e.g. `student.contract_name = "A & B <Corp>"`) merged into a template with surrounding bold (e.g. `"Contrato de **{{ student.contract_name }}**."`) → rendered output contains the merged text with `&`/`<`/`>` escaped (not interpreted as ReportLab XML) *and* still wrapped in a working `<b>` tag (proves escaping and legitimate admin-authored bold coexist correctly).
- (b) A context value containing each of `*`, `_`, `#`, and a leading `-` (e.g. `student.contract_name = "-*_# Nome"`, or four separate targeted sub-cases, one per character) merged into a template — required dedicated test, per CTM-06's own text — asserting **both**: (1) the character renders literally in the output (not as bold/italic/heading/list-item syntax — e.g. no unexpected `<b>`/`<i>` tag, no `Heading` style, no `ListFlowable`), and (2) a `**bold**` span written elsewhere in the *same* template body still renders correctly as bold (proves the merged stray character did not "pair" with, or otherwise corrupt, unrelated formatting elsewhere in the document — the explicit non-bleed requirement).
- `escape_context` direct unit tests: a nested dict (student/plan_tier/plan_version shape) with `*`/`_`/`#`/leading-`-` values in multiple leaves is escaped in every leaf; non-string leaf values (e.g. `plan_tier.weekly_frequency: int`) pass through unmodified without raising.

### Jest (frontend)

**`ContractTemplatesPage.test.tsx` — extends the existing test file (existing tests listed above are kept; `react-markdown` is mocked, per the autocrítica's test-layering decision):**
```tsx
jest.mock('react-markdown', () => ({
  __esModule: true,
  default: ({ children }: { children: string }) => <div data-testid="markdown-body">{children}</div>,
}))
```
- The "opens a modal with the version body" test is updated to assert the mocked `ReactMarkdown` component receives the *exact*, unsubstituted `body` string as its children (e.g. a body containing a literal `{{ student.contract_name }}` placeholder alongside `**bold**`/`# heading` syntax) — proves the wiring passes raw Markdown-with-placeholders through, unmodified, matching CTM-02's "Jinja2 placeholders remain visible as literal, unsubstituted text" requirement and CTM-10's "no client-side substitution."
- A new test confirms the modal no longer renders the body inside a `whitespace-pre-wrap` element (i.e., the old raw-text rendering path is gone) — a regression guard so a future edit can't silently revert to the old behavior.
- New helper-text test: asserts the updated paragraph (CTM-07) contains the Markdown-syntax guidance sentence.

### Cypress (new, addressing the Jest-mocking gap identified in the autocrítica)

One new scenario in `contracts.cy.ts` (or a new small `contract-templates.cy.ts`, implementer's call, following the existing `cy.createContractTemplate` custom-command convention already used six times in `contracts.cy.ts`): create a contract template version whose body contains at least one instance of each supported element (`# `, `## `, `**bold**`, `_italic_`, `- item`, `1. item`, `---`), open the "Ver conteúdo" modal, and assert real rendered DOM elements exist (`cy.get('h1')`, `cy.get('strong')`, `cy.get('li')`, `cy.get('hr')`, etc.) with the expected text — this is the one place the *real* `react-markdown` library is exercised end-to-end (a real Vite-bundled browser build, not Jest), closing the coverage gap the mocked Jest test intentionally leaves open. Also asserts a literal `{{ student.contract_name }}` placeholder appears verbatim (unsubstituted) in the rendered modal, per CTM-02/CTM-10.

## File-level task breakdown

1. **`dojo-app/backend/app/services/markdown_pdf.py`** (new) — `MarkdownPdfConverter` class: `escape_context`, `to_flowables`, and the private `_inline` helper plus the HR/heading/list/paragraph block classifiers.
2. **`dojo-app/backend/app/services/contract_pdf_service.py`** (modify) — `render_pdf` calls `MarkdownPdfConverter.escape_context(context)` before `Template(...).render()`, and `MarkdownPdfConverter.to_flowables(rendered)` instead of the current `for paragraph_text in rendered.split("\n\n")` loop; signature-image appending logic after the loop is unchanged.
3. **`dojo-app/backend/tests/unit/test_markdown_pdf.py`** (new) — all `MarkdownPdfConverter` unit tests listed in "Test plan" above.
4. **`dojo-app/backend/tests/unit/test_contract_pdf_service.py`** (modify) — extend `TestRenderPdf`'s two existing fixture-body tests with the CTM-04 "still plain paragraphs, nothing new introduced" assertions; add the CTM-06(a)/(b) merge-field-literal-rendering tests described above (may live here or in `test_markdown_pdf.py` — colocate with whichever existing fixture-building helpers make the test least verbose; implementer's call).
5. **`dojo-app/frontend/package.json`** (modify) — add `"react-markdown": "^10.1.0"` to `dependencies`; `npm install` to regenerate `package-lock.json`.
6. **`dojo-app/frontend/src/pages/ContractTemplatesPage.tsx`** (modify) — import `ReactMarkdown`; replace the view-modal's `whitespace-pre-wrap` div with `<ReactMarkdown>{viewVersion.body}</ReactMarkdown>`; update the helper-text paragraph (CTM-07).
7. **`dojo-app/frontend/src/pages/ContractTemplatesPage.test.tsx`** (modify) — add the `jest.mock('react-markdown', ...)`, update the existing view-modal test, add the new wiring/regression/helper-text tests described above.
8. **`dojo-app/frontend/cypress/e2e/contracts.cy.ts`** (modify) or a new `contract-templates.cy.ts` — add the real-library rendering scenario described above.
9. No Alembic migration, no API schema change (`schemas/contract_template.py`, `schemas/contract.py` untouched), no new API endpoint — this feature is entirely a rendering-layer change on both ends.

## Risk assessment

- **Preview/PDF asymmetry on `*text*`:** `react-markdown`'s default parsing treats `*text*` as italic (standard CommonMark), while CTM's backend subset deliberately does *not* support `*text*` as italic (reserved for list markers) and the backend converter will render a stray `*text*` as literal-with-list-ambiguity per its own classifier rules. An admin who writes `*text*` expecting it to look like `_text_` will see it rendered as italic in the preview but not specially formatted in the generated PDF. This is a genuine, small spec/library mismatch, not a bug in either side individually — flagging it here as a known residual risk rather than silently absorbing it. Mitigating it fully would mean passing `disallowedElements`/a custom `remark` plugin to `react-markdown` to suppress `*`-emphasis, which is more machinery than this small feature's UI-preview role (CTM-02 is preview-only, not the source of truth — the PDF is) justifies; left as-is, documented, and revisitable if it proves confusing in practice.
- **Leaf-value leading `"N. "` (digit-dot-space) not defensively escaped:** as noted in the autocrítica, a merged field value that happens to *start* with a digit-dot-space pattern (e.g., a contrived `"1. Nome"`) is not defensively backslash-escaped by `escape_context` and could, in the rare case such a value lands at the very start of a block, be misread as an ordered-list marker. Not in CTM-06's required test list; documented as an accepted, low-probability residual gap (student/plan display strings are names, addresses, CPFs, currency, dates — none naturally begin with `"N. "`) rather than added complexity for a scenario with no realistic trigger in current data.
- **`react-markdown`'s ESM-only nature vs. this repo's `ts-jest`/CommonJS Jest config:** resolved via mocking (see autocrítica/test plan) rather than a Jest reconfiguration, keeping CTM-08's "no other new dependency" constraint intact. If a future feature needs *unmocked* Jest coverage of another ESM-only package, this same tension will recur and may eventually justify a one-time Jest ESM migration — out of scope here, flagged as a forward-looking note only.
- **`react-markdown` major-version churn:** pinning `^10.1.0` (caret range) means a future `npm install` could pick up a new minor/patch within v10 automatically; a future v11 major would need an explicit, deliberate bump (standard semver risk, no different from this repo's other caret-pinned dependencies).

## Next Agent

Next Agent: doc-writer (to write an ADR for the CTM-06 backslash-escaping mechanism and the hand-rolled-parser-vs-library decision), then issue-creator to break the "File-level task breakdown" above into implementable issues, then `implementer` to build against this plan. Architecture is complete and self-reviewed; no further tech-analyst decision gate is expected unless `implementer` surfaces a genuine scope-changing ambiguity.
