# Independent + Security Review — PR-3: Financial Foundation

## Verdict: APPROVED WITH FOLLOW-UPS → both follow-ups fixed, re-verified

Initial review verdict: **APPROVED WITH FOLLOW-UPS**. The implementation is a faithful, correct build of `plan.md`'s "Phase 3 Implementation Plan" and correctly implements the trickiest specified nuance (the late-breaking "don't auto-create `StudentPlan` during generation" change, with a dedicated regression test). No High-severity or security-blocking issues were found.

## Findings

1. **[Medium — Data integrity/Security] RESOLVED.** No server-side positive-value validation on `PaymentCreate.amount`, `PlanTierCreate.price`/`weekly_frequency`, `PlanPriceUpdate.price`. A negative payment amount, submitted directly to the JSON API (bypassing the frontend's cosmetic `min="0"` HTML attribute), could corrupt `BalanceService.allocate`'s FIFO math (negative `remaining`, nonsensical status/balance). Fixed: `Field(gt=0)` added to the price/amount fields, `Field(ge=1)` to `weekly_frequency`, rejected by FastAPI request validation (422) before reaching service logic.
2. **[Medium — Test coverage gap on a named acceptance criterion] RESOLVED.** No test exercised acceptance criterion 2 ("editing a tier's price never repriced an already-assigned student") end-to-end. Code was structurally correct (assign/set_price never touch each other's tables) but unverified. Fixed: two new tests in `test_student_plan_service.py::TestPriceLocking` prove both the `StudentPlan` lock and a freshly generated `Mensalidade` retain the original `PlanVersion`/price after a subsequent `set_price` call.
3. **[Low — polish, non-blocking]** `PlanService.set_price`/`create_tier` have no upper-bound sanity check on `price`/`weekly_frequency`. Not addressed — purely cosmetic, covered substantively by finding 1's lower-bound fix.

## Areas reviewed and confirmed correct

- **Correctness:** FIFO payment allocation, mensalidade status priority (paid > overdue > partial > open, no grace period per D8), proration formula (matches D6 exactly, verified against independent arithmetic), idempotent `generate_monthly_charges` (unique constraint + per-student rollback-safe), plan-tier-lookup-gap fails loudly (400, names the missing frequency), `StudentPlan` never auto-created during generation (confirmed in final code + dedicated regression test).
- **Security:** every new route in `plans.py`/`mensalidades.py`/`payments.py` uses `get_current_instructor_or_admin` (matches Phase 2 precedent exactly); no public/unauthenticated finance endpoint (D5); no raw SQL; no sensitive data leakage.
- **Data integrity:** all monetary columns use `Numeric(10, 2)`, no floats; `Payment` soft-void audit trail mirrors `Document`'s pattern, never hard-deleted; migration downgrade correctly reuses the battle-tested index-drop-order fix from `ea64c8751ff2`.
- **Phase 2 consistency:** append-only-supersession pattern, computed-on-read status, docstring/lint conventions, and the unrelated belt-promotion `exams`/`exam_participants`/`exam_board_members` tables are untouched.

No further review cycle required — the fixes are small, contained, and directly verified by the new/updated tests plus a green full suite (283/0).
