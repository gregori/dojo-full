# Epic 2 Plan — Financeiro, Pré-Checkin e Relatórios

## Status

Phase 1 (Pré-Checkin) shipped as `da5bd69`. Phase 2 (Exames Médicos + document foundation) ready for `squad-feature`. Phase 3 (Financial foundation) plan complete and decisions signed off (2026-07-20); ready for `squad-feature`. Phases 4–5 policies defined but need implementation planning.

## Scope and Outcome

Epic 2 extends the completed dojo-management MVP with advance class confirmation, medical-document controls, contracts, financial controls, and exportable reports. It comprises 27 requirements across five ordered implementation phases.

## Requirements Review

Structured review completed on 2026-07-19. The detailed findings are in [review.md](review.md). Key outcomes:

- Phase 1 needs a defined event-state matrix, public-endpoint security behavior, confirmation eligibility, and idempotent physical-check-in conversion.
- The existing one-hour cutoff must be exercised server-side and added to acceptance tests.
- Reports that require financial data must follow the financial phase.
- Contracts need an authoritative plan/pricing source before their required fields can be generated.

## Corrected Delivery Order

| Order | Phase | Requirements | Deliverable | Gate |
|---|---|---|---|---|
| 1 | Pré-Checkin | PRE-01–PRE-05 | Separate pre-checkin lifecycle integrated with physical attendance | Resolve Phase 1 decisions below |
| 2 | Exames Médicos + document foundation | MED-01–MED-06 | Medical validity tracking and reusable controlled PDF storage pattern | Define storage and document-access policy |
| 3 | Financial foundation | FIN-01–FIN-07 | Plans, fees, payments, overdue rules, frequency pricing | Define billing and pricing policy |
| 4 | Contracts | CON-01–CON-04 | Generated and signed contracts using the authoritative financial plan | Define legal template/versioning |
| 5 | Reports | REP-01–REP-05 | PDF/CSV reports for exams, attendance, and finance | Define report projection formula |

This changes the previous order so financial reporting follows financial data, and contracts consume an established plan/pricing model.

## Phase 1 Implementation Plan — Pré-Checkin

### Intended design

- Add `pre_checkins` as a distinct relation to `events` and `students`; do not treat a confirmation as attendance.
- Provide public, rate-limited confirmation endpoints using registration number plus PIN, mirroring the existing `/api/v1/checkin` interaction pattern.
- Add instructor-only endpoints/data to show future-event confirmation counts and confirmed students.
- Add `/precheckin` as a public React page; extend `EventsPage` with confirmation badges and an event-detail roster.
- During a physical check-in, atomically convert an active matching pre-checkin and create at most one official attendance record.
- Retain the actual physical method (`tablet` or `qrcode`) as the attendance method; model pre-confirmation separately rather than overwriting it with `precheckin`.

### Planned touch points

| Layer | Primary files/modules |
|---|---|
| ORM and migration | `backend/app/models/__init__.py`, Alembic revision |
| API schemas | `backend/app/schemas/` and schema exports |
| API routes | `backend/app/api/checkin.py`, new pre-checkin router, `backend/app/api/events.py` |
| Domain services | `backend/app/services/attendance_service.py`, new pre-checkin service, `event_service.py` |
| Public UI | `frontend/src/App.tsx`, new `pages/PreCheckInPage.tsx`, `services/api.ts` |
| Instructor UI | `frontend/src/pages/EventsPage.tsx` |
| Tests | backend unit/API tests plus frontend/Cypress flow coverage |

### Phase 1 acceptance criteria

1. An active eligible student can view and confirm an eligible scheduled future event through `/precheckin` using registration number and PIN.
2. Creation, cancellation, and re-confirmation are rejected by the backend from one hour before the event start onward.
3. No more than one active pre-checkin exists per student/event; repeated requests are idempotent and race-safe.
4. Only instructors/admins can see counts and student identities; public responses do not disclose other students or whether a registration/PIN combination was valid.
5. Cancelled, started, and finished events cannot receive pre-checkins; cancellation makes existing confirmations non-actionable.
6. A physical tablet/QR check-in for a confirmed student produces exactly one attendance and marks the pre-checkin converted; a no-show produces no attendance.
7. The Events page surfaces the confirmed count and instructor roster for eligible events; the existing event-cancellation action remains authoritative.

