# Epic 2 Plan — Financeiro, Pré-Checkin e Relatórios

## Status

Planned with decision gates. The work is sequenced, but implementation must begin with Phase 1 only after the listed Phase 1 decisions are accepted.

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

## Later Phase Contracts

### Documents (Phase 2)

Define one reusable document abstraction before contracts: ownership, document type, storage key, MIME/size validation, access permissions, retention/deletion, and audit metadata. Medical expiry is one year; visual alert begins 30 days before expiry.

### Finance (Phase 3)

Define plan/catalog ownership, billing cycle, due dates, pricing by weekly class frequency, partial/overpayment behavior, discounts, and overdue calculation. These policies become the source for both contracts and finance reports.

### Contracts (Phase 4)

Generate versioned PDFs at enrollment from the financial plan. Store both generated and signed copies with the shared document policy. Legal text/template approval is a product/legal input, not an implementation assumption.

### Reports (Phase 5)

Supply parameterized PDF/CSV exports for belt exams, individual/class attendance, and finance. Define financial projections (time horizon and formula) before building REP-04.

## Migration Strategy

- One backwards-compatible Alembic revision per phase, with explicit downgrade coverage.
- Phase 1 introduces `pre_checkins` with foreign keys to `events` and `students`, timestamps/status, and a uniqueness constraint appropriate to the chosen history model.
- Phase 2 owns document-storage schema; later phases reuse it rather than adding independent file columns.
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

Accept or revise the four Phase 1 decisions, then use `squad-feature` to prepare the scoped Phase 1 implementation work.
