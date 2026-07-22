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

## Frontend Jest unit tests — NOT YET WRITTEN (open gap)

Confirmed via real CI log (`gh run view --job=88798474120 --log`, run `29879985293`, PR #26, 2026-07-22): the `test` job's "Run unit tests" step (`npm test -- --coverage --watchAll=false --passWithNoTests`) genuinely runs Jest, finds **zero** test files anywhere in `dojo-app/frontend/src`, and only reports success because of the `--passWithNoTests` flag:

```
> jest --coverage --watchAll=false --passWithNoTests
No tests found, exiting with code 0
All files | 0% stmts | 0% branch | 0% funcs | 0% lines
```

This is a pre-existing, repo-wide condition (not introduced by this PR) — no `.test.ts(x)`/`.spec.ts(x)` file exists anywhere in the frontend, despite Jest, `@testing-library/react`, `@testing-library/jest-dom`, and `@testing-library/user-event` already being installed dependencies and `jest`/`jest --watch` scripts already defined in `package.json`. **The user has asked for real Jest unit tests to be written** (component/page tests using the already-installed Testing Library stack) as separate follow-up work from the e2e effort below — there is no existing pattern in this repo to follow (greenfield), so establish one deliberately (test file location convention, e.g. co-located `*.test.tsx` or a `__tests__/` dir; how to mock `axios`/`react-query` calls, etc.) rather than guessing.

## E2E coverage added retroactively for Epic 2 Phases 1-3 (2026-07-21/22)

The user flagged that Phases 1-3 shipped with zero e2e coverage despite an established Cypress convention elsewhere in the repo (`checkin.cy.ts`, `exams.cy.ts`, `students.cy.ts`, etc. — none of which run in CI either, a pre-existing gap). Added `cypress/e2e/precheckin.cy.ts` (5 tests), `medical-exam.cy.ts` (10 tests), `financial.cy.ts` (10 tests) — 25 tests total — plus 9 new custom Cypress commands in `cypress/support/e2e.ts` (`getEventTypeId`, `getBeltId`, `createPlanTier`, `assignStudentPlan`, `generateMensalidades`, `recordPayment`, and fixes to `getAuthToken`/`createStudent`/`createEvent`). Wired a new `e2e` job into `.github/workflows/ci-frontend.yml` (Docker Compose stack + health checks + `cypress run`, separate from the existing lint/unit/build job, `needs: test`).

**A genuine production bug was found and fixed during this verification pass:** `app/core/storage.py`'s local-disk fallback (added to let the medical-exam upload flow run without real OCI credentials in dev/CI) only created the top-level `local_storage/documents` directory, not the nested subdirectories implied by a document's storage key (e.g. `medical-exams/<student_id>/<file>.pdf`) — every upload failed with an unhandled `FileNotFoundError` → 500. Fixed by creating `destination.parent` instead of the fixed top-level directory.

### Real CI result (confirmed, 2026-07-22)

PR #26, workflow run [29879985293](https://github.com/gregori/dojo-full/actions/runs/29879985293), job `e2e` (88798587287): **22/25 passing (88%)**.

- `precheckin.cy.ts` — **5/5 passing**.
- `financial.cy.ts` — **10/10 passing**.
- `medical-exam.cy.ts` — **7/10 passing**, 3 failing, all three in the "Envio Público de Exame Médico" (public upload) describe block:
  1. **`deve aceitar upload válido de PDF via registro e PIN`** — `AssertionError: Timed out retrying after 4000ms: Expected to find content: '/sucesso|registrado/i' but never did.` The storage.py fix resolved the underlying 500 (confirmed separately via direct `curl` — PDF/JPEG/PNG all return 200 from the API), so this is now a **frontend UI assertion failure**: the test uploads via the real `/medical-exam` page UI and waits for a success message (`cy.contains(/sucesso|registrado/i)`) that never appears, even though the API call itself presumably succeeds. Needs investigation into `MedicalExamPage.tsx`'s post-submit UI state/messaging, or the test's wait/assertion timing.
  2. **`deve aceitar upload válido de JPEG`** — `AssertionError: expected 400 to equal 200`.
  3. **`deve aceitar upload válido de PNG`** — `AssertionError: expected 400 to equal 200`.
  Both assert `interception.response?.statusCode).to.eq(200)` after intercepting `POST /api/v1/medical-exams/public/submit`. Direct `curl` testing (bypassing Cypress/the browser) with equivalent minimal JPEG/PNG magic-byte content and an explicit `Content-Type` on the multipart file part returned **200 successfully** against the same backend code — so `_validate_file`'s magic-byte check (`app/services/medical_exam_service.py:60-65`, `MIME_SIGNATURES` dict) is confirmed correct. The 400 is therefore most likely caused by how Cypress's `cy.get('input#exam-file').selectFile({ contents, fileName, mimeType })` constructs the multipart file part's `Content-Type` header in an actual browser upload (via the real `MedicalExamPage.tsx` form submit) — not proven yet, just the leading hypothesis. Needs direct verification (e.g. intercept and log the actual outgoing request headers/multipart body in a browser dev-tools/network capture, or add a temporary backend debug log of the received `file.content_type` during a Cypress run) rather than continued guessing.

**Next step for a fresh session:** fix these 3 medical-exam failures (1 UI-timing/messaging issue, 2 likely-Cypress-multipart issues — confirm the JPEG/PNG root cause with actual evidence before changing anything), then re-run the `e2e` CI job (or `npx cypress run --spec cypress/e2e/medical-exam.cy.ts` locally against a real running stack) to confirm 25/25, then write the Jest unit test suite described above as separate follow-up work.
