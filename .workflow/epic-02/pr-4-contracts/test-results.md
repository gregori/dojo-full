# Test Results — PR-4: Contracts

Re-verified by the orchestrating session after the fix pass for review findings 1-4, 2026-07-23, against the real `dojo-mysql` container (`docker compose up -d mysql backend`, tests run via `docker exec dojo-backend poetry run pytest -q`).

## Backend (pytest)

**331 passed, 0 failed** (283 pre-existing + 48 new/changed for contracts, up from 38 at the prior pass — the fix for findings 1/2 added regression coverage: `test_no_plan_reassignment_committed_when_student_data_missing`, `test_no_plan_reassignment_committed_when_no_active_template`, `test_third_call_during_renewal_reuses_the_draft_not_a_second_orphaned_one`, `test_prefers_the_draft_when_a_signed_and_draft_contract_coexist`, `test_falls_back_to_signed_when_no_draft_exists`, `test_returns_none_when_no_draft_or_signed_contract_exists`). Coverage 94% total; `app/services/contract_service.py` now **100%** (was 92%), `app/schemas/contract.py` **100%**.

## Frontend (Jest)

`npx jest` — **33 passed, 0 failed** across 8 suites (unchanged — findings 1-4 were backend-only, no frontend fix needed).

## Findings verified fixed (code-level, pending independent reviewer re-confirmation)

1. HIGH (atomicity) — `generate_for_matricula` now validates merge fields and looks up the active template *before* calling `StudentPlanService.assign`, per `contract_service.py:85-93`.
2. HIGH (ordering) — `get_active_or_draft` now deterministically prefers `draft` over `signed`, per `contract_service.py:21-34`.
3. MEDIUM (signature payload) — `ContractSignOnScreenRequest.signature_png` now has `Field(max_length=MAX_SIGNATURE_PNG_LENGTH)` (`schemas/contract.py`), and `_decode_signature_png` in `api/contracts.py` catches `binascii.Error`/`ValueError` and raises a clean 400.
4. LOW (filename) — `download_contract` now derives the extension via `mimetypes.guess_extension(mime_type)` instead of hardcoding `.pdf` (`api/contracts.py:112`).
5. Non-blocking (template-version supersession race) — unchanged, still accepted per PR-2 precedent.

## Cypress E2E Tests (`contracts.cy.ts`) — Execution & Root Cause Analysis (2026-07-23, Tester session)

### Initial State
- All 6 test scenarios in contracts.cy.ts attempted but failing: 1 pass (D5 authorization API test), 5 failures.
- Failures: tests created students but couldn't find them in the GET /api/v1/students response that should appear in the UI table.

### Root Cause: Missing ORDER BY in Student Query
When running contracts.cy.ts against a live database with 100+ existing test students from prior e2e runs:
- Backend endpoint `GET /api/v1/students` defaults to `limit=100` but had NO `ORDER BY` clause
- StudentService.get_students() would return results in undefined order (implementation-dependent, typically insertion order but not guaranteed)
- Newly created students, when beyond the first 100 results, were invisible to the e2e tests
- Real bug: `/app/services/student_service.py` line 38-46 queries without explicit sort order

### Fix Applied
**File: `dojo-app/backend/app/services/student_service.py`** (line 46)

Changed:
```python
return query.offset(skip).limit(limit).all()
```

To:
```python
return query.order_by(Student.created_at.desc()).offset(skip).limit(limit).all()
```

Rationale: Sort by `created_at DESC` (newest first) ensures newly created students appear at the start of results, guaranteed to be on page 1 regardless of total student count.

### Verification
- **Backend pytest re-run after fix:** 331 tests passed (0 failed). No order-dependent assertions broken in existing tests.
- **Cypress e2e re-run after fix:** Scenario 1 (D1) now progresses to modal rendering stage (student successfully found in table). Scenarios 2-5 still encounter separate modal/contract rendering issues (not part of this root cause), Scenario 6 (authorization) passes as before (1/6 passing; 5/6 still failing but for different reasons: modal display, not data visibility).

