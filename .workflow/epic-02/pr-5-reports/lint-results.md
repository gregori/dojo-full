# Lint Results — PR-5: Reports

Verified by the implementer session, 2026-07-26, inside the `dojo-backend` container (`docker exec dojo-backend ...`) and on the host frontend checkout (`dojo-app/frontend`).

## Backend

- `ruff check .` — **PASS** ("All checks passed!")
- `ruff format --check .` — **PASS** ("116 files already formatted") after auto-formatting the two new files (`app/api/reports.py`, `tests/unit/test_api_reports.py`) that were initially flagged.

## Fix-pass re-verification (2026-07-26, after review findings 1-2)

Re-ran on the implementer's local sandbox (Windows, host Python — not the Docker container this time) after fixing review findings 1 (PDF `Paragraph` escaping) and 2 (CSV formula-injection neutralization), plus the two optional non-blocking follow-ups (403-wrong-role test, pdf/csv-format tests for the two previously-uncovered endpoints):

- `ruff check .` (full repo) — **1 pre-existing, unrelated error**: `tests/unit/test_contract_pdf_service.py:39` (`C420` dict-comprehension rule). Confirmed via `git log`/`git diff` this file is untouched by PR-5 (last modified in PR-4's commit `bfc62c7`, 2026-07-24) — out of scope per "no unrelated refactors." `ruff check` on every file this fix pass touched (`app/services/report_export_service.py`, `tests/unit/test_report_export_service.py`, `tests/unit/test_api_reports.py`) — **PASS**, "All checks passed!".
- `ruff format --check .` (full repo) — **PASS**, "116 files already formatted" (no reformatting needed for any file this fix pass touched).

Ruff version in this environment: `0.15.14` (vs. whatever the original PR-5 gate run used) — plausibly why `C420` now fires where it may not have before; not something this fix pass introduced or is in scope to fix.

## Frontend

- `npm run lint` (eslint) — **PASS**, "No issues found"
- `npx tsc --noEmit` — **PASS**, "No errors found"
- `npm run build` (`tsc && vite build`) — **PASS**, built in ~8.5s
- `npm run format:check` (prettier) — **PASS**, "All matched files use Prettier code style!" after auto-formatting the three new files (`ReportsPage.tsx`, `ReportsPage.test.tsx`, `cypress/e2e/reports.cy.ts`) that were initially flagged. Pre-existing repo-wide Prettier drift on unrelated files is untouched, per PR-2/PR-4 precedent.
