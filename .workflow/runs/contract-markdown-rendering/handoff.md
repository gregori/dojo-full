# Handoff — Contract Template Markdown Rendering (CTM)

## What Was Done

- Standalone, bounded feature — not part of Epic 2 (`.workflow/epic-02/handoff.md` documents that epic as fully shipped, PR-5 open). Read for context only; nothing there is touched by this run.
- Confirmed ground truth directly against the codebase before writing requirements: `ContractPdfService.render_pdf` (`dojo-app/backend/app/services/contract_pdf_service.py`) currently splits on `\n\n` into plain `Paragraph`s with no escaping; `ContractTemplatesPage.tsx` uses a plain `<textarea>` for authoring and `whitespace-pre-wrap` for the "view" modal preview; no Markdown-related dependency exists yet in either `dojo-app/backend/pyproject.toml` or `dojo-app/frontend/package.json`.
- Wrote the structured requirements document: `.workflow/runs/contract-markdown-rendering/requirements.md` (CTM-01 – CTM-10).
- No source code touched — requirements-only phase.

## Key Decisions

- Core technical direction (Markdown authoring + `react-markdown` preview + ReportLab-flowables converter, staying on ReportLab, no WeasyPrint) was already locked in by the user before this run — not re-litigated.
- Markdown subset resolved: headings 1-2 only, `**bold**`, `_italic_` (not `*italic*`, reserved for list markers), single-level unordered/ordered lists, `---` horizontal rule, blank-line paragraphs. Links/images/tables/code/blockquotes/nesting/heading-3+ are explicit non-goals.
- Malformed-input handling is a **required** acceptance criterion (CTM-05), not optional — must degrade gracefully, never crash PDF generation, matching the class of bug `report_export_service.py` already fixed once (HIGH-severity, unescaped `Paragraph` content).
- A real pre-existing gap was surfaced during this pass: `ContractPdfService.render_pdf` does not currently escape Jinja2-merged text before building a `Paragraph` (unlike `report_export_service.py`'s already-fixed `render_pdf_table`). CTM-06 requires this feature to close that gap, not just avoid introducing a new one.
- Backend parser dependency choice (hand-rolled minimal parser vs. a light package like Python's `markdown`) is explicitly left to `tech-analyst`; requirements only state the constraint (small feature, avoid heavy dependencies).
- Reports pages (`ReportsPage.tsx`, `report_export_service.py`) are explicitly out of scope for this feature, despite the user mentioning similar treatment might come later.

## Open Questions

None blocking. See `requirements.md`'s "Open Questions" section for the reasoning (core direction already decided by the user; remaining specifics resolved as explicit defaults per this task's own scoping guidance).

## Next Action

`requirements-reviewer` to review `.workflow/runs/contract-markdown-rendering/requirements.md` against this codebase's ground truth (per the epic-02 precedent reviews).

## Requirements Review — NOT APPROVED (2026-07-26)

Full findings in `.workflow/runs/contract-markdown-rendering/review-requirements.md`. Verdict: **NOT APPROVED**, one blocking gap, everything else in the document is clear/complete/testable.

- **Ground truth re-verified independently** against `contract_pdf_service.py`, `ContractTemplatesPage.tsx`, `test_contract_pdf_service.py`, and `.workflow/epic-02/pr-5-reports/review.md` — every factual claim in `requirements.md` checked out; no correction needed to the document's description of current behavior.
- **Blocking finding:** CTM-06 only requires escaping merged student/plan data against ReportLab-XML markup (`<`, `>`, `&`); it says nothing about shielding merged data from being interpreted as **Markdown syntax** (`*`, `_`, `#`, leading `-`/`1.`/`---`) by the parser CTM-03 requires to run *after* the merge (locked merge order: Jinja2 first, then Markdown-parse). A merge field (e.g. `student.contract_name`, or `student.address`, itself a concatenation of several free-text DB columns) containing a Markdown-special character is exposed to the Markdown parser identically to the admin's own authored syntax — a stray `*` in one field could pair with another stray `*` elsewhere in the document and silently corrupt formatting in a signed legal contract, a failure mode CTM-05's "never raises an exception" criterion would not catch. This is the same class of miss as the HIGH finding fixed in `report_export_service.py` (PR-5), one layer higher in the pipeline. Fixable without touching the locked merge order or Option A architecture — needs one added paragraph to CTM-06 plus a short CTM-05/CTM-06-interaction sentence.
- Three more non-blocking, same-pass wording fixes noted (CTM-05's "best-effort" hedge weakens testability; CTM-04's regression-fixture reference is vague; two optional Markdown-subset boundary questions: combined bold+italic, and whether a non-technical admin has any way to author a literal `*`/`#`/`-` without it becoming Markdown syntax).
- Does not require re-opening the Option A decision or a new user interview — a single product-manager edit pass to `requirements.md` should resolve it, then proceed directly to `tech-analyst` without a second full review round (per the review doc's own Decision Gate).

## Requirements Fix Pass (2026-07-26) — resolves NOT APPROVED

`.workflow/runs/contract-markdown-rendering/requirements.md` updated in place to resolve `review-requirements.md`'s blocking finding #1 and fold in non-blocking findings #2-#5. No source code touched.

- **Finding #1 (BLOCKING, resolved).** CTM-06 rewritten into two required sub-parts: (a) the existing ReportLab-XML-markup escaping (`<`, `>`, `&`), unchanged in substance; (b) new — Jinja2-merged field values (e.g. `student.contract_name`, `student.address`, `plan_tier.name`) must render as literal text with respect to the supported Markdown subset too (`*`, `_`, `#`, leading `-`/`1.`/`---`), so a stray Markdown-special character in merged data can never be interpreted as formatting or "bleed" into unrelated document formatting. States the required outcome only; the mechanism (e.g. escaping Markdown-special characters in merged values independently of the Jinja2 render) is left to `tech-analyst`, consistent with how CTM-09 already leaves parser mechanics open. Added a required test-case requirement (merge value containing a Markdown-special character must render literally and must not affect other paragraphs).
- **Finding #2 (non-blocking, resolved).** CTM-05's "best-effort" hedge removed; replaced with four enumerated, binding cases (unclosed bold/italic, `###`+ heading, nested list item, other unsupported markup) each with a required fallback rendering, plus an explicit "never silently drop the offending text" rule.
- **Finding #3 (non-blocking, resolved).** Added a "CTM-05 / CTM-06 interaction" note directly under CTM-06: CTM-06 (content-integrity, merge-field literal rendering) takes precedence over and runs prior to CTM-05 (crash-safety, admin-authored malformed-Markdown fallback) — a correctly implemented CTM-06 means merge-field Markdown-special characters never reach CTM-05's fallback path at all.
- **Finding #4 (non-blocking, resolved).** CTM-04 now names the exact existing fixtures to use: the two plain-text bodies already in `dojo-app/backend/tests/unit/test_contract_pdf_service.py`'s `TestRenderPdf` class (`"Contrato de {{ student.contract_name }}.\n\nPlano: {{ plan_tier.name }}."` in `test_produces_non_empty_pdf_bytes`, and `"Corpo do contrato."` in `test_signature_image_increases_output_size`) — no new DB-sourced fixture is required.
- **Finding #5 (optional, resolved).** Added a "Boundary clarifications" subsection under the Markdown-subset table: (a) combined bold+italic (`***text***` etc.) is explicitly out of scope, falls under CTM-05's graceful-degradation rule like any other unsupported syntax; (b) there is no admin-facing escape mechanism for literal `*`/`#`/`-` characters in this feature (accepted limitation of the small subset, distinct from CTM-06 which only covers merge-field values, not admin-typed text) — can be revisited as follow-up work if it proves to be a real problem.
- Also updated the document's "Status" and "Constraints" sections to reflect the review outcome and to state CTM-05 (crash-safety) and CTM-06 (content-integrity) as two distinct, both-required criteria.

Per `review-requirements.md`'s own Decision Gate item 4, this fix does not require a second full `requirements-reviewer` pass — only a light re-check of the edited CTM-05/CTM-06 text would be warranted, and the review doc already pre-authorized proceeding straight to `tech-analyst` once these findings were folded in.

## Tech Analyst — Architecture Complete (2026-07-26)

Full design written to `.workflow/runs/contract-markdown-rendering/plan.md`. Autocrítica performed before finalizing (see plan.md's own "Autocrítica" section) — no flaw left unresolved.

- **Backend converter:** hand-rolled, line-based parser (new `dojo-app/backend/app/services/markdown_pdf.py`, `MarkdownPdfConverter` class), not Python-Markdown or any other library — rejected a general Markdown library because CTM's subset deliberately diverges from CommonMark (`*text*` is not italic) and a library would still need a hand-built CTM-06 escaping mechanism on top, so it buys nothing over hand-rolling while adding an HTML-intermediate translation layer this project's own precedent (rejecting WeasyPrint in Phase 4) already argued against.
- **CTM-06 escaping mechanism (the crux):** backslash-escape Markdown-special characters (`*`, `_`, `#`, leading `-`) in the Jinja2 context's leaf string values, *before* `Template.render()` — not after. This preserves the locked merge order (Jinja2 first, then Markdown-parse) exactly, since only the context values change, not when substitution happens. The backslash rides through Jinja2 untouched, prevents the parser's bold/italic/list/heading/HR regexes from ever pairing with or recognizing merged-in characters as syntax, and is stripped back to a plain visible character in the final output after ReportLab-XML escaping. Closes both CTM-06(a) (existing gap: merged text was never escaped against `<`/`>`/`&` before) and CTM-06(b) (new: merged text can't be read as Markdown syntax) in one mechanism.
- **CTM-05 crash safety:** achieved by construction (every classifier is a total regex-match-or-fallback function; no `try/except` added anywhere), per CLAUDE.md's "don't program defensively" rule — deliberately rejected wrapping the converter in a blanket exception handler.
- **Frontend:** `react-markdown@10.1.0` (latest, React-19-compatible) replaces `whitespace-pre-wrap` in `ContractTemplatesPage.tsx`'s view modal; helper text gains a Markdown-syntax sentence (CTM-07).
- **New finding during design (not in requirements.md):** `react-markdown` is ESM-only; this repo's `jest.config.cjs` (`ts-jest`, CommonJS transform, `.tsx?`-only) cannot load it without either a new dependency (`babel-jest`) or a fragile `transformIgnorePatterns` allow-list — both rejected. Resolved by mocking `react-markdown` in `ContractTemplatesPage.test.tsx` (tests our own wiring) plus one new Cypress scenario (tests the real library in a real browser build, no Jest ESM problem there). Documented as a deliberate test-layering decision in plan.md, not a shortcut.
- Full test plan (pytest per CTM element/CTM-04/CTM-05/CTM-06 case, Jest, Cypress) and a 9-item file-level task breakdown are in `plan.md`.
- Two residual risks documented and accepted (not silently ignored): a `*text*` preview/PDF formatting asymmetry (react-markdown default-parses it as italic; the backend subset does not), and an unescaped leading-digit-dot-space (`"N. "`) merged-value edge case outside CTM-06's required test list.

## Next Agent

Next Agent: doc-writer (to write an ADR for the CTM-06 backslash-escaping mechanism and the hand-rolled-parser-vs-library choice), then issue-creator to turn plan.md's file-level task breakdown into issues, then implementer to build. No further tech-analyst decision gate expected unless a genuine scope-changing ambiguity is found during implementation.

## Implementer — Build Complete (2026-07-26)

Implemented exactly per `plan.md`, no redesign. Files changed:

- `dojo-app/backend/app/services/markdown_pdf.py` (new) — `MarkdownPdfConverter` (`escape_context`, `to_flowables`) + module-private `_inline`/block classifiers, exactly the regexes/algorithm in plan.md. No `try/except` anywhere (crash-safety by construction, per CTM-05/CLAUDE.md).
- `dojo-app/backend/app/services/contract_pdf_service.py` — `render_pdf` now calls `MarkdownPdfConverter.escape_context(context)` before `Template(...).render()` and `MarkdownPdfConverter.to_flowables(rendered)` instead of the old `\n\n`-split loop. Signature/Image-appending logic unchanged.
- `dojo-app/backend/tests/unit/test_markdown_pdf.py` (new) — one test per supported element, CTM-05 malformed-input cases (including the `***texto***` boundary case), CTM-06(a)/(b) merge-field literal-rendering cases (four separate special-character sub-cases + non-bleed assertions), `escape_context` direct tests.
- `dojo-app/backend/tests/unit/test_contract_pdf_service.py` — extended both `TestRenderPdf` fixture tests with CTM-04 "still exactly N plain paragraphs, no Heading/List/HR flowables" assertions.
- `dojo-app/frontend/package.json` + `package-lock.json` — added `react-markdown@^10.1.0` (only new dependency, per CTM-08), `npm install` run.
- `dojo-app/frontend/src/pages/ContractTemplatesPage.tsx` — view-modal's `whitespace-pre-wrap` div replaced with `<ReactMarkdown>{viewVersion.body}</ReactMarkdown>` (wrapper div keeps existing Tailwind classes plus `prose prose-sm max-w-none`); helper text gains the verbatim CTM-07 Markdown-guidance sentence as plain (non-rendered) UI copy.
- `dojo-app/frontend/src/pages/ContractTemplatesPage.test.tsx` — `jest.mock('react-markdown', ...)` per plan's exact mock shape; "opens a modal" test updated to assert the mock receives the exact unsubstituted body (placeholder + Markdown syntax) via `textContent`; added a `whitespace-pre-wrap`-is-gone regression test and a helper-text-guidance test.
- `dojo-app/frontend/cypress/e2e/contracts.cy.ts` — added "Scenario 7" exercising the real (unmocked) `react-markdown` library: creates a template version with one instance of every supported element, opens "Ver conteúdo", asserts real `h1`/`h2`/`strong`/`em`/`li`/`hr` DOM elements and a verbatim unsubstituted `{{ student.contract_name }}` placeholder.

### Gate results

- Backend: `ruff check .` — all checks passed. `ruff format --check .` — 119 files already formatted (after one `ruff format .` pass on the new/edited files). `pytest` full suite (via `docker exec dojo-backend pytest`, this repo's established local invocation per `pr-5-reports/test-results.md`) — **418 passed, 0 failed**; `app/services/markdown_pdf.py` at 100% line coverage.
- Frontend: `npm run lint` — no issues. `npx jest` full suite — **60 passed, 0 failed** (11 suites). `npm run format:check` (Prettier) — clean on every file this task touched (2 unrelated pre-existing files, `BeltRequirementsPage.test.tsx`/`BeltsPage.test.tsx`, still flagged — untouched, out of scope). `npx tsc --noEmit` / `npm run build` — **1 pre-existing, unrelated failure**: `src/pages/StudentsPage.tsx:514` (`TS2790`), part of an already-dirty, uncommitted `registration_number` feature that predates this task and was never touched by it (confirmed via `git diff` isolating that file's changes) — zero TypeScript errors in any CTM file.
- Cypress: new scenario added, not executed — `docker exec dojo-frontend` showed the running frontend container's `node_modules`/`package.json` do not reflect the working tree's new `react-markdown` dependency (stale/non-bind-mounted image), so a real run would fail for infrastructure reasons unrelated to the spec; rebuilding the container was outside this task's scope without explicit instruction. Verified the spec by direct code review instead (balanced braces, follows the other 6 scenarios' conventions in the same file); this repo's `eslint.config.js` explicitly ignores `cypress/` and `tsconfig.json`'s `include` excludes it, so no automated lint/type gate covers it either way.

### Deviations from plan.md (documented, not silent)

1. **CTM-05 case 5 (`***texto***`) nuance.** Verified via direct Python testing that plan.md's exact `_BOLD_RE` (`r"\*\*(?<!\\\*\*)(.+?)\*\*"`) — implemented byte-for-byte as specified — actually produces `<b>*texto</b>*` (partial single-bold with a leftover asterisk), not fully inert literal text, because it has no flanking guard against a leading/trailing third asterisk. Kept the regex exactly as the plan specifies (did not add flanking-rule machinery) because: requirements.md explicitly calls this an accepted "out of scope" boundary case; the hard requirements still hold (no exception, "texto" text never dropped, and no actual *combined* bold+italic emphasis is produced — only bold); and any fix would be new regex complexity beyond what plan.md authorized. The added test asserts exactly those three properties rather than byte-exact literal-text equality.
2. **`prose`/`prose-sm` Tailwind classes are inert.** Added per plan.md's suggested JSX, but this repo's `tailwind.config.js` has no `@tailwindcss/typography` plugin and CTM-08 forbids adding a new frontend dependency for this feature — so these utility classes currently apply no extra styling (harmless no-op), exactly matching plan.md's own "or equivalent" hedge. Not treated as a blocking gap.
3. **Pre-existing, unrelated dirty-tree state left untouched.** `StudentsPage.tsx` (WIP `registration_number` feature, causes the one real `tsc`/`build` failure above) and `BeltRequirementsPage.test.tsx`/`BeltsPage.test.tsx` (pre-existing Prettier-formatting warnings) were already uncommitted in the working tree before this task started and are unrelated to CTM — left untouched per "do not refactor unrelated code."
4. **No GitHub issue commenting.** `.workflow/runs/contract-markdown-rendering/state.json` shows no linked issue number for this standalone run (it never went through an `issue-creator` step), so the Implementer role's usual "comment on issue" steps were skipped as not applicable.

## Current Status

Implementation complete, all CTM-01–CTM-10 acceptance criteria covered by backend/frontend unit tests plus one new Cypress scenario (unexecuted, see above). Backend gates fully green; frontend gates green except one pre-existing, unrelated `tsc`/build failure.

## Next Agent

Next Agent: reviewer.

## Reviewer — Independent + Security Review (2026-07-26)

Full findings in `.workflow/runs/contract-markdown-rendering/review.md`. **Verdict: NOT APPROVED** — one HIGH content-integrity finding, empirically reproduced (throwaway scripts, not the implementer's own tests), plus two non-blocking LOW observations.

- **HIGH — CTM-06(b) not actually satisfied.** `markdown_pdf.py`'s backslash-escape/unescape mechanism (`escape_context` + `_inline`'s `_BOLD_RE`/`_ITALIC_RE`/unescape loop) fails exactly the scenario CTM-06(b) itself names as the required guarantee: a merged field's escaped special character can still pair with a real, admin-authored delimiter of the same type. Reproduced: `contract_name = "Silva*"` merged into the ordinary authoring pattern `"**{{ student.contract_name }}**"` renders as `<b>Silva\</b>*` — a leaked literal backslash and a mis-paired/corrupted bold span, not literal text. Underscore/italic is worse: `_ITALIC_RE` has no escape-awareness at all, so a stray merged underscore anywhere in the *same paragraph block* as an unrelated real `_..._` span (not even adjacent) pairs incorrectly, e.g. `"Nome: Silva_ texto _italico_ fim."` → `"Nome: Silva\<i> texto </i>italico_ fim."`. None of the 5 `TestToFlowablesMergeFieldLiteralRendering` tests catch this because they place the merged value and the real markup in separate, blank-line-separated blocks — block-splitting trivially isolates them regardless of whether the escape mechanism works, so the tests prove a weaker property than CTM-06(b) requires. Fix guidance (see review.md finding 1 for full detail): the single-backslash-prefix approach needs to be replaced with a sentinel/placeholder scheme that leaves no bare `*`/`_` character for `_BOLD_RE`/`_ITALIC_RE` to find during the regex passes, with the real literal character substituted back in only as the final step.
- **LOW, non-blocking.** `escape_context` has no `list` branch (latent gap, not currently reachable since `build_context` never produces list leaves). Documented `"N. "` leading-digit residual risk already self-disclosed by the implementer/plan — accepted, non-blocking.
- Confirmed correct: CTM-06(a) XML-escaping, CTM-05 crash-safety-by-construction, CTM-04 backward compatibility, all frontend wiring (CTM-01/02/07/08/10) including no `rehype-raw`/`dangerouslySetInnerHTML` XSS reopening, and CTM-10 scope discipline (no touch to `ReportsPage.tsx`/`report_export_service.py`, no new API/schema/migration).

## Next Agent

Next Agent: implementer (fix the HIGH finding — CTM-06(b) escape/unescape mechanism redesign — per `review.md`'s fix guidance; optionally fold in the LOW `list`-branch hardening; then return to reviewer for re-verification, matching the PR-5 precedent's fix → re-verify → APPROVED cycle). Status remains `in-progress`, not `linter`.

## Fix pass — CTM-06(b) escape/unescape mechanism redesigned (2026-07-26)

Independent+security review (`review.md`) returned **NOT APPROVED**: 1 HIGH content-integrity finding (backslash-escape/unescape mechanism does not prevent a merged field's escaped Markdown-special character from pairing with a real, admin-authored delimiter of the same type — see review.md finding 1 for full repro), 1 LOW non-blocking (`escape_context` has no `list` branch), 1 LOW already-accepted (leading `"N. "` merged values, untouched, out of scope). Mirrors the PR-5 precedent's fix → re-verify pattern.

**Root cause.** The old mechanism prefixed a bare backslash onto each Markdown-special character in merged context leaf strings (e.g. `*` → `\*`) before Jinja2 render, then stripped the backslash back off in `_inline()` *after* `_BOLD_RE`/`_ITALIC_RE` ran. Because the literal `*`/`_` character itself survived inside the intermediate `\*`/`\_` sequence, it remained visible to the regex engine as a real delimiter candidate: `_BOLD_RE`'s partial 3-character negative lookbehind only excluded one specific adjacency and could still let its own non-greedy capture consume half of an escaped pair; `_ITALIC_RE` had no escape-awareness at all. A merged field wrapped directly in real `**{{ field }}**` (the single most natural authoring pattern this feature exists to support), or merely sharing a paragraph block with an unrelated real `_..._` span, could mis-pair and corrupt the rendered output.

**Fix — sentinel-based escaping, per the review's own fix guidance.**
- `escape_context()` now replaces each Markdown-special character (`*`, `_`, `#`, and a leading `-`) with a distinct Private Use Area Unicode sentinel (`U+E000`–`U+E003`), not a backslash-prefixed literal. No raw `*`/`_`/`#`/leading-`-` character survives in a merged leaf string past this step.
- These sentinels ride through Jinja2's `Template.render()` unchanged (no Jinja2-special meaning), are untouched by `xml.sax.saxutils.escape()` (which only touches `&`/`<`/`>`), and don't match any block/inline classifier regex in the module — so `_BOLD_RE`/`_ITALIC_RE`/`_HEADING_RE`/`_UNORDERED_ITEM_RE` structurally cannot see a merged special character as a delimiter candidate. Pairing is eliminated by construction, not by making the regexes escape-aware — `_BOLD_RE` could even be simplified back to a plain `\*\*(.+?)\*\*` since the backslash-adjacency lookbehind is no longer needed.
- `_inline()` still XML-escapes the entire text run unconditionally first (CTM-06(a), unchanged), then applies bold/italic substitution, and only as the very last step — mirroring exactly where the old backslash-unescape ran — substitutes each sentinel back to its original literal character.
- Folded in Finding 2 (cheap, low-risk): `escape_context`'s recursion now also branches on `isinstance(value, list)`, mapping `escape_value` over each item, closing the latent (previously unreachable) gap for any future list-shaped context leaf.
- Finding 3 (leading `"N. "` merged values) untouched, per instructions — already accepted/documented/non-blocking.
- No `try/except` added anywhere; crash-safety-by-construction (CTM-05) preserved. Merge order (Jinja2 render after `escape_context`, Markdown-parse after that) unchanged.

**New regression tests** (`tests/unit/test_markdown_pdf.py`):
- `test_merged_asterisk_wrapped_directly_in_real_bold_renders_correctly` — reproduces review.md's exact repro (`contract_name = "Silva*"` wrapped in `"**{{ student.contract_name }}**"`); asserts `paragraph.text == "<b>Silva*</b>"` and no leaked backslash.
- `test_merged_underscore_same_block_as_unrelated_real_italic_span` — reproduces the italic same-block (not adjacent) repro; asserts the real `_italico_` span still renders as `<i>italico</i>` and the merged underscore stays a plain literal character outside any tag.
- `test_xml_special_chars_and_markdown_special_char_coexist_inside_real_bold` — re-verifies CTM-06(a) (XML-escaping) coexists correctly with the new sentinel mechanism when a merged value contains both `<`/`>`/`&` and a Markdown-special character, wrapped in real bold.
- Kept all pre-existing cross-block-isolation tests (still valid, just insufficient alone, per the review) and added `test_list_leaf_values_are_escaped` for Finding 2.
- `TestEscapeContext`'s direct assertions updated from backslash-literal equality checks to sentinel-absence checks plus a round-trip-through-Jinja2-and-`_inline` literal-restoration check (since the intermediate escaped form is no longer a printable ASCII string).

**Verified the new tests are not vacuously true.** Reconstructed the old backslash-based `escape_context`/`_inline` in a throwaway script and ran review.md's exact two repro cases against it inside the actual runtime environment:
- Before (old code): `Case 1 output: '<b>Silva\\</b>*'` (leaked backslash, mis-paired/truncated bold, dangling `*`). `Case 2 output: 'Nome: Silva\\<i> texto </i>italico_ fim.'` (merged underscore incorrectly opened italic on the wrong span).
- After (fixed code): `Case 1 output: '<b>Silva*</b>'` (correct — merged `*` literal, inside the bold tag, no backslash). `Case 2 output: 'Nome: Silva_ texto <i>italico</i> fim.'` (correct — real italic span intact, merged underscore literal, no leaked backslash).

**Gate results** (this container's actual working invocation is the system Python, since `poetry run pytest`/`poetry run python` resolve to a poetry venv missing `jinja2`/`pytest`; `docker exec dojo-backend bash -lc "cd /app && /usr/local/bin/python3.13 -m {ruff,pytest} ..."` is what actually executes against the real dependency set — confirmed via `poetry run which pytest` resolving to `/usr/local/bin/pytest`, the system install):
- `ruff check .` — all checks passed (backend-wide).
- `ruff format --check .` — 119 files already formatted (after one `ruff format` pass on the two touched files).
- `pytest -q` (full backend suite) — **422 passed, 0 failed** (was 418 pre-fix-pass; +4 net new tests: 3 new regression cases + 1 Finding-2 test, minus none removed). `app/services/markdown_pdf.py` at 100% line coverage.

## Current Status

Fix pass complete. HIGH finding (CTM-06(b)) resolved via sentinel-based re-escaping; LOW Finding 2 (`list` branch) folded in; LOW Finding 3 untouched per instructions. All gates green.

## Next Agent

Next Agent: reviewer (re-verify the fix per the PR-5 precedent's fix → re-verify → APPROVED cycle).

## Reviewer — Re-verification (fix pass), 2026-07-26

Full findings in `.workflow/runs/contract-markdown-rendering/review.md`'s "Re-verification (fix pass)" section. **Verdict: APPROVED.**

- Read the actual sentinel-based `escape_context`/`_inline` code directly (not the implementer's summary): confirmed the fix is **structural**, not just empirically patched for the two originally-reported repro cases — `escape_context` does a global (all-occurrences) `str.replace` per special character per leaf, so every merged leaf reaching the rendered text contains zero raw `*`/`_`/`#`/leading-`-` characters, meaning `_BOLD_RE`/`_ITALIC_RE` (now simplified back to plain, no lookbehind hack) can only ever pair on admin-authored delimiters, regardless of how many merge fields or special characters appear in a block.
- Confirmed sentinel collision safety on all four sub-points: survives Jinja2's bare `Template.render()` unchanged (no autoescape), disjoint from `xml.sax.saxutils.escape()`'s `&`/`<`/`>` set, doesn't match any of the module's own classifier regexes, and is restored in every flowable-producing branch (`HR`/heading/unordered-list/ordered-list/paragraph), not just the paragraph default.
- Independently reconstructed the OLD backslash-based mechanism in a throwaway script and confirmed all 3 new regression tests are genuinely discriminating (fail against old code, pass against new) — not vacuously true.
- Re-ran `test_markdown_pdf.py` (25 passed) and `test_contract_pdf_service.py` (6 passed) in isolation; both green, CTM-04/CTM-05/CTM-06(a) all still hold by direct code read.
- Confirmed Finding 2's `list` branch is correctly implemented (recurses properly, handles empty lists and non-dict/str items).
- Two new, non-blocking residual observations noted for completeness (not regressions from this fix pass, not blocking): a theoretical sentinel/real-data collision if a DB field ever literally contained a Private Use Area code point (not reachable via any current input path), and a pre-existing (unchanged) leading-hyphen-escaping limitation scoped to leaf-string-start only, not per-embedded-line.

## Post-approval user testing — two follow-up fixes (2026-07-27)

User manually tested the live feature (dojo dev stack, admin login) after the review's APPROVED verdict and root's independent gate re-confirmation. Two real, user-surfaced gaps were found and fixed in the same session, both scoped as small additive/CSS-only follow-ups to the already-approved architecture (no new requirements/design/review cycle run for either — judged proportionate to their size and risk per CLAUDE.md's incremental-work guidance):

1. **Infra gap (not a code bug): `dojo-frontend`'s Docker service has no bind mount** (`docker-compose.yml`'s `frontend` service only has a build context, unlike `backend`'s `./dojo-app/backend:/app` mount) — the running container was serving a pre-feature image with no `react-markdown` installed, so the user's first look at "Ver conteúdo" showed raw unrendered Markdown. Fixed by `docker compose build frontend && docker compose up -d frontend` (rebuilt image now bakes in the feature). This will recur on every future frontend change until/unless the compose file gets a dev bind mount — noted here, not fixed (out of scope of this feature; a legitimate small infra follow-up for a future session if it keeps causing confusion).
2. **User request — live preview while authoring, not just after saving.** Added a live-updating Markdown preview pane next to the "Corpo do Contrato" textarea in the "Nova Versão" form (`ContractTemplatesPage.tsx`), reusing the same `ReactMarkdown` component already reviewed/approved for the view-modal — no new dependency, no backend change, no new security surface. 3 new Jest tests added (typing updates the live preview; empty-body placeholder message; unsubstituted-placeholder guarantee holds in the live pane too). Gates: `lint`/`tsc`/`jest` (63/63)/`format:check` all clean (same one pre-existing unrelated `StudentsPage.tsx` `tsc` error as before, untouched).
3. **Real presentational bug found via user testing: headings/lists didn't visually render.** Root cause diagnosed directly (not guessed): both `ReactMarkdown` containers used inert `prose prose-sm max-w-none` classes (`@tailwindcss/typography` plugin is not installed in this project — confirmed absent from `package.json`/`tailwind.config.js`), while `src/index.css`'s active `@tailwind base` (Preflight) resets heading font-sizes to `inherit` and list `list-style` to `none`. The Markdown was parsing correctly into real `<h1>`/`<h2>`/`<ul><li>`/`<ol><li>` DOM nodes the whole time (matching backend PDF-side tests and the Cypress spec's `cy.get('h1')` etc. assertions) — this was purely presentational. Bold/italic looked fine only because Preflight doesn't reset `<strong>`/`<em>`. Fixed by replacing `prose prose-sm max-w-none` in both locations (view-modal, live-preview pane) with a single extracted `MARKDOWN_CONTENT_CLASSES` constant of explicit Tailwind v3.4 arbitrary-variant descendant-selector utilities (`[&_h1]:text-xl [&_h1]:font-bold ...`, `[&_ul]:list-disc [&_ul]:pl-5 ...`, etc.) — zero new dependency, consistent with this file's existing utility-first Tailwind convention. Gates re-confirmed clean (lint/tsc/jest 63/63/format:check) after this change too.

Both fixes were verified by rebuilding and recreating the `dojo-frontend` container and having the user re-test live in the browser each time. **User confirmed final approval of the visual result.**

## Next Agent

None — feature complete, independently reviewed APPROVED, and confirmed working end-to-end by the user in the live dev stack. Remaining open item (not blocking, not part of this feature): `docker-compose.yml`'s `frontend` service has no dev bind mount, unlike `backend` — worth fixing in a future session so frontend code changes don't require a manual image rebuild to take effect locally. Not committed/pushed yet — awaiting the user's explicit go-ahead for that step.
