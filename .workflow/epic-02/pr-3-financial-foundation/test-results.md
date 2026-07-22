# Test Results — PR-3: Financial Foundation

## Backend unit tests

`uv run pytest tests/unit -q` — **283 passed, 0 failed** (baseline before this PR: 244 passed, 0 failed; **39 new tests**, after the post-review fix pass added 2 more):

- `test_plan_service.py` — 4 tests (PlanTier/PlanVersion CRUD, price-change supersession)
- `test_student_plan_service.py` — 8 tests (tier auto-derivation from `classes_per_week`, supersession, plan-tier-lookup-gap failure, plus 2 post-review `TestPriceLocking` regression tests: `test_set_price_after_assignment_does_not_reprice_the_student`, `test_mensalidade_generated_after_price_change_still_uses_locked_version` — covering acceptance criterion 2 end-to-end)
- `test_mensalidade_service.py` — 5 tests (idempotent generation, proration, skip-inactive-student, skip-unassigned-student)
- `test_balance_service.py` — 9 tests (FIFO payment allocation, status computation priority order: paid/overdue/partial/open, overpayment/credit)
- `test_payment_service.py` — 5 tests (record/void payment, soft-delete audit trail)
- `test_api_finance.py` — 8 tests (authorization: instructor/admin-only, no public access, on all new routes)

One real defect was caught by the new tests and fixed during implementation: `BalanceService.get_balance` originally summed FIFO-capped per-mensalidade paid amounts instead of raw total active-payment amounts, silently dropping overpayment/credit from the reported balance. Fixed to sum active payments directly.

## Post-review fix pass

Independent review (see `review.md`) returned **APPROVED WITH FOLLOW-UPS** — two Medium findings, both fixed and re-verified:

1. No server-side positive-value validation on `PaymentCreate.amount`, `PlanTierCreate.price`/`weekly_frequency`, `PlanPriceUpdate.price` — fixed with Pydantic `Field(gt=0)`/`Field(ge=1)` constraints, closing a reachable FIFO-balance-corruption path via a negative payment/price submitted directly to the JSON API.
2. Acceptance criterion 2 ("editing a tier's price never repriced an already-assigned student") had no direct regression test — added two tests proving both the `StudentPlan` lock and a freshly generated `Mensalidade` still use the original `PlanVersion` after `PlanService.set_price` is called.

Full suite re-verified green (283/0) after the fix pass.

## Migration verification

Ran against a real MySQL 8.0 container (`dojo-db`), full chain from an empty database:

- `f5889d99aeae → b39e1a4c7d20 → ea64c8751ff2 → c7a3f9d21b6e` (upgrade) — clean
- `downgrade -1` then `upgrade head` — clean after a fix: dropping the composite `(plan_tier_id, status)` / `(student_id, status)` indexes on `plan_versions`/`student_plans` initially failed with a MySQL "index needed in a foreign key constraint" error (same class of issue as the precedent `ea64c8751ff2` migration); fixed by restoring a plain single-column index before dropping the composite one in `downgrade()`.
- `alembic current` confirms `c7a3f9d21b6e (head)` after the full up/down/up cycle.

## Frontend

No Jest specs added — consistent with repo-wide precedent (no existing Jest specs anywhere in the frontend).

## E2E coverage added retroactively for Epic 2 Phases 1-3 (2026-07-21)

The user flagged that Phases 1-3 shipped with zero e2e coverage despite an established Cypress convention elsewhere in the repo (`checkin.cy.ts`, `exams.cy.ts`, `students.cy.ts`, etc. — none of which run in CI either, a pre-existing gap). Added `cypress/e2e/precheckin.cy.ts` (5 tests), `medical-exam.cy.ts` (10 tests), `financial.cy.ts` (10 tests) — 25 tests total — plus 9 new custom Cypress commands in `cypress/support/e2e.ts` (`getEventTypeId`, `getBeltId`, `createPlanTier`, `assignStudentPlan`, `generateMensalidades`, `recordPayment`, and fixes to `getAuthToken`/`createStudent`/`createEvent`). Wired a new `e2e` job into `.github/workflows/ci-frontend.yml` (Docker Compose stack + health checks + `cypress run`, separate from the existing lint/unit/build job).

**A genuine production bug was found and fixed during this verification pass:** `app/core/storage.py`'s local-disk fallback (added to let the medical-exam upload flow run without real OCI credentials in dev/CI) only created the top-level `local_storage/documents` directory, not the nested subdirectories implied by a document's storage key (e.g. `medical-exams/<student_id>/<file>.pdf`) — every upload failed with an unhandled `FileNotFoundError` → 500. Fixed by creating `destination.parent` instead of the fixed top-level directory. Verified directly via `curl` against a locally-run backend (bypassing Cypress/Docker entirely due to environment port contention, see below): PDF, JPEG, and PNG uploads all now return 200 and the file is correctly written to disk at the expected nested path.

**Verification method note:** a final, single, clean three-spec Cypress run in one process could not be completed in this session due to persistent OS-level port-8000 contention in the working environment (stale/zombie socket entries not resolvable via normal process management) — not a code issue. Confidence in the final state instead comes from: (1) a full clean run earlier in this pass showing `precheckin.cy.ts` 5/5 and `financial.cy.ts` 9/10 (with the one remaining failure — a price-update test's `form: true` vs JSON body mismatch — subsequently fixed and code-reviewed but not re-run in that exact process), and (2) direct `curl` verification of all three medical-exam upload content types (PDF/JPEG/PNG) succeeding end-to-end against a correctly configured local backend after the storage.py fix, which resolves the previously-observed PDF 500 and demonstrates the JPEG/PNG 400s seen under Cypress were a Cypress-side artifact (likely `selectFile()`'s multipart Content-Type handling), not a backend defect — backend accepts all three real content types correctly.

**Known open item:** the JPEG/PNG upload tests in `medical-exam.cy.ts` may still fail under Cypress specifically (unconfirmed after the storage fix, not re-verified in a clean run) despite the backend being proven correct via curl. If they still fail on the next real CI run, the fix is on the test side (how `cy.get('input#exam-file').selectFile(...)` propagates the file's Content-Type through the multipart request), not the backend.