### Required decisions before Phase 1 build

- Confirm the event-state matrix above, including reschedule behavior (proposed: confirmations remain only if the new start remains outside the one-hour cutoff; otherwise invalidate and require reconfirmation).
- Confirm that active students are eligible regardless of belt/attendance eligibility, unless a class-specific eligibility rule already exists.
- Confirm public-endpoint controls: rate limit by client and registration attempt, generic invalid-credential errors, and no list access until successful credential validation.
- Confirm that `Event` is the canonical scheduled-class entity for pre-checkin.

## Phase 2 Implementation Plan — Exames Médicos + Document Foundation

### Requirements review

Structured review completed on 2026-07-19; full findings in [review-phase2.md](review-phase2.md). Two items required a decision before this plan could be written; both are now resolved (see "Required decisions" below). Also flagged and resolved: the existing `Exam`/`ExamParticipant`/`ExamBoardMember` tables model **belt-promotion** exams and must not be reused or extended for medical documents — Phase 2 introduces its own, unrelated model.

### Required decisions before Phase 2 build — resolved 2026-07-19

- **MED-05 actor (product decision, overrides prior policy):** student self-service upload **is** in scope, via a public registration-number+PIN endpoint, in addition to instructor/admin upload on the student's behalf. This reverses the Phase 1-era blanket "no student self-service" document-access note recorded below; that note now applies only to other future document types (e.g., contracts) unless separately revisited. `review-phase2.md` had recommended instructor/admin-only as the practical default — the user explicitly chose the broader option, so the public upload path must be built with the same rate-limiting and credential-privacy discipline as the Phase 1 public pre-checkin endpoints.
- **MED-04 scope (product decision):** Phase 2 only computes and exposes the medical-exam status (`valido` / `vencendo` / `vencido` / `sem_registro`) per student. No enrollment/reactivation action is blocked in this phase — there is no existing "matrícula renewal" entity or endpoint in the schema today (`Student` only has `is_active` plus create/update/deactivate). Blocking enforcement is deferred to Phase 3 (Financial foundation), which will define the renewal/billing action that consults this status.
- **MED-03 alert:** visual/dashboard status flag only, no email/push (consistent with epic Non-Goals; notifications are Epic 3 territory).
- **MED-01/02 data shape:** one structured field (exam date) plus one opaque attached document; no other medical fields modeled.
- **Document policy (carried over, Phase 1-era, 2026-07-19):** storage in OCI Object Storage reusing `dojo-infra/terraform/modules/storage/` (confirmed present in the repo); backend persists metadata and object key only, never file bytes; uploads limited to PDF/JPEG/PNG up to 10MB; soft delete with audit trail (actor, timestamp) on expiry, supersession, or student removal — no automatic hard delete.

### Intended design

- Add a generic `documents` table (reusable by Phase 4 Contracts later): owner (`student_id`), `document_type` (`medical_exam`, `contract`, ...), `storage_key`, `mime_type`, `size_bytes`, uploader (`uploaded_by_user_id` nullable, `uploaded_by_student_self` boolean), `status` (`active`/`superseded`/`deleted`), soft-delete audit fields (`deleted_at`, `deleted_by`).
- Add a domain `medical_exams` table: `student_id`, `exam_date`, `expires_at` (stored, computed as `exam_date + 365 days` at write time), `document_id` (nullable FK to `documents`), `status` (`active`/`superseded`). Append-only history: a new submission supersedes the previous active row rather than overwriting it, matching the retention policy. Exactly one `active` row per student is enforced at the service layer (transactional, same pattern used for `PreCheckIn` conversion in Phase 1), not a hard DB constraint, since history must be preserved.
- Status computation is a service-layer function, not a stored per-request value: `valido` if today is more than 30 days before `expires_at`; `vencendo` in the last 30 days before `expires_at`; `vencido` once past `expires_at`; `sem_registro` if the student has no active record.
- Public self-service upload mirrors the Phase 1 pre-checkin pattern exactly: registration number + PIN, IP + registration rate limiting, generic non-disclosing responses regardless of credential validity.

