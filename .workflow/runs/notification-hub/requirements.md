# Requirements — Notification Hub (Student Opt-In, Delivery & History)

## Status

First pass. Scope was already decided directly with the user in the session that produced this document (see "Decision already locked in" below) — this document formalizes that decision into structured, testable acceptance criteria; it is not the output of a fresh requirements interview. Standalone, bounded feature — not part of any epic or either in-flight run (`recurring-event-series`, `contract-markdown-rendering`).

## Context

Ground truth confirmed directly against the codebase before this document was written:

- Students have no login/user account in this system — only a `pin` field on `Student` (`dojo-app/backend/app/models/__init__.py:150`), reused today by the existing public pre-check-in flow (`registration_number` + `pin`, see `PreCheckInPage.tsx` / `pre_checkin_service.py`).
- All three statuses this feature keys off of are **computed on read today, not stored**:
  - Pre-check-in: `PreCheckIn` rows exist per event/student (`dojo-app/backend/app/models/__init__.py:260`); `PRE_CHECKIN_CUTOFF = timedelta(hours=1)` (`dojo-app/backend/app/services/pre_checkin_service.py:14`) governs the existing *cutoff enforcement*, a different concept from the new reminder this feature adds.
  - Medical exam: `MedicalExam.expires_at` (`dojo-app/backend/app/models/__init__.py:324`); `EXPIRY_WARNING_WINDOW = timedelta(days=30)` (`dojo-app/backend/app/services/medical_exam_service.py:17`) is the existing lead time used to compute the admin dashboard's "expiring soon" status on every read.
  - Mensalidade: `Mensalidade.due_date` (`dojo-app/backend/app/models/__init__.py:414`); there is no stored status column — `BalanceService.compute_status` (`dojo-app/backend/app/services/balance_service.py:51`) derives `open`/`partial`/`overdue`/`paid` on every read from `due_date` and associated `Payment` rows.
- The existing admin-facing `DashboardPage.tsx` (`dojo-app/frontend/src/pages/DashboardPage.tsx`) already surfaces medical-exam-expiry and overdue-mensalidade widgets to admins, computed on demand. This feature does not touch, replace, or duplicate that page or its widgets.
- No email-sending infrastructure (SMTP, transactional email provider) exists anywhere in this backend today (confirmed by codebase search).
- No PWA manifest, service worker, or push-notification code exists anywhere in the frontend today (confirmed by codebase search) — both the PWA shell and Web Push are entirely new for this feature.

**The problem:** students (or their guardians, for `category="child"` students) have no way to be proactively reminded about upcoming events they haven't pre-checked into, an expiring medical exam, or an upcoming mensalidade due date — today they only find out reactively (e.g. turned away at check-in, or told by an admin) after the fact.

## Decision already locked in (do not re-litigate)

Agreed directly with the user in this session, not re-opened here:

1. **Feature name / shape**: "Notification Hub" — a new, standalone, public, student-facing page for opt-in and notification history. It does NOT touch, modify, or replace the existing admin-facing `DashboardPage.tsx`.
2. **Recipients**: the student only, for all three trigger types. No admin/staff recipient of any kind is introduced or changed by this feature.
3. **Channels (v1)**: (a) in-app notification history — a list with read/unread state, persisted in the backend, shown on the new opt-in page; (b) browser push notification via a PWA + Web Push, delivered even when the page is not open, contingent on the student having granted permission and (for full reliability) the PWA being installed/added to home screen. Email is explicitly out of scope for v1 (no email infra exists in this codebase today).
4. **Opt-in / identification mechanism**: reuse the existing `registration_number` + `pin` identification pattern already used by the public pre-check-in flow. No new login/account system, no explicit "guardian" data model or relationship — a guardian uses the exact same flow as the student, on their own device, using the student's `registration_number` + `pin`. Multiple devices/subscriptions per student are allowed and are not deduplicated by this feature (e.g. student's phone + guardian's phone both stay subscribed); a repeat opt-in on the same device does not need to replace or dedupe anything in particular.
5. **Trigger rules**: each of the three trigger types fires as a single, one-time notification per occurrence — no recurring/escalating reminders once fired, regardless of whether the underlying condition (e.g. still not pre-checked-in, exam still expired, mensalidade still unpaid) persists.
   - Pre-check-in reminder: 1 day before `Event.start_datetime`, only if the student has no `PreCheckIn` for that event yet.
   - Medical exam expiration reminder: 30 days before `MedicalExam.expires_at` (same lead time as the existing `EXPIRY_WARNING_WINDOW`, for consistency with what admins already see — not necessarily achieved by reusing that exact code).
   - Mensalidade due reminder: 7 days before `Mensalidade.due_date`.