### Summary
- **Real app bug found and fixed:** Missing ORDER BY in student list query could hide newly created records on large datasets.
- **Fix verified safe:** All 331 backend pytest pass post-fix; no regressions.
- **Remaining failures** (Scenarios 1-5 modal rendering) are distinct from this data-visibility issue and require further investigation or are test-authoring improvements (not blocking this PR's core feature, per review gate criteria).

## Not yet run this pass (non-blocking per review decision)

- Frontend Prettier `format:check` — not spot-checked this pass (same non-blocking note carried from PR-2/PR-3).

## Continued E2E Investigation (2026-07-24, Tester session follow-up)

### Additional Test Helper Bug Fixed
**File: `dojo-app/frontend/cypress/support/e2e.ts`** (lines 52-53)

Found and fixed missing return statement in `cy.createStudent()` command:
```typescript
// Before: cy.getBeltId().then((beltId) => { ... return cy.wrap(...) })
// After:  return cy.getBeltId().then((beltId) => { return cy.request(...).then(...) })
```

The outer `cy.getBeltId().then()` callback was not returning its result, causing student data to be undefined in test assertions.

**Verification**: After fix, test data initialization confirmed working; improved test progression (students now properly created and accessible for modal interaction).

### Current E2E Status: 1/6 Passing, 5/6 Failing (UNCONFIRMED ROOT CAUSES)

**Passing**: Scenario 6 (D5 - Authorization: non-authorized caller gets 401) — 2051ms

**Failing** (unresolved, root causes inconclusive):
1. **Scenario 1 (D1 - Generate Contract)**: Row found via `cy.contains('tr', studentData.full_name)` but `<td>` element reports "not visible because content is being clipped by overflow" at line 93. studentData properly initialized; cy.contains locates a row; but row's cells remain hidden despite element existence. Likely CSS overflow/layout issue or row-selection accuracy under load.

2. **Scenario 2 (D2/D3 - On-screen Signature)**: Modal opens for correct student, but cannot find button text '/Confirmar Assinatura/i' expected at line 189. Button either missing, not rendered, or text content differs from test expectation.

3. **Scenario 3 (D6 - Contract Renewal)**: `cy.within()` call at line 307 matches 2 elements instead of 1. Suggests `cy.contains('tr', ...)` or similar selector is over-matching, requiring `.first()` narrowing.

4. **Scenario 4 (D4 - Upload PDF)**: Cannot find text '/Rascunho/i' (Draft status badge) expected at line 395. Contract created via API in beforeEach; modal opens; but draft status text not visible.

5. **Scenario 5 (D7 - Regenerate Draft)**: Same visibility issue as Scenario 1 (row `<td>` overflow clipping) at line 490.

### Investigation Approach (Attempted, Inconclusive)
- Verified backend StudentService.get_students() has no eager-loading or join-duplication issues
- Verified StudentResponse schema has no problematic serialization
- Attempted browser console log capture via cy.on('window:console') and cy.intercept for network inspection
- Checked for stale React Query cache between test scenarios
- Added diagnostic logging (removed after investigation)

**Conclusion**: Remaining failures appear to be **test-layer or frontend UI rendering issues**, not data/backend contract generation issues. The contract creation itself (POST /matricular, POST /sign-on-screen) succeeds (status 201 returned); the failures are at UI assertions (missing text, overflow clipping). **Root causes remain unconfirmed** — would require deeper DOM inspection, browser DevTools video analysis, or frontend unit test additions.

### No Further Fixes Applied This Session
Given time spent without reaching confirmed root causes, this session closes with fixes for ORDER BY and cy.createStudent only. Remaining 5 failures require either: separate e2e debugging session with video/DOM capture, or acceptance that test scenarios may need refactoring (e.g., using data attributes instead of text content matching).

## Final Resolution — All 6 Scenarios Green (2026-07-24, direct root-cause session)

Picked up from the inconclusive state above by investigating the actual rendered DOM and network activity directly (screenshots, live docker stack, `git diff` review) rather than further trial-and-error. Confirmed root causes for every remaining failure, all fixed, then re-ran the full spec 5 consecutive times clean (6/6 each run) plus a final full-suite confirmation (backend pytest, frontend Jest, ruff, eslint, tsc, vite build).

### Root causes found and fixed

1. **Real infra bug — Docker/Poetry entrypoint completely broken.** `docker-compose.yml` declared an anonymous volume `- /app/.venv` to shield the backend container from a bind-mounted host `.venv`, but Poetry 2.4.1 auto-creates an empty in-project `.venv` on the *first* `poetry run` invocation regardless of `virtualenvs.create = false` — and once created, `poetry run` prefers that empty venv over the correctly-populated global site-packages (`ModuleNotFoundError: sqlalchemy`), hanging `entrypoint.sh`'s `until poetry run python ...` DB-readiness loop forever. Since `virtualenvs.create false` is set at build time too (`Dockerfile.dev`), dependencies live entirely in the global interpreter and `poetry run` is unnecessary. Fixed by dropping the `poetry run` prefix from all four invocations in `entrypoint.sh` (DB check, `alembic upgrade head`, `seed_database.py`, `uvicorn`) and removing the now-pointless `- /app/.venv` volume line from `docker-compose.yml`. This was blocking the stack from starting at all — not a test bug, a genuine local/CI-adjacent infra defect.
2. **Real frontend bug — main students table missing horizontal scroll.** `StudentsPage.tsx`'s primary table wrapper used `overflow-hidden` while every other table in the same file (medical exam history, mensalidades, contract history) correctly uses `overflow-x-auto`. With the growing number of per-row action-button columns (medical exam, financeiro, contrato) added across PR-2/3/4, the table now overflows a standard/Cypress-default viewport width, and `overflow-hidden` clipped the rightmost "Contrato" button out of the interactive area entirely (not just requiring scroll — genuinely inaccessible). Fixed by wrapping the table in `<div className="overflow-x-auto">`, matching the established pattern.
3. **Test bug (Scenario 2) — wrong expected button text.** Test expected a button reading "Confirmar Assinatura"; the actual button (`StudentsPage.tsx`) reads "Assinar". Fixed the test's expected text.
4. **Test bug (Scenario 2) — wrong event type for signature capture.** The canvas uses `signature_pad@5.1.3`, which listens for Pointer Events only (no legacy mouse-event fallback in this major version). The test fired `mousedown`/`mousemove`/`mouseup`, which the library never saw, so the canvas stayed empty and `handleSignOnScreen`'s `isEmpty()` guard silently no-op'd (`cy.wait('@sign')` timed out with "no request ever occurred"). Fixed by switching the test to `pointerdown`/`pointermove`/`pointerup` with `pointerId`/`isPrimary`/`button`/`buttons` set.
5. **Test bug (Scenarios 1 & 5) — ambiguous `cy.contains(fullName)` match.** After opening the contract modal, `cy.contains(studentData.full_name)` (no selector) matched the *background* students-table row (still in the DOM behind the modal overlay, same page) in preference to the modal's own `<h3>Contrato — {full_name}</h3>` heading, and the background row was correctly judged not-visible (covered/clipped). Fixed by scoping to `cy.get('h3').contains(...)`.
6. **Test bug (Scenario 3) — `cy.get('table')` matched 2 elements.** With the contract modal open, `cy.get('table')` unscoped matches both the background students table and the modal's own "Histórico" table, so `.within()` correctly refused ("requires... a single result, but... 2 elements"). Fixed with `.last()` (the modal's table renders later in the DOM).
7. **Test bug (Scenario 3) — history table below the fold inside the modal's own scroll area.** The modal is `position: fixed` with `max-h-[90vh] overflow-y-auto`; `.should('be.visible')` is a passive assertion and does not auto-scroll (unlike action commands). The "Histórico" table's badges were genuinely below the currently-scrolled viewport of the modal. Fixed with explicit `.scrollIntoView()` before the visibility assertions (applied to the Scenario 1/5 `<h3>` checks too, for the same reason).
8. **Test flakiness (Scenarios 2/3/4/5, ~1-in-4 runs) — beforeEach contract precreation not asserted.** Each scenario's `beforeEach` precreates a draft (and, for Scenario 3, signs it) via raw `cy.request(..., failOnStatusCode: false)` with no assertion on the response and no explicit `return`, so an occasional slow/failed precreation call surfaced only later as a mysterious "Rascunho"/"Assinado" not found in the test body, well after the real cause. Fixed by explicitly `return`-ing the request chain and asserting `response.status` (`201`/`200`) immediately in the `beforeEach`, plus bumping the two post-modal-open status-badge assertions from the 4s default to `{ timeout: 10000 }` to give React Query's fetch-on-mount headroom under load. Verified with 5 consecutive full-suite runs, all 6/6 green.

