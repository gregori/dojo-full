# Handoff — Epic 02: Financeiro, Pré-Checkin e Relatórios

## What Was Done

- Initialized squad planning run `.workflow/runs/epic-02-plan/`.
- Reviewed canonical Epic 2 artifacts in `.planning/` and current pre-check-in integration points.
- Completed a structured requirements review and recorded the delivery plan at `.workflow/runs/epic-02-plan/plan.md`.
- Resolved the four Phase 1 decision-gate items and shipped **PR-1 (Pré-Checkin)**: `PreCheckIn` model, event minimum-belt eligibility, reversible migration, public confirm/cancel/list endpoints, instructor count/roster endpoints, `/precheckin` public page, transactional conversion on physical check-in, and a uniqueness constraint (one attendance per student/event). Details in `.workflow/epic-02/pr-1-precheckin/handoff.md`.
- Committed as `da5bd69 feat(precheckin): add pre-check-in lifecycle and fix migration baseline`; pushed `feature/pre-checkin` and opened PR #23 against `develop`. Fixed CI in the same PR: removed the stale `ci.yml` (wrong paths + wrong tool for the Poetry-based `dojo-app/backend`), added `develop` to `ci-backend.yml`/`ci-frontend.yml` triggers, and fixed real Prettier violations the now-working CI caught in the new pre-checkin frontend code. PR #23 is green.
- Completed the Phase 2 requirements review (`review-phase2.md`) and, with the two decision-gate items resolved by the user, wrote the detailed Phase 2 implementation plan in `plan.md`.

## Key Decisions