6. **No backfill at launch**: only future crossings of these thresholds (from go-live onward) generate notifications. A student already past a threshold at launch time (already-expired exam, already-overdue mensalidade, already-past event) does not get a retroactive notification for that already-past occurrence.

This document resolves the remaining product-level specifics that decision leaves open: the opt-in page's exact behavior, notification content/state semantics, per-channel delivery expectations, and the trigger rules' edge cases (e.g. cancelled events, cancelled pre-check-ins, superseded exams, already-paid mensalidades).

## User Personas

**Student** (`category="adult"`) — wants to be reminded, without having to remember to check the app, when they're about to miss pre-check-in for a class, when their medical exam is about to expire, or when a mensalidade payment is coming due — so they can act before it becomes a problem (blocked at check-in, blocked from training, or a missed payment).

**Guardian of a child student** (`category="child"`) — plays the identical role as the student above, using the exact same public opt-in flow on their own device with the child's `registration_number` + PIN. No feature behavior differs by category; this persona is called out only because it is the actual primary user for `category="child"` students, not because the system special-cases it.

## Business Outcome

Students (or their guardians) proactively receive timely, one-time reminders for the three highest-friction "student forgot / didn't know" scenarios in the dojo's operations, reducing missed pre-check-ins, lapsed medical exam coverage, and late mensalidade payments — without requiring any new login system or admin-side work.

## In Scope

### NH-01 — Public opt-in page

A new public page (unauthenticated, reachable without an admin session) lets a student or guardian:

- Enter `registration_number` and `pin`.
- On successful match against an active `Student` record, be prompted to grant browser notification permission for a Web Push subscription.
- On the browser granting permission, the resulting push subscription is linked to that `student_id` in the backend.

**Given** a visitor on the opt-in page **when** they submit a `registration_number` + `pin` that matches an active student **then** they are prompted to grant notification permission, and if granted, a new push subscription record is created and linked to that student.

**Given** a visitor on the opt-in page **when** they submit a `registration_number` + `pin` that does not match any active student **then** they see a clear error message and no subscription is created.

**Given** a visitor on the opt-in page **when** they decline or dismiss the browser's notification-permission prompt **then** they see a clear message that push notifications are unavailable, but they may still access their in-app notification history (NH-08) using the same `registration_number` + `pin`.

### NH-02 — Multiple devices per student, no dedup requirement