### Planned touch points

| Layer | Primary files/modules |
|---|---|
| ORM and migration | `dojo-app/backend/app/models/__init__.py` (new `Document`, `MedicalExam`), new Alembic revision on top of `b39e1a4c7d20` |
| API schemas | `dojo-app/backend/app/schemas/` (new `document.py` / `medical_exam.py`) |
| API routes | New `dojo-app/backend/app/api/medical_exams.py` (instructor/admin CRUD + status/dashboard) and a public router (registration+PIN upload), mirroring `pre_checkins.py` |
| Domain services | New `medical_exam_service.py` (status computation, supersession transaction, rate-limited public submission) |
| Storage integration | New thin client wrapping OCI Object Storage upload/delete, reusing `dojo-infra/terraform/modules/storage/` |
| Instructor UI | `dojo-app/frontend/src/pages/StudentsPage.tsx` (status badge, upload form, history), new dashboard "exames vencendo" list |
| Public UI | New `dojo-app/frontend/src/pages/MedicalExamPage.tsx`, reusing the public Axios client from `services/api.ts` |
| Tests | Backend unit/API tests for status computation, supersession, rate limiting, and public/instructor upload paths |

### Phase 2 acceptance criteria

1. Instructor/admin can record a medical exam (date + optional PDF/JPEG/PNG ≤10MB) for any student; a new record supersedes the prior one, preserving history.
2. A student can self-submit their medical exam (date + file) via a public endpoint authenticated by registration number + PIN, rate-limited by IP and registration number, with generic responses that don't disclose credential validity.
3. The system computes and exposes a per-student status (`valido` / `vencendo` / `vencido` / `sem_registro`) — visual/dashboard only, no email/push.
4. Instructors can see a dashboard list of students whose exam is `vencendo` or `vencido`.
5. Uploaded files are stored in OCI Object Storage; the database persists only metadata and the storage key; only PDF/JPEG/PNG up to 10MB are accepted.
6. Medical exam records form an append-only history per student with exactly one active record at a time; a superseded or soft-deleted record retains actor/timestamp audit metadata and is never hard-deleted automatically.
7. MED-04 (blocking matrícula renewal) is out of scope for Phase 2; item 3's status is the interface Phase 3 will consume once a renewal/billing action exists. No existing student action is blocked by this phase.
8. The new `documents`/`medical_exams` tables are unrelated to, and do not modify, the existing `exams`/`exam_participants`/`exam_board_members` (belt-promotion) tables.

## Later Phase Contracts

### Finance (Phase 3) — policy resolved 2026-07-19

Define plan/catalog ownership, billing cycle, due dates, pricing by weekly class frequency, partial/overpayment behavior, discounts, and overdue calculation. These policies become the source for both contracts and finance reports.

- **Pricing:** fixed plan catalog tiered by weekly class frequency (not a per-class dynamic rate).
- **Billing cycle:** monthly, single standardized due date for all students (e.g. day 5), proportional charge in the enrollment month.
- **Overdue:** flag-only in reports/dashboards; no automatic check-in or access block in this epic.
- **Partial/overpayment:** accepted; tracked as a residual balance (owed or credit) applied to the next charge.

### Contracts (Phase 4) — policy resolved 2026-07-19

Generate versioned PDFs at enrollment from the financial plan. Store both generated and signed copies with the shared document policy. Legal text/template approval is a product/legal input, not an implementation assumption.

- **Template versioning:** the legal template is versioned; each generated contract records the template version and the financial plan/version it used.
- **Signature capture:** dual path — on-screen/touch signature embedded into the generated PDF (tablet flow), or upload of an externally-signed PDF via the Phase 2 document policy. Operator chooses per contract.

### Reports (Phase 5) — policy resolved 2026-07-19

Supply parameterized PDF/CSV exports for belt exams, individual/class attendance, and finance. Define financial projections (time horizon and formula) before building REP-04.

- **REP-04 projection:** expected revenue over the next N months (default 3) = sum of currently active plans; no adjustment for historical delinquency/cancellation.

