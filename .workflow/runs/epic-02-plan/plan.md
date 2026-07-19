# Epic 2 Plan — Financeiro, Pré-Checkin e Relatórios

## Status

Phase 1 (Pré-Checkin) shipped as `da5bd69`. Phase 2 (Exames Médicos + document foundation) is planned and decision-gated to completion; ready for `squad-feature`. Phases 3–5 have their policy decisions resolved but no detailed implementation plan yet.

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