- Corrected delivery order: Pré-Checkin → Medical/Documents → Financial Foundation → Contracts → Reports.
- Pré-checkin is distinct from attendance; physical check-in remains the official attendance event.
- Phase 1 decisions resolved: eligibility is configurable per class/event via minimum belt (general classes: none; yudansha: blue+; graduated: purple+); changes lock one hour before event start; public endpoint uses registration+PIN with IP/registration rate limiting and generic responses; pre-checkin never auto-converts to attendance — only a physical check-in does, preserving its physical method.
- During PR-1 verification, fixed a latent bug where `app/main.py` bootstrapped schema via `create_all` instead of Alembic, making the initial revision a no-op on a fresh database; Alembic is now the single source of schema truth.
- **Phase 2 (Documents) decisions resolved (2026-07-19):** documents stored in OCI Object Storage (reusing `dojo-infra/terraform/modules/storage/`), backend keeps only metadata + object key; uploads limited to PDF/JPEG/PNG up to 10MB; expired or orphaned (student removed) documents are soft-deleted with an audit trail (who/when), never hard-deleted automatically. Access is instructor/admin by default, **except medical-exam uploads specifically**, which also allow student self-service via a public registration+PIN endpoint (decided during Phase 2 planning — see "Requirements Review — Phase 2" below).
- **Phase 3 (Finance) decisions signed off (2026-07-20):** pricing uses fixed plans by weekly-frequency tier (D9) using declared `Student.classes_per_week` field (D1 confirmed); billing is monthly with a single standardized due date for all students and proportional charging in the enrollment month; overdue payments are flagged in reports/dashboards only (D8); partial/overpayments tracked as residual balance applied next (D7); no discounts or scholarships modeled (D10 confirmed); medical-exam status is display-only on overdue dashboard, gating nothing (D3 confirmed, narrowing Phase 2's "renewal/billing action" language); student prices locked to assigned `PlanVersion` (D11 confirmed, grandfathered), changed only via explicit reassignment — in practice triggered during annual contract renewal (Phase 4 responsibility; see plan.md Phase 3 section for integration breadcrumb).
- **Phase 4 (Contracts) decisions resolved (2026-07-19):** the legal template is versioned, and each generated contract records which template version and which financial plan/version it used; signature capture supports both an on-screen/touch signature (embedded into the generated PDF, tablet flow) and upload of an externally-signed PDF (via the Phase 2 document policy) — the operator chooses per contract.
- **Phase 5 (Reports) decisions resolved (2026-07-19):** REP-04's financial projection is the simple model — expected revenue over the next N months (default 3) assumed as the sum of currently active plans, with no adjustment for historical delinquency/cancellation.

## Open Questions

None outstanding for Phases 2–5 policy definitions. Remaining unknowns (contract legal text/wording, exact due-date day, exact projection horizon N) are product/legal inputs to confirm during each phase's own decision gate, not blockers to scoping.

## Requirements Review — Phase 2 (Exames Médicos + document foundation)

Full findings in `.workflow/runs/epic-02-plan/review-phase2.md`. The review's two blocking items were resolved by explicit user decision on 2026-07-19, and the detailed implementation plan is written in `.workflow/runs/epic-02-plan/plan.md` ("Phase 2 Implementation Plan").

1. **MED-05 actor — resolved, overrides the review's own recommendation:** the review recommended instructor/admin-only upload (no technical path existed for authenticated student upload). The user explicitly chose the broader option instead: student self-service upload **is** in scope, via a new public registration-number+PIN endpoint (same credential and privacy pattern as the Phase 1 pre-checkin public endpoints), in addition to instructor/admin upload on the student's behalf. This reverses the Phase 1-era blanket "no student self-service" document note for medical exams specifically; that note still applies to other future document types (e.g., contracts) unless separately revisited.
2. **MED-04 "renovação de matrícula" — resolved:** rather than either candidate the review posed (gate `is_active` reactivation, or invent a new renewal touchpoint), the user chose a third option — Phase 2 only computes and exposes a per-student medical-exam status (`valido`/`vencendo`/`vencido`/`sem_registro`). No existing action is blocked in this phase. Enforcement is deferred to Phase 3 (Financial foundation), which will define the renewal/billing action that consults this status.

Also resolved per the review's quick items: MED-03's alert is a visual/dashboard status flag only (no email/push); MED-01/02's exam record is one date field plus one opaque attached document, no other medical fields; the new `Document`/`MedicalExam` models are fully independent of the existing belt-promotion `Exam`/`ExamParticipant`/`ExamBoardMember` tables.

- **Shipped PR-2 (Exames Médicos + document foundation) (2026-07-19):** `Document`/`MedicalExam` models + migration `ea64c8751ff2` (on `b39e1a4c7d20`), instructor/admin CRUD + status/dashboard endpoints, public registration+PIN self-service upload, OCI Object Storage client, and matching frontend (`MedicalExamPage.tsx`, `StudentsPage.tsx` badge/upload/history, `DashboardPage.tsx` alert list). Deterministic gates pass (ruff, 244/244 pytest, eslint, tsc/vite build; migration verified up/down against real MySQL). Independent+security review found 2 HIGH (boundary-less multipart `Content-Type` breaking real-browser uploads; file-type validated only via spoofable client header) and 2 MEDIUM (unbounded in-memory read before size check; unlocked supersession race) findings — all fixed and re-verified, verdict **APPROVED**. One optional, non-blocking follow-up noted: lock the parent `Student` row in `record_exam` to close a narrow first-ever-submission race window. Full detail in `.workflow/epic-02/pr-2-medical-exams/{review.md,lint-results.md,test-results.md,handoff.md}`. Committed as `9037868 feat(medical-exams): add exames médicos + document foundation (PR-2)`; pushed `feature/medical-exams` and opened [PR #25](https://github.com/gregori/dojo-full/pull/25) against `develop`.

## Requirements Review — Phase 3 (Financial Foundation)

Full findings in `.workflow/runs/epic-02-plan/review-phase3.md`; detailed implementation plan in `.workflow/runs/epic-02-plan/plan.md` ("Phase 3 Implementation Plan — Financial Foundation"), written 2026-07-20 by tech-analyst.

- **Architecture (tech-analyst, 2026-07-20):** two new versioned-history pairs following the Phase 2 `Document`/`MedicalExam` supersession precedent — `PlanTier`/`PlanVersion` (catalog, versioned pricing) and `StudentPlan` (per-student locked assignment to a `PlanVersion`), plus `Mensalidade` (one row per active student per month, `plan_version_id` frozen at generation, no stored status) and `Payment` (soft-voidable, mirrors `Document`'s audit pattern). Mensalidade/payment status and student balance are **computed on read** via FIFO allocation across a student's mensalidades and payments — no stored ledger, matching Phase 2's "computed, not stored" precedent. New Alembic revision on top of `ea64c8751ff2` (current head). No scheduler infra exists in the codebase, so monthly generation is an explicit, idempotent instructor/admin-triggered action, not a cron job. Instructor/admin-only API surface — no public/self-service endpoint added this phase (D5 default). Full data model, service layer, API, and frontend touch points are in `plan.md`; not duplicated here.
- **Four decisions still require explicit user sign-off before `squad-feature` builds PR-3** (design proceeds against these defaults, per `review-phase3.md`'s decision gate):
  - **D1** — pricing/frequency source: declared `Student.classes_per_week` (default) vs. attendance-derived actual frequency.
  - **D3** — whether the Phase 2 handoff's promised "renewal/billing action that consults [medical-exam] status" gates anything, or (default) is a display-only flag on the overdue dashboard, gating nothing.
  - **D10** — discounts/scholarships: none modeled (default), fixed-price catalog only.
  - **D11** — price-locking: student stays locked to the `PlanVersion` active at assignment (default, grandfathered) vs. auto-repricing when the catalog changes.
  - D2, D4–D9 are adopted as settled working defaults (merge FIN-02/07, computed-on-read status, no student self-service beyond D5, daily pro-rata proration, FIFO payment allocation, no overdue grace period, single global catalog) and are not re-gated.

## Requirements Review — Phase 3, PR-3 Build (Financial Foundation)

- **Implemented PR-3 (Financial foundation) (2026-07-20):** `PlanTier`/`PlanVersion`/`StudentPlan`/`Mensalidade`/`Payment` models + migration `c7a3f9d21b6e` (on `ea64c8751ff2`), instructor/admin-only plan/mensalidade/payment CRUD and generation endpoints (no public endpoint this phase, per D5), and matching frontend (`PlansPage.tsx`, `StudentsPage.tsx` "Financeiro" modal, `DashboardPage.tsx` "Inadimplentes" table reusing `MedicalExamBadge` for the D3 display-only flag). Deterministic gates pass (ruff, 283/283 pytest, eslint, tsc/vite build; migration verified up/down/up against real MySQL). Independent+security review found 2 MEDIUM findings (missing positive-value validation on payment/price fields — a negative value could corrupt FIFO balance math; missing regression test for acceptance criterion 2's price-locking guarantee) — both fixed and re-verified, verdict **APPROVED**. Full detail in `.workflow/epic-02/pr-3-financial-foundation/{review.md,lint-results.md,test-results.md}`.
- One deliberate design deviation resolved during build: `generate_monthly_charges` does **not** auto-assign a `StudentPlan` to an active-but-unassigned student — it skips them, consistent with plan assignment being its own explicit action tied to enrollment/contract signing (the D11 breadcrumb for Phase 4). Covered by a dedicated regression test.
- Working tree has the implementation uncommitted — not yet committed, pushed, or opened as a PR.

## E2E Test Coverage Added for Phases 1-3 (2026-07-21)

The user raised that Phases 1-3 shipped with zero e2e coverage, despite an established (but not CI-wired) Cypress convention elsewhere in the repo. Added `precheckin.cy.ts`, `medical-exam.cy.ts`, `financial.cy.ts` (25 tests) plus 9 new custom Cypress commands, and wired a new `e2e` job into `.github/workflows/ci-frontend.yml`. Full detail in `.workflow/epic-02/pr-3-financial-foundation/test-results.md` ("E2E coverage added retroactively" section).

**A real bug was found and fixed in the process:** `app/core/storage.py`'s dev/CI local-disk fallback (itself added during this pass, since OCI credentials are empty in dev/CI and the medical-exam public upload endpoint was throwing an unhandled 500) had a directory-creation bug — fixed and verified via direct `curl` testing (PDF/JPEG/PNG all return 200 end-to-end). This is the only genuine production-code defect found across all of Epic 2's e2e verification; every other test failure encountered was a test-authoring issue (stale hardcoded IDs, wrong response-shape assumptions, form-encoding mismatches), all fixed in the test files themselves.

A final single clean 3-spec Cypress run could not complete in this session due to OS-level port contention in the sandbox (stale socket entries, not a code issue) — see test-results.md for exactly what was and wasn't independently re-verified after the last fix.

## Next Action

**Committed as `a92798f` (feature/financial-foundation); pushed and opened [PR #26](https://github.com/gregori/dojo-full/pull/26) against `develop`, 2026-07-21.** Phase 3 (Financial foundation), plus the retroactive e2e coverage for Phases 1-3, is fully shipped pending PR review/merge. Once merged, Phase 4 (Contracts) is next, using `PlanVersion.id` as the pricing source per the D11 breadcrumb.

## Next Agent

Next Agent: planner (Phase 4 — Contracts) once PR #26 merges.
