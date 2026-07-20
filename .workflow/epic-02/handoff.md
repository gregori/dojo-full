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
- **Phase 3 (Finance) decisions resolved (2026-07-19):** pricing uses fixed plans by weekly-frequency tier (not a per-class dynamic rate); billing is monthly with a single standardized due date for all students (e.g. day 5), with proportional charging in the enrollment month; overdue payments are flagged in reports/dashboards only — no automatic check-in or access block in this epic; partial and overpayments are accepted and tracked as a residual balance (owed or credit) applied to the next charge.
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

## Next Action

- Wait for CI to run on PR #25 and for it to be merged. Once merged, start Phase 3 (Financial foundation, PR-3) per `plan.md`'s "Later Phase Contracts" section — pricing tiers, billing cycle/due dates, and overdue handling policies are already resolved (see "Key Decisions" above); a detailed Phase 3 implementation plan (mirroring Phase 2's) still needs to be written before `squad-feature` can build it.
