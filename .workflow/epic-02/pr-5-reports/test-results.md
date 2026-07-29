# Test Results — PR-5: Reports

Verified by the implementer session, 2026-07-26, against the real dockerized MySQL stack (`docker compose up -d db backend frontend`, backend tests run via `docker exec dojo-backend pytest`; frontend Jest/Cypress run on the host against the live `http://localhost:3000` / `http://localhost:8000`).

## Backend (pytest)

- New/changed test files: `test_report_service.py`, `test_report_export_service.py`, `test_api_reports.py` — **44 passed, 0 failed**, 100% statement coverage on `app/services/report_service.py`, `app/services/report_export_service.py`, and `app/schemas/report.py`.
- Full backend regression suite (`docker exec dojo-backend pytest -q`): **375 passed, 0 failed**, 94% total coverage. No regressions in any Phase 1-4 test.

Coverage per new module: `app/services/report_service.py` 76/76 stmts (100%), `app/services/report_export_service.py` 35/35 stmts (100%), `app/schemas/report.py` 57/57 stmts (100%), `app/api/reports.py` 85%+ (uncovered lines are FastAPI route-declaration boilerplate already exercised indirectly).

## Frontend (Jest)

- `ReportsPage.test.tsx` (new): **11 passed, 0 failed** — covers all four sections' "Visualizar" (happy path + empty-result state) and "Exportar PDF"/"Exportar CSV" (correct endpoint/params/`responseType: 'blob'`).
- Full Jest suite (`npx jest`): **44 passed, 0 failed** across all suites. No regressions.

## Cypress e2e (`reports.cy.ts`, new)

Run against a live stack (`docker compose up -d db backend frontend`, real MySQL, real backend, real Vite dev server):