A student may have more than one active push subscription (e.g. their own phone and a guardian's phone). Opting in again from a new device adds a new subscription rather than requiring removal of prior ones. Notifications are delivered to every active subscription linked to that student at the time of sending. Re-opting-in from the same device is not required to detect or replace a prior subscription from that same device — it is acceptable behavior (not a defect) if this results in more than one subscription record for the same physical device.

### NH-03 — Pre-check-in reminder trigger

Eligibility mirrors the existing rule enforced at pre-check-in time — no separate roster/registration concept is introduced. It combines the `is_active` check from `authenticate_student` (same file) with the belt-eligibility check from `PreCheckInService._validate_eligibility` (`dojo-app/backend/app/services/pre_checkin_service.py:46-51`): a student is eligible for a given event if the student is `is_active`, AND (the event has no `minimum_belt_id` set, OR the student's `current_belt.sort_order >= minimum_belt.sort_order`).

**This reminder fires for every `event_type_id`, with no exclusions** — including recurring "Aula Regular" occurrences generated by an `EventSeries` (one `Event` row per weekly occurrence). This is a deliberate, user-confirmed v1 trade-off: simplicity (no event-type filtering logic) over notification volume — an eligible student training, e.g., 3x/week can receive up to 3 pre-check-in reminders that week, one per distinct `Event` occurrence (NH-06's one-notification-per-occurrence guarantee still holds; this is a matter of frequency across many distinct occurrences, not a repeat for the same occurrence).

**Given** an `Event` with `start_datetime` exactly 1 day in the future **when** an eligible, active student (per the rule above) has no `PreCheckIn` record for that event **then** exactly one notification of type "pre-check-in reminder" is generated for that student referencing that event, regardless of the event's `event_type_id`.

**Given** a student whose `current_belt.sort_order` is below the event's `minimum_belt.sort_order` **when** the 1-day-before threshold is reached **then** no pre-check-in reminder is generated for that student/event, even if the student has no `PreCheckIn` record for it — the student is not eligible for the event in the first place.

**Given** a student who already has a `PreCheckIn` for that event (`status` of `confirmed` or `converted`) **when** the 1-day-before threshold is reached **then** no pre-check-in reminder is generated for that student/event.

**Given** an `Event` with `status` of `cancelled` **when** its 1-day-before threshold is reached **then** no pre-check-in reminder is generated for it.

**Given** a student whose only `PreCheckIn` for that event has `status="cancelled"` **when** the 1-day-before threshold is reached **then** the student is treated as not pre-checked-in and a reminder is generated (a cancelled pre-check-in is not equivalent to a confirmed one), provided the student is otherwise eligible per the rule above.

### NH-04 — Medical exam expiration reminder trigger

**Given** a student's `active`-status `MedicalExam` with `expires_at` exactly 30 days in the future **when** that threshold is reached **then** exactly one notification of type "medical exam expiring" is generated for that student.

**Given** a `MedicalExam` with `status="superseded"` **when** its `expires_at` would otherwise cross the 30-day threshold **then** no reminder is generated for it — only a student's current `active` exam is eligible.

**Given** a student with no `MedicalExam` on file at all **when** notifications are generated **then** no medical exam reminder is generated for that student (absence of an exam is a different, pre-existing problem this feature does not newly address).

### NH-05 — Mensalidade due reminder trigger

**Given** a `Mensalidade` with `due_date` exactly 7 days in the future **when** that threshold is reached **then** exactly one notification of type "mensalidade due" is generated for the student who owns it, regardless of whether it is already partially paid (a partial payment does not suppress the due-date reminder — only full payment does, per the next criterion).

**Given** a `Mensalidade` that is already fully paid (per the existing computed `paid` status) before its 7-day-before threshold is reached **then** no mensalidade due reminder is generated for it.

### NH-06 — One-time firing, no repeats

**Given** any of the three trigger conditions above has already generated a notification for a specific occurrence (a specific event, a specific medical exam record, or a specific mensalidade) **when** the underlying condition still holds on a later day (e.g. the student still hasn't pre-checked in, the exam is still unrenewed, the mensalidade is still unpaid) **then** no duplicate or follow-up notification is generated for that same occurrence — each occurrence produces at most one notification of its type, ever.

### NH-07 — No retroactive notifications at launch

**Given** the feature's go-live date **when** a student is already past a trigger threshold at that moment (e.g. an event less than 1 day away or already in the past with no pre-check-in, a medical exam already within 30 days of expiring or already expired, a mensalidade already within 7 days of its due date or already overdue) **then** no notification is generated retroactively for that already-past threshold — only thresholds crossed from go-live onward generate notifications.

### NH-08 — In-app notification history with read/unread state

**Given** a student or guardian who has previously completed the opt-in flow (NH-01) **when** they return to the page and re-enter their `registration_number` + `pin` **then** they see a list of all notifications generated for that student, each showing at minimum: the notification type (pre-check-in / medical exam / mensalidade), a human-readable message referencing the relevant event/exam/mensalidade, the date it was generated, and whether it has been read.

**Given** a student viewing their notification list **when** they open/view a previously-unread notification **then** it is marked as read, and this read state persists across sessions and devices (i.e. viewing it from one device marks it read for that student everywhere, not just on that device).

### NH-09 — Push delivery

**Given** a student with at least one active push subscription (NH-01/NH-02) **when** a notification is generated for them (NH-03/NH-04/NH-05) **then** a push notification is sent to every one of their active subscriptions, deliverable even if the student does not currently have the page open in a browser tab, subject to the browser/OS actually delivering it (delivery guarantees beyond the app's own send attempt are outside this feature's control).

**Given** a student with zero active push subscriptions (never opted in, or permission was revoked) **when** a notification is generated for them **then** it still appears in their in-app history (NH-08) once they visit the opt-in/history page and identify themselves — push delivery failure or absence never prevents the in-app record from existing.

### NH-10 — Notification content references the underlying record

Each notification's message content is specific enough for the student to know what to do next without needing to guess:

- Pre-check-in reminder: names the event (title) and its date/time, and communicates that pre-check-in is still needed.
- Medical exam reminder: communicates that their medical exam is expiring soon and its expiration date.
- Mensalidade reminder: names the reference month and due date, and communicates that payment is coming due.

## Explicit Non-Goals

- Email delivery of any kind — no SMTP/email-provider integration is introduced by this feature.
- Any change to the existing admin-facing `DashboardPage.tsx` or its medical-exam/mensalidade widgets — admins get nothing new from this feature.
- Any notification recipient other than the student (e.g. no admin/staff notification, no separate "notify the dojo" trigger).
- SMS, WhatsApp, Telegram, or any channel other than in-app history and Web Push.
- Repeating, escalating, or snoozed/re-sent reminders once a notification has fired for a given occurrence (NH-06) — even if the underlying problem is still unresolved.
- A full student login/account system (persistent sessions, password reset, etc.) — identification remains the existing `registration_number` + PIN, one-shot per visit, exactly as the pre-check-in flow works today.
- An explicit "guardian" data model, relationship, or role — a guardian is simply someone using the student's existing credentials on their own device; no new entity or permission concept is introduced.
- Any new trigger type beyond the three named here (e.g. no birthday reminders, no belt-exam reminders) — future trigger types are out of scope for this pass.
- Deduplicating push subscriptions per physical device (NH-02) — acceptable to accumulate more than one subscription per device across repeated opt-ins.
- An in-app "stop notifications" / unsubscribe control — students rely on revoking browser notification permission directly (device/browser settings) to stop push in v1; no in-product opt-out UI or endpoint is provided.

## Constraints

- The pre-check-in reminder (NH-03) applies to every `event_type_id` without exclusion, including recurring "Aula Regular" occurrences produced by an `EventSeries` — this is a deliberate, user-confirmed trade-off accepting higher notification frequency for a regularly-training student in exchange for v1 implementation simplicity (no event-type filtering rule to build or maintain).
- All three trigger conditions (pre-check-in completion, medical exam expiry, mensalidade due/paid status) are **computed on read today, not stored as flags or status columns** (see Context). Any process that detects "a threshold is crossed today" must perform equivalent date-arithmetic/status computation itself; it cannot simply query an existing status column that flips at the right moment. This is a real implementation constraint worth flagging to `tech-analyst`, not a technical design decision made here.
- No email-sending infrastructure exists in this codebase; this feature is not to add any store of email addresses/SMTP config to satisfy this feature — email is out of scope for v1 (see Non-Goals).
- No PWA manifest, service worker, or Web Push infrastructure exists in this codebase today — this feature introduces the first instance of all three. The exact push provider (e.g. Firebase Cloud Messaging) and PWA implementation approach are `tech-analyst` decisions, not specified further here.
- Identification continues to use the existing `registration_number` + `pin` fields already on `Student` — no new credential type, no password, no email verification step is introduced.
- Multiple push subscriptions per student are expected and must all receive deliveries (NH-02, NH-09) — a single-subscription-per-student assumption would be a functional gap, not just a nice-to-have.
- Per `CLAUDE.md`'s repository-wide testing mandate, every NH-0X criterion above must be covered by automated tests: Pytest unit/integration tests for the trigger-detection logic (all three trigger types, including their no-fire edge cases: cancelled events, cancelled pre-check-ins, superseded exams, fully-paid mensalidades, and the no-backfill-at-launch behavior of NH-07), the opt-in endpoint (valid/invalid `registration_number`+`pin`, multi-device subscription creation), the notification-history endpoint (read/unread state persistence across sessions), and the one-time-firing guarantee (NH-06); Jest unit/component tests for the opt-in page and notification history UI; Cypress end-to-end coverage for the full opt-in-then-view-history flow. Exact test file/case breakdown is left to `tech-analyst`'s implementation plan.

## Open Questions

None blocking product scope — the locked decisions above (including the push-unsubscribe decision reflected in Non-Goals) resolve every product question raised during review. The items below are intentionally left to `tech-analyst` because they are implementation choices, not product ambiguities:

- Exact Web Push provider/library (e.g. Firebase Cloud Messaging vs. raw Web Push protocol) and PWA manifest/service-worker implementation shape.
- Exact scheduling mechanism for detecting threshold crossings (e.g. a daily batch job) and its cadence/timezone handling.
- Exact API/route naming and payload shapes for the opt-in and notification-history endpoints.
- Whether/how push-subscription staleness (e.g. browser revokes a subscription silently) is detected and cleaned up — not specified as a product requirement here since it does not change student-visible behavior beyond NH-09's "best effort" framing.

If `tech-analyst` surfaces a genuine scope-changing ambiguity while designing against this document, route it back to the user at that point rather than treating any of the above as re-litigable without cause.

## Next Agent

Next Agent: requirements-reviewer