## Migration Strategy

- One backwards-compatible Alembic revision per phase, with explicit downgrade coverage.
- Phase 1 introduces `pre_checkins` with foreign keys to `events` and `students`, timestamps/status, and a uniqueness constraint appropriate to the chosen history model.
- Phase 2 introduces the generic `documents` table and the domain `medical_exams` table (append-only history, service-layer-enforced single active row); later phases reuse `documents` rather than adding independent file columns.
- Phase 3 owns financial plan/payment tables; Phase 4 references its approved plan/version; Phase 5 remains read-oriented.

## Verification Strategy

- Backend: unit tests for lifecycle/state transitions and service idempotency; API tests for authorization, cutoff, rate-limit behavior, and error privacy.
- Frontend: confirmation/cancellation UI tests and Cypress path for a public pre-check-in plus instructor roster.
- Migration: upgrade/downgrade verification against a representative existing database.
- Per phase: run repository-specific formatting/lint/test commands and record results in the phase test artifacts.

## Non-Goals

- Online payment processing and full accounting.
- Email/SMS/push reminders (Epic 3).
- Multi-organization configuration UI (Epic 4).
- QR check-in redesign beyond the integration needed for conversion.

## Next Action

Phase 1 (Pré-Checkin) shipped as `da5bd69`. Phase 2 (Exames Médicos + document foundation) decisions are resolved and the implementation plan above is ready; use `squad-feature` to build PR-2 against the acceptance criteria in "Phase 2 Implementation Plan".

## Phase 3 Implementation Plan — Financial Foundation

### Requirements review

Structured review completed 2026-07-20; full findings in [review-phase3.md](review-phase3.md). **APPROVED for tech-analyst**, with four items — D1, D3, D10, D11 — explicitly flagged as needing the user's sign-off before final schema commitment, even though each already has a sound, epic-consistent recommended default. This plan is designed against those defaults (per the review's own instruction: not blocking analysis, but tech-analyst must still route them back to the user rather than treat them as settled). D2, D4–D9 are treated as settled working defaults and are not re-gated here.

Ground-truth re-confirmed while designing (2026-07-20): `Student.classes_per_week`/`class_days` exist exactly as described and are staff-editable via `StudentsPage.tsx`; no `Plan`/`Payment`/`Invoice` table exists anywhere (greenfield); `MedicalExamService.compute_status`/`get_dashboard` compute status on read from an `active` record, the exact precedent this plan reuses for mensalidade status (D4) and for the overdue dashboard (D3); `Document`'s soft-delete/audit fields (`status`, `deleted_at`, `deleted_by`) are the exact precedent reused for voiding a payment. The existing belt-promotion `exams`/`exam_participants`/`exam_board_members` tables are unrelated to this phase's financial model and are not touched, extended, or referenced — Phase 3 introduces its own, fully independent tables, exactly as Phase 2 did for `documents`/`medical_exams`.

### Required decisions before Phase 3 build — resolved 2026-07-20

These four decisions were confirmed by explicit user sign-off on 2026-07-20. The design below proceeds against each as confirmed below.

- **D1 (frequency source):** `Student.classes_per_week` is the sole input to plan-tier lookup. FIN-06 is "read this field," not a new computation. No attendance-derived frequency metric is introduced.
- **D3 (medical-exam status in Phase 3):** Display-only on the overdue dashboard (reusing `MedicalExamService.get_status`); does not gate mensalidade generation, payment recording, or balance computation. This confirms and narrows the Phase 2 handoff's original language ("renewal/billing action that consults status") to clarify that status informs dashboards, not blocking logic, in this phase.
- **D10 (discounts/scholarships):** None modeled. The plan catalog is fixed-price only; no per-student override or discount field exists in the schema.
- **D11 (price-locking and annual renewal):** Each student's mensalidade locks to the `PlanVersion` active at assignment (the "grandfathered" design). Editing a tier's price creates a new `PlanVersion` and never reprices existing students. A student's price changes only via an explicit reassignment action — in practice, this occurs annually during contract renewal (Phase 4 responsibility). See the Phase 3 design breadcrumb below for how Phase 4 will integrate this pattern.