### Final verification (this session, against the fixed stack)

- `contracts.cy.ts`: **6/6 passing**, 5 consecutive clean full-suite runs (no flakes after fix #8).
- Backend: **331 passed, 0 failed** (`docker exec dojo-backend python -m pytest -q`, entrypoint fix confirmed not to affect app behavior).
- Frontend: **33 passed, 0 failed** (`npx jest`).
- Backend lint: `ruff check` and `ruff format --check` clean.
- Frontend lint/build: `eslint src` clean, `tsc --noEmit` clean, `vite build` clean.

### Files changed this pass

- `docker-compose.yml` — removed stale `- /app/.venv` anonymous volume (backend service).
- `dojo-app/backend/entrypoint.sh` — removed `poetry run` prefix (4 call sites); global site-packages already has all deps per `virtualenvs.create false`.
- `dojo-app/frontend/src/pages/StudentsPage.tsx` — wrapped the main students table in `overflow-x-auto` (2 lines).
- `dojo-app/frontend/cypress/e2e/contracts.cy.ts` — all test-side fixes above (#3–#8).

**Contracts e2e is now fully green and the fixes are backend/frontend-regression-tested. Ready for commit.**

## Known non-blocking issue (carried over, still unfixed, out of scope for this PR)

`scripts/seed_database.py` still calls `Base.metadata.create_all()` after `alembic upgrade head` — same dual-schema-authority bug already fixed once in `app/main.py`. Flagged as a follow-up for a future small fix.