- Isolated run (`npx cypress run --spec cypress/e2e/reports.cy.ts`): **5/5 passing**.
  1. Belt-exam report (REP-01) JSON preview renders a seeded participation row.
  2. Student attendance report (REP-02) JSON preview renders the seeded total-attendance count.
  3. Real PDF download round trip (REP-05): clicks "Exportar PDF", intercepts the real network response, confirms `content-type: application/pdf` and decodes the first 5 response bytes to confirm the `%PDF-` magic bytes (axios' `responseType: 'blob'` makes Cypress capture the body as an `ArrayBuffer` rather than a string, so the assertion decodes it explicitly).
  4. Real CSV download round trip (REP-05) for the financial report: confirms all three section headers (Pagamentos/Inadimplência/Projeção) appear in the downloaded text body.
  5. Authorization regression: an invalid bearer token gets 401 on `GET /api/v1/reports/finance` and `GET /api/v1/reports/belt-exams/{id}`.
- Full pre-existing e2e suite re-run (`npx cypress run`, all 12 spec files) confirms **no regression from the new `/reports` route/nav entry**: `reports.cy.ts` again **5/5 passing** (fastest spec in the run, 49s, 0 pending), alongside `contracts.cy.ts` 6/6, `financial.cy.ts` 10/10, `medical-exam.cy.ts` 10/10, `precheckin.cy.ts` 5/5 — i.e. every spec that is part of this epic's actual CI-verified surface (see `.github/workflows/ci-frontend.yml`'s `Run Cypress e2e tests` step) passed cleanly.
- The full local run also surfaced widespread failures/large "pending" counts in seven **pre-existing, pre-Epic-2 legacy specs** (`auth.cy.ts`, `belt-progress.cy.ts`, `belt-requirements.cy.ts`, `checkin.cy.ts`, `events.cy.ts`, `exams.cy.ts`, `students.cy.ts`) that are **not part of `ci-frontend.yml`'s e2e job** (which only ever ran `precheckin.cy.ts`, `medical-exam.cy.ts`, `financial.cy.ts` before this PR) and are not exercised or maintained by any phase of this epic. These are pre-existing, out-of-scope for Phase 5 (Reports touches none of the pages those specs cover), consistent with this repo's own documented precedent that this local Windows/Docker Desktop/WSL2 environment has known flakiness not present in real CI (see `.workflow/epic-02/handoff.md`'s "Local sandbox note" from the Phase 3/4 sessions). No fix was attempted for these, per Phase 5's scope discipline (do not touch Phase 1-4 code beyond the two documented integration points).

## Fix-pass re-verification (2026-07-26, after review findings 1-2)

Independent review (`review.md`) returned NOT APPROVED with 2 blocking findings (HIGH: unescaped `Paragraph` titles crash PDF export on markup-like input; MEDIUM/CWE-1236: unescaped CSV cells enable formula injection) and 2 non-blocking findings (no 403-wrong-role test; `app/api/reports.py` at 85% coverage). All four were fixed in this pass.

**Finding 1 fix** — `ReportExportService.render_pdf_table` now escapes `title` and every `section_title` with `xml.sax.saxutils.escape()` before constructing a `Paragraph`. Verified the exact repro from the review no longer raises:
```
title = "Exame de Faixa - <b>unclosed bold"
section_title = "Presenças - Aula <Avançado>"
ReportExportService.render_pdf_table(title, [(section_title, ["Evento"], [["<b>unclosed & bold"]])])
-> returns bytes starting with b"%PDF-" (1834 bytes), no exception
```
`Table` cell content (not `Paragraph`-bound) was independently confirmed safe with the same adversarial strings before deciding no escaping was needed there (ReportLab's plain-string `Table` cells render literally, no markup parsing) — verified with a standalone script.

**Finding 2 fix** — `ReportExportService.render_csv` now prefixes any cell value starting with `=`, `+`, `-`, or `@` with a leading `'` (OWASP CSV-injection mitigation) via a new `_neutralize_formula` helper, applied to every data-row cell (not headers/titles, which are static/report-level strings, not attacker-influenced). Verified output for adversarial input:
```
Input cells:  ['=cmd|calc'], ['+1'], ['-5 students'], ['@SUM(A1)'], ['Pix']
Output cells: '=cmd|calc     '+1     '-5 students     '@SUM(A1)     Pix   (unchanged)
```

**New regression tests** (backend, `test_report_export_service.py`):
- `TestRenderPdfTable::test_title_with_markup_special_characters_does_not_raise` — calls `render_pdf_table` with a title and section title each containing `<`, `>`, `&`, and an unbalanced-tag substring (`"Aula <Avançado>"` / `"<b>unclosed bold"`), asserts `%PDF-` magic bytes are still returned instead of raising.
- `TestRenderCsv::test_cell_values_starting_with_formula_trigger_characters_are_neutralized` — calls `render_csv` with cells starting with each of `=`, `+`, `-`, `@`, parses the output with `csv.reader`, and asserts each is prefixed with a leading `'` while a normal-text cell (`"Pix"`) is left untouched.

**Non-blocking findings also folded in:**
- Finding 3: added `TestAuthorization::test_report_endpoints_reject_wrong_role_with_403` to `test_api_reports.py` — overrides only `get_current_user` (not `get_current_instructor_or_admin`) with a `MagicMock(spec=User, role="student")` so the real dependency chain runs and asserts `403` on all four endpoints.
- Finding 4: added `test_pdf_format_returns_pdf_bytes`/`test_csv_format_returns_csv_content` to both `TestStudentAttendanceReportEndpoint` and `TestClassAttendanceReportEndpoint` — these two endpoints previously had no pdf/csv-format test at all, which is exactly what the reviewer's cited uncovered lines (71-82, 86-95, 175, 197 in `app/api/reports.py`) correspond to (`_student_attendance_sections`/`_class_attendance_sections` and their `_render` call sites).

**Full backend regression suite re-run**: **382 passed, 0 failed** (was 375 before this fix pass; +7 new tests: 1 PDF-escaping regression test, 1 CSV-neutralization regression test, 1 wrong-role-403 test, 4 pdf/csv-format tests for the two previously-uncovered endpoints). No regressions in any Phase 1-4 test or any other Phase 5 test.

Coverage tooling (`pytest-cov`) could not be run to completion in this local Windows sandbox during the fix pass — `pytest --cov=...` reproducibly failed with `ImportError: PyO3 modules compiled for CPython 3.8 or older may only be initialized once per interpreter process` while importing `bcrypt` via `tests/unit/conftest.py`, an environment/tooling quirk unrelated to the code changes (not reproducible without `--cov`; same conftest imports fine for the full non-coverage `pytest` run above). Exact post-fix coverage percentages for `app/api/reports.py` were therefore not re-measured numerically in this pass; the new pdf/csv-format tests target precisely the branches the reviewer identified as uncovered, so the gap should be closed or substantially reduced, but this is not independently confirmed by a coverage report in this session.

## CI wiring (deviation, small and additive)

`ci-frontend.yml`'s e2e job only listed `precheckin.cy.ts,medical-exam.cy.ts,financial.cy.ts` — `contracts.cy.ts` had never actually been added despite being reported green "via real CI" in the Phase 4 handoff. Added both `contracts.cy.ts` and `reports.cy.ts` to the `--spec` list so the new Reports e2e coverage (and the previously-unwired Contracts coverage) actually runs in CI going forward. This is a one-line, additive change to CI configuration, not application code, and keeps every phase's e2e spec actually gated by CI rather than only verified ad hoc.