D2 (merge FIN-02/FIN-07 into one "price-for-tier" capability), D4 (computed-on-read status), D5 (no student self-service), D6 (daily pro-rata proration), D7 (FIFO payment allocation), D8 (no grace period), D9 (single global catalog) are adopted as-is per the requirements/review defaults and are reflected directly in the design below without a separate gate.

### Intended design

**Data model** — two new versioned-history pairs, following the `Document`/`MedicalExam` append-only-supersession precedent from Phase 2 rather than a stored state machine:

- `PlanTier` — stable identity for a weekly-frequency tier: `id`, `weekly_frequency` (`Integer`, unique), `name` (e.g. "2x por semana"), `is_active` (bool, for retiring a tier from future assignment without deleting history). Global/single catalog (D9), no organization scoping, consistent with the epic's multi-org non-goal.
- `PlanVersion` — the priced, versioned history of a tier: `id`, `plan_tier_id` FK, `price` (`Numeric(10, 2)` — this phase's first monetary column; no existing precedent in the schema, but the standard, correct type to avoid float rounding), `status` (`active`/`superseded`), `effective_from`, `created_by` (user). Editing a tier's price creates a new `active` `PlanVersion` and supersedes the previous one (service-layer-enforced exactly one active version per tier, same transactional pattern as `MedicalExamService.record_exam`'s supersession, not a DB constraint, since history must be kept). `PlanVersion.id` is the stable identifier Phase 4 records against a signed contract — resolves the "migration/backward-compatibility" requirement directly.
- `StudentPlan` — a student's assignment to a locked `PlanVersion`: `id`, `student_id` FK, `plan_version_id` FK, `status` (`active`/`superseded`), `started_at`, `ended_at` (nullable). Assigning or changing a student's plan creates a new `active` row and supersedes the prior one (same single-active-row service pattern); the price is locked at assignment time (D11) and is never silently repriced by a later catalog edit. This is also the natural place for Phase 5's REP-04 projection to read "this student's current price" without needing a mensalidade record to exist yet (closing the gap the review flagged in its §3.3) — expose it as a standalone query, not one coupled to billing-row existence.
- `Mensalidade` — one row per active student per billing month: `id`, `student_id` FK, `plan_version_id` FK (the price snapshot used — directly satisfies "each mensalidade records which plan/version it used"), `reference_month` (first-of-month date), `due_date`, `amount` (`Numeric(10, 2)`, computed and frozen at generation time, including any proration — never mutated afterward, per FIN-01's "no editing a mensalidade's historical amount" non-goal). `UniqueConstraint(student_id, reference_month)` makes monthly generation idempotent and race-safe, mirroring `Attendance`'s `uq_attendances_event_student` pattern. No stored status column (D4) — status is computed on read.
- `Payment` — `id`, `student_id` FK (not tied to a specific mensalidade by FK), `amount` (`Numeric(10, 2)`), `payment_date`, `method` (nullable string, informational only), `recorded_by` (user), `status` (`active`/`voided`), `voided_at`, `voided_by` — reusing `Document`'s soft-correction/audit pattern for the minor open item ("can a payment be corrected after entry") the requirements doc flagged as non-blocking.

**Why no allocation/ledger table:** per D7 and D4, a student's balance and each mensalidade's status are computed on read by walking that student's `active` mensalidades (ascending `due_date`) and `active` payments (ascending `payment_date`) and greedily applying payment amounts oldest-mensalidade-first (FIFO); any amount left over after all open mensalidades are covered is the student's credit, which the same walk applies to the next mensalidade once it exists — so credit never needs a separate stored balance field. This mirrors the Phase 2 "computed, not stored" precedent exactly and avoids a reconciliation table that could drift out of sync with payments.

**Status computation** (service-layer function, priority-ordered, same style as `MedicalExamService.compute_status`):
```
paid            if paid_amount >= mensalidade.amount
overdue         elif today > due_date                 (D8: no grace period)
partial         elif paid_amount > 0
open            otherwise
```

**Proration (D6 working formula, unresolved beyond this default):** `plan_price * (days_remaining_in_month_including_effective_day / total_days_in_month)`, rounded to the cent. Applied to (a) a student's first mensalidade in their enrollment month, and (b) a mid-cycle `StudentPlan` change, for the remainder of the month starting the day of change — but only if that month's mensalidade has not yet been generated; if it has, the new price takes effect starting the next generation cycle rather than mutating an already-generated row (keeps FIN-01's "no historical edits" non-goal intact). This nuance should be confirmed alongside D6 during build, not assumed silently.

**Generation trigger:** no scheduler/cron infrastructure exists anywhere in this codebase today, and adding one is out of scope for a billing-record-generation feature. `MensalidadeService.generate_monthly_charges(reference_month)` is an explicit, idempotent, instructor/admin-triggered action (safe to invoke repeatedly — the unique constraint skips students who already have a row for that month), not an automatic background job. It iterates `Student.is_active == True` only (mirrors `MedicalExamService.get_dashboard`'s active-student filter) — a deactivated student mid-cycle gets no new mensalidade, and existing unpaid ones are left as-is, per FIN-01's stated edge case.

**D11 annual-renewal breadcrumb for Phase 4:** The design locks each student's price to their assigned `PlanVersion` via `StudentPlanService.assign`, and changes it only via explicit reassignment. User sign-off confirmed (2026-07-20) that this matches the real business practice: price changes occur annually when students sign new contracts. Phase 4's (Contracts) implementation plan must account for this by having its contract-generation/renewal workflow trigger `StudentPlanService.assign` with the current year's active tier version — this is noted here as a forward-looking integration point, not a Phase 3 responsibility. The service API requires no Phase 3 changes to support this pattern.

**Plan-tier lookup gap (new edge case, not covered by the requirements doc):** if a student's `classes_per_week` has no matching `PlanTier`, plan assignment/generation must fail loudly (`HTTPException` naming the missing tier) rather than silently default to a price — the catalog must be kept complete for every `classes_per_week` value in active use. Flag this as an implementation note for build, not a new open decision.

**Service layer:**

- `PlanService` — CRUD `PlanTier`; `set_price(tier_id, price)` creates and activates a new `PlanVersion`, superseding the previous one.
- `StudentPlanService` — `assign(student_id, tier_id)` looks up the tier's current active `PlanVersion` and creates a new active `StudentPlan`, superseding any prior one; exposes `get_current_price(student_id)` as a standalone query (for Phase 5's REP-04, independent of mensalidade existence).
- `MensalidadeService` — `generate_monthly_charges(reference_month)`, proration calculation, `get_student_charges(student_id)`.
- `PaymentService` — `record_payment(student_id, amount, date, method, recorded_by)`, `void_payment(payment_id, voided_by)` (soft, audit-trailed, not a hard delete).
- `BalanceService` — `compute_status(mensalidade, student_payments)`, `get_balance(student_id)` (owed/credit), `get_overdue_dashboard()` — the FIN-05 list (student, amount owed, count of open/overdue mensalidades, days since oldest overdue due date), which also calls `MedicalExamService.get_status` per listed student and includes it as a display-only flag (D3), never a gate.

**API layer** (instructor/admin only throughout, via `get_current_instructor_or_admin`; per D5's default, and confirmed against the requirements doc — no FIN-0X item requests student self-service, so unlike Phase 2's medical-exam public endpoint, **Phase 3 adds no public endpoint**):

- `POST /api/v1/plans` / `GET /api/v1/plans` — create/list plan tiers (with each tier's current active price).
- `PUT /api/v1/plans/{tier_id}/price` — set a new price (creates a new `PlanVersion`).
- `POST /api/v1/students/{student_id}/plan` / `GET /api/v1/students/{student_id}/plan` — assign/reassign and view a student's plan history.
- `POST /api/v1/mensalidades/generate` — generate the month's charges (idempotent; body optionally names `reference_month`, defaults to current month).
- `GET /api/v1/students/{student_id}/mensalidades` — a student's charge history with computed status per row.
- `POST /api/v1/payments` — record a payment against a student.
- `POST /api/v1/payments/{payment_id}/void` — soft-void a mis-entered payment.
- `GET /api/v1/students/{student_id}/balance` — current owed/credit summary.
- `GET /api/v1/finance/overdue` — the FIN-05 inadimplentes dashboard list, including the D3 medical-exam status flag per row.

**Frontend:**

- New `PlansPage.tsx` (admin-only, mirrors `StudentsPage.tsx`'s form conventions) — plan tier catalog CRUD; editing a price shows an explicit confirmation that it creates a new version and does not reprice existing students (D11), consistent with the locked-pricing default.
- `StudentsPage.tsx` extension — a per-student "Financeiro" action (mirrors the existing `Stethoscope`/medical-exam modal pattern): current plan assignment, mensalidade history with computed status badges, a record-payment form, and the computed balance.
- `DashboardPage.tsx` extension — a new "Inadimplentes" table, structurally identical to the existing "Exames Médicos Vencendo/Vencidos" table, showing student, amount owed, days overdue, and the student's medical-exam status badge (reusing the existing `MedicalExamBadge` component) as the D3 flag-only column.

**FIN-07 alternate reading (deferred, not discarded):** if D1 is later overridden toward attendance-derived frequency, FIN-07's "actual attendance vs. declared tier" reconciliation becomes a distinct, separately-scoped feature (its own attendance-frequency-window service) — it is not part of this design and would need its own decision gate (window length, informational-only vs. tier-mismatch flag) before being added.

### Planned touch points

| Layer | Primary files/modules |
|---|---|
| ORM and migration | `dojo-app/backend/app/models/__init__.py` (new `PlanTier`, `PlanVersion`, `StudentPlan`, `Mensalidade`, `Payment`), new Alembic revision on top of `ea64c8751ff2` (current head) |
| API schemas | `dojo-app/backend/app/schemas/` (new `plan.py` / `mensalidade.py` / `payment.py`) |
| API routes | New `dojo-app/backend/app/api/plans.py`, `mensalidades.py`, `payments.py` (all instructor/admin only, no public router) |
| Domain services | New `plan_service.py`, `student_plan_service.py`, `mensalidade_service.py`, `payment_service.py`, `balance_service.py` |
| Instructor UI | New `dojo-app/frontend/src/pages/PlansPage.tsx`; extend `StudentsPage.tsx` (financial modal) and `DashboardPage.tsx` (inadimplentes list) |
| Tests | Backend unit tests for proration, FIFO allocation, status computation, idempotent generation; API tests for authorization and idempotency |

### Phase 3 acceptance criteria

1. Admin can define and version a plan catalog of weekly-frequency tiers with a price each (D9: single global catalog; D10: no discounts/overrides); each mensalidade records which `PlanVersion` it used.
2. A student is assigned a locked `PlanVersion` at enrollment/plan-change (D11 confirmed); editing a tier's price never repriced an already-assigned student.
3. `POST /api/v1/mensalidades/generate` idempotently creates one mensalidade per active student per reference month, with the amount computed from the student's assigned plan/version and prorated (D6 working formula) in the enrollment month or a mid-cycle plan-change month.
4. Instructor/admin can record a payment (date, amount) against a student and soft-void a mis-entered one; overpayment becomes credit applied via FIFO to the next open mensalidade (D7), underpayment leaves a residual balance.
5. The system computes, on read, whether each mensalidade is open/partial/paid/overdue (D4), with no stored status field, using the no-grace-period threshold (D8).
6. Instructor/admin can view a list of students with overdue mensalidades (amount owed, days overdue); each row also shows the student's current medical-exam status as a display-only flag (D3 confirmed) that gates nothing.
7. FIN-06's weekly-frequency value is `Student.classes_per_week` (D1 confirmed); no attendance-derived frequency metric exists in this phase.
8. No public/self-service financial endpoint exists (D5); no online payment processing, discount modeling (D10 confirmed), or email/SMS/push notifications are introduced (carried-over Non-Goals).
9. The new `PlanTier`/`PlanVersion`/`StudentPlan`/`Mensalidade`/`Payment` tables are unrelated to, and do not modify, the existing `exams`/`exam_participants`/`exam_board_members` (belt-promotion) tables.
