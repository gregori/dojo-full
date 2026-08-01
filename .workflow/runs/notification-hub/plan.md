# Implementation Plan — Notification Hub (Student Opt-In, Delivery & History) (NH-01 – NH-10)

## Status

Design complete. Greenfield feature — no `Notification`/`PushSubscription` model, no scheduler, no PWA manifest/service worker, and no Web Push infra exist anywhere in this codebase today (confirmed independently by `product-manager`, `requirements-reviewer`, and re-confirmed directly below). Standalone, bounded feature; does not touch `DashboardPage.tsx` or any admin surface. House style follows `.workflow/runs/recurring-event-series/plan.md` (Requirements review / Autocrítica / Intended design / Migration plan / Test plan / File-level task breakdown / Risk assessment).

## Requirements review / ground truth re-confirmed

Re-verified directly against the current codebase before designing (all citations below were opened and read in full, not trusted from `requirements.md`/`review-requirements.md` alone):

- `Student` (`app/models/__init__.py:137-173`): `registration_number` (unique), `pin` (bcrypt hash), `is_active`, `current_belt_id` all confirmed exactly as `requirements.md` describes. No relationship to a notification/subscription concept exists yet.
- `PreCheckInService.authenticate_student` / `MedicalExamService.authenticate_student` (`pre_checkin_service.py:20-26`, `medical_exam_service.py:23-29`) are **byte-for-byte identical**: look up by `registration_number`, reject if not found, not `is_active`, or `verify_password(pin, student.pin)` fails. This exact 4-line idiom is the established "public credential check" pattern in this codebase and is reused (a third, deliberately duplicated copy — see Autocrítica) for this feature's `NotificationService.authenticate_student`.
- `PreCheckInService._validate_eligibility` (`pre_checkin_service.py:46-51`) confirmed: belt eligibility is `not event.minimum_belt_id or student.current_belt.sort_order >= minimum_belt.sort_order`. Combined with `authenticate_student`'s `is_active` check, this is NH-03's full eligibility rule, reused verbatim (not re-derived) in the new trigger-detection logic.
- `Event` (`app/models/__init__.py:208-238`): `start_datetime` (non-null, `DateTime(timezone=True)`), `status` enum incl. `"cancelled"`, `minimum_belt_id` (nullable FK) — all as requirements describe. `EventSeries`/`event_series_id`/`occurrence_date` (from the already-merged `recurring-event-series` feature) confirm "every `event_type_id`, no exclusions" is a real, already-shipped multi-occurrence-type set — NH-03 applies to `Event` rows uniformly regardless of series origin, no special-casing needed.
- `PreCheckIn` (`:260-279`): `status` enum is exactly `confirmed | cancelled | converted`, unique per `(event_id, student_id)`. A cancelled `PreCheckIn` is correctly excluded from "already checked in" per NH-03's fifth criterion.
- `MedicalExam` (`:311-331`): `expires_at` (non-null), `status` enum `active | superseded`. `MedicalExamService.EXPIRY_WARNING_WINDOW = timedelta(days=30)` (`:17`) and `compute_status` (`:39-50`) confirmed as a pure function of `expires_at` — reused conceptually (not by import, since the semantics needed here — "did the 30-day threshold get crossed today" — are a date-arithmetic question, not an "is it currently within 30 days" status question; see Autocrítica) rather than by calling `compute_status` directly.
- `Mensalidade` (`:397-418`): no stored status column, confirmed. `BalanceService.compute_status` (`balance_service.py:51-61`) and `get_student_charges_with_status` (`:64-82`) confirmed as the one authoritative, already-tested `open/partial/overdue/paid` computation (FIFO payment allocation) — **reused directly by function call**, not reimplemented, for NH-05's "already fully paid" exclusion. This directly satisfies the Constraints section's warning against a second, subtly different "is this paid" computation.
- `app/core/timezone.py` (already exists, added by `recurring-event-series`): `APP_TIMEZONE = ZoneInfo("America/Sao_Paulo")`, `local_now()`, `local_today()`. **Reused as-is, not reinvented** — this feature's own "which calendar day is a threshold crossed on" computation goes through the same, already-shipped, already-tested timezone module.
- `app/core/rate_limiter.py`: a simple in-memory `RateLimiter` class (5 attempts/60s per identifier), already instantiated per public flow (`precheckin_rate_limiter`, `medical_exam_rate_limiter`) and applied per-IP and per-`registration_number` in `pre_checkins.py`/`medical_exams.py`. Reused for the new public notification endpoints (a new `notification_rate_limiter` instance, same idiom).
- `pre_checkins.py`/`medical_exams.py`'s public write endpoints (`confirm`, `cancel`, `submit_medical_exam`) deliberately return a **generic, non-disclosing** `{"status": "accepted", "message": "..."}` regardless of credential validity, specifically to avoid a registration-number/PIN validity oracle. **NH-01's own acceptance criteria explicitly require the opposite** ("they see a clear error message") for this feature's endpoints — a real, deliberate divergence from this codebase's existing public-endpoint security convention, addressed head-on in Autocrítica below, not silently overridden either way.
- `app/services/event_series_service.py`'s `_get_or_create_occurrence` and `pre_checkin_service.py`'s `confirm` both use the identical idiom for exactly-once creation under concurrency: `db.add()` → `db.commit()` → on `IntegrityError`, `db.rollback()` and re-fetch. This is the exact mechanism reused for NH-06's "fires at most once per occurrence, ever" guarantee (see Autocrítica for why a DB unique constraint, not an in-application check, is load-bearing here).
- `docker-compose.yml` / `pyproject.toml` confirm MySQL 8.4 in dev/prod, SQLite in-memory for unit tests (`tests/unit/conftest.py`, `StaticPool`) — both engines already confirmed (by `recurring-event-series`'s own ground-truth pass) to treat `NULL` as distinct for composite unique indexes, a fact this design also relies on (see PushSubscription/Notification below).
- **No scheduler, broker, or cron infra exists in this backend** — confirmed by inspecting `pyproject.toml` (no `celery`, `apscheduler`, `redis`, `rq`) and `docker-compose.yml` (no broker service). At the time this design was first drafted, two parallel Kubernetes manifest sets existed in this repo (`k8s/` and `dojo-infra/k8s/`); that ambiguity has since been resolved and `k8s/` (along with its dead `deploy.yml` workflow) has been deleted from the repo entirely (commit `952c5f0`) — **`dojo-infra/k8s/` (applied via `kubectl apply -k` / Kustomize by `.github/workflows/deploy-k8s.yml`) is the one, confirmed-live manifest set** this feature targets. `dojo-infra/k8s/` currently has **no existing `CronJob` or `Job` resource of any kind** — this feature's `notification-check-cronjob.yaml` will be the first one added there, not a mirror of an existing sibling file in that directory (see Autocrítica for the now-deleted `k8s/` directory's historical role in identifying this idiom).
- `dojo-app/frontend/package.json`: no PWA/service-worker/push library of any kind (`vite-plugin-pwa`, `workbox`, `web-push` all absent). `qrcode.react` exists (added by a later, unrelated feature) but is irrelevant here. `index.html` has no `<link rel="manifest">`. Confirms the PWA shell and Web Push client code are both entirely new.
- `App.tsx` registers `/precheckin` and `/medical-exam` as flat, unauthenticated `<Route>` entries (no `PrivateRoute` wrapper) — the exact precedent this feature's new `/notifications` route follows.
- Alembic head is `6c95b3a8815d` (`add_event_series.py`) — confirmed by walking every `down_revision` chain in `alembic/versions/`; the new migration chains on top of it.

**Web Push library research (per the task's explicit instruction to verify current, non-deprecated practice rather than assume from training data):**

- The standard Web Push API (browser `PushManager`, VAPID authentication, service-worker `push` event) is confirmed current and non-deprecated — "Baseline: widely available" per MDN, no deprecation notices, no migration guidance toward an alternative. VAPID (RFC 8292) remains the standard authentication mechanism.
- `pywebpush` (Python) is confirmed current: latest release `2.3.0`, actively published, requires Python ≥3.10 (this backend runs 3.13), supports VAPID directly (`vapid_private_key`/`vapid_claims` kwargs), and defaults to the current `aes128gcm` (RFC 8188) encryption padding scheme — the older `aesgcm` scheme it also supports is explicitly marked deprecated in its own docs and is not used here. No functional replacement is needed.
- Firebase Cloud Messaging (FCM) was explicitly considered and rejected: it requires creating and managing a Google/Firebase project, a service-account credential, and a separate client SDK dependency purely to relay what the standard Web Push protocol already does natively and license-free for a browser-only PWA (this feature has no native mobile app to justify FCM's main advantage). Given "prefer simpler architectures" and no native-app requirement anywhere in `requirements.md`, standard Web Push + VAPID via `pywebpush` is the simpler, dependency-lighter, vendor-neutral choice.

## Autocrítica (self-review, performed before committing the design below)

- **Scheduling mechanism — the task's own hardest call.** Considered (a) an in-process APScheduler thread inside the FastAPI app, (b) a Kubernetes `CronJob` invoking a standalone script against the existing backend image, (c) introducing Celery + a broker. **Rejected (c) outright**: three simple daily/hourly date-arithmetic checks over a small dojo's data do not justify a new message-broker dependency (Redis/RabbitMQ) that this `docker-compose.yml` doesn't have and nothing else in this codebase needs — a clear case of the "don't introduce a broker for three simple checks" instruction. **Rejected (a):** this repo's actually-deployed backend runs more than one replica in at least one of its two live manifest sets (`dojo-infra/k8s/backend/deployment.yaml`: `replicas: 2`); an in-process scheduler would fire redundantly in every replica at the same instant, relying entirely on the DB-level idempotency guarantee to absorb the waste (harmless, but wasteful — every replica re-scans every event/exam/mensalidade every tick) and would add a background-thread lifecycle to the request-serving process for no benefit over the alternative. **Fixed:** a Kubernetes `CronJob` (option b), reusing the existing backend Docker image with an overridden command (`python -m app.jobs.notification_check`). `CronJob` and `Job` are standard, first-class Kubernetes resources fully supported by k3s (this app's actual deployment target, per `dojo-infra/k8s/`) — the technical feasibility of this approach does not depend on any in-repo precedent. `dojo-infra/k8s/` (the live manifest set) has no existing `CronJob`/`Job` example today, so this feature's manifest is the first of its kind there, not a mirror of an existing sibling file; the "same image, overridden command" idiom itself was originally identified from the now-deleted `k8s/mysql-backup-cronjob.yaml`/`k8s/backend-migration-job.yaml` (removed from the working tree in commit `952c5f0` as dead code — still visible in git history before that commit if a concrete reference example is useful during implementation, but no longer present to literally copy from). This adds **zero new runtime dependencies**, runs exactly once per scheduled tick regardless of how many backend replicas exist, and needs no new lifecycle code inside `app/main.py`.
  - **Cadence — reconsidered "once a day" for a robustness reason, not scope creep.** A literal once-a-day cron tick that happens to fail or be skipped (node maintenance, a transient DB outage at exactly that hour) would, under an exact-day-match trigger query, silently and permanently skip that day's crossings — a real correctness gap for NH-06/NH-09, not a hypothetical. Two fixes were considered: (i) widen the trigger query to a trailing multi-day lookback window, or (ii) keep the query strictly "today only" but run it more often. **(i) was rejected**: a lookback window risks violating NH-07 (no backfill at launch) on the very first run after go-live, since anything that crossed its threshold in the preceding N days — including before the feature was deployed — would then fire, exactly what NH-07 forbids; making it safe would require a separate "launch date" configuration value and comparison, a second moving part for no real gain. **(ii) is adopted instead**: the CronJob schedule is `"0 * * * *"` (hourly) rather than once daily. This is a **pure schedule-string change, zero code complexity added** — the trigger query itself is unchanged and still only ever asks "did X cross its threshold *today*" (satisfying NH-06/NH-07 exactly as literally specified), but now has 24 chances per day to run rather than 1, and `concurrencyPolicy: Forbid` plus the existing per-row idempotent-insert mechanism means running it more often is always safe, never produces a duplicate `Notification`, and never double-sends a push (see below). Documented explicitly so a future maintainer doesn't "simplify" this back to once-daily thinking it's mere frequency tuning — it is the concrete fix for a missed-run correctness gap.
  - **Two apparent Kubernetes manifest sets — resolved via execution history, not guessed.** `k8s/` and `dojo-infra/k8s/` are both present in the repo and both are referenced by GitHub Actions workflow files, but checking actual run history (`gh run list`) resolves which is live: `deploy.yml` (applies `k8s/`) triggers only on `push: branches: [main]`, and this repo's real default branch is `master` (`main` does not exist) — `gh run list --workflow=deploy.yml` shows **zero runs, ever**; `deploy-k8s.yml` (applies `dojo-infra/k8s/` via SSH + `k3s kubectl` against `master`) has a long, real run history, most recently three consecutive successful runs. **`dojo-infra/k8s/` is the live, actually-deployed manifest set; `k8s/` is dead/vestigial code, never applied in practice.** **Fixed:** the new CronJob manifest is added only to `dojo-infra/k8s/backend/notification-check-cronjob.yaml` (+ registered in `dojo-infra/k8s/kustomization.yaml`) — no hedged duplicate in `k8s/`, since adding a manifest to dead code would be pure waste, not risk mitigation.
- **Push library — Web Push/VAPID via `pywebpush` vs. Firebase Cloud Messaging.** Already justified above (ground-truth research); restated here because it was the task's explicit second hard call. No native mobile app exists or is planned per `requirements.md`'s explicit Non-Goals, removing FCM's main advantage over raw Web Push; `pywebpush` is actively published (2.3.0), needs no new external account/project, and both browsers this app needs to support already implement the standard Push API. **Fixed: standard Web Push + VAPID via `pywebpush`, not FCM.**
- **`Notification`'s reference to the underlying record — considered three nullable FK columns (`event_id`/`medical_exam_id`/`mensalidade_id`) with a `CheckConstraint` enforcing exactly one is set, matching this codebase's strong "always use a real FK" convention** (every other model here — `Document`, `Contract`, `MedicalExam`, `Payment` — uses explicit FKs, never a stringly-typed polymorphic reference). **Rejected in favor of a single non-FK `reference_id` column**, for a reason specific to this feature, not a general rejection of the convention: NH-10 requires each notification's `message` to be human-readable and fully specific (event title + datetime, exam expiry date, mensalidade month + due date) **at the moment it fires** — so the design freezes/snapshots the fully-rendered message string into the `Notification` row at creation time (the same "snapshot, don't recompute later" principle `recurring-event-series` applied to `Mensalidade.amount`/`Event.occurrence_date`). Because the frontend history view therefore never needs to join back to `Event`/`MedicalExam`/`Mensalidade` to render anything, the only remaining purpose of `reference_id` is as half of the idempotency key (`student_id` + `notification_type` + `reference_id`) — a genuine polymorphic FK's referential-integrity benefit (preventing an orphaned reference) buys nothing here that isn't already covered by the fact that trigger-detection code is the only writer of this column and always populates it from a real, just-queried row's `id`. Three nullable FKs plus a cross-column `CheckConstraint` would be real, working complexity spent on a guarantee this feature doesn't need. **Fixed:** one `reference_id: String(36)`, no FK, documented in the model's own docstring as deliberate.
- **`PushSubscription.endpoint` — considered a unique constraint** (a browser typically returns the same `endpoint` URL for a device's existing subscription, so uniqueness would provide "free" dedup). **Rejected**: NH-02 explicitly states re-opting-in from the same device accumulating more than one subscription row "is acceptable behavior (not a defect)," and enforcing uniqueness would require upsert-style conflict handling (catch-and-update-existing) that requirements never asked for and that isn't needed for any stated acceptance criterion. **Fixed:** no uniqueness constraint on `endpoint`; NH-02's explicit non-requirement is honored literally, not "improved on" unprompted.
- **NH-01's "clear error message" vs. this codebase's existing anti-enumeration convention (`pre_checkins.py`/`medical_exams.py`'s generic-accepted-response pattern) — a real, considered tension, not an oversight.** NH-01's own Given/When/Then text is unambiguous and was reviewed and approved without a Finding on this specific point: an invalid `registration_number`/`pin` combination must produce a distinguishable, clear error, not a generic "accepted" response. Implementing this literally does reintroduce a validity oracle this codebase's other two public flows deliberately avoid. **Resolved, not silently overridden either direction:** implement NH-01/NH-08 exactly as specified (a real 401 with a clear message on invalid credentials), mitigated the same way every other public, credential-bearing endpoint in this codebase already is — a per-IP **and** per-`registration_number` `RateLimiter` (the exact existing `RateLimiter` class, a new `notification_rate_limiter` instance) bounding brute-force attempts to 5/60s, identical to `precheckin_rate_limiter`/`medical_exam_rate_limiter`. This is the same mitigation strength already deemed acceptable elsewhere in this app for PIN-bearing public endpoints; it does not eliminate the oracle, but it is the established, already-reviewed bar for this codebase, applied consistently, not invented new for this feature.
- **`NotificationService.authenticate_student` — a third, near-identical copy of the same 4-line credential check** (`PreCheckInService`/`MedicalExamService` already each have one). Considered extracting a shared `authenticate_student_by_credentials(db, registration_number, pin)` helper into `student_service.py` to remove the now-three-way duplication. **Deferred, not done here:** the codebase already tolerates this exact duplication twice without refactoring (an established, if imperfect, precedent), and a shared-helper extraction touching two already-shipped, tested files is a refactor outside this feature's own scope and risk budget. Flagged as a candidate low-risk follow-up cleanup, not built as part of this plan.
- **Trigger-detection query shape — considered one giant cross-joined SQL query per trigger type vs. a bounded SQL date-range pre-filter followed by a Python loop for the belt-eligibility/payment-status logic that doesn't translate cleanly to SQL.** Rejected a single complex query: this codebase's own established idiom for "computed on read" business rules (`MedicalExamService.get_dashboard`, `BalanceService.get_overdue_dashboard`) is exactly "a narrow, indexed SQL filter, then a plain Python loop for anything conditional" — followed here for consistency, not reinvented as a single opaque query. **Fixed:** each trigger routine does one SQL query bounded to the single relevant calendar day (converted to a UTC range via `APP_TIMEZONE`, mirroring `local_today()`'s own logic), then a small Python loop applies the remaining eligibility/payment-status rule per candidate row — bounded, indexed, and consistent with existing style.
- **Checked NH-06's concurrency guarantee is real, not just "usually true."** The idempotency key is a genuine composite DB `UniqueConstraint("student_id", "notification_type", "reference_id")`, and `NotificationService.create_if_new` uses the exact `db.add()` → `db.commit()` → catch `IntegrityError` → `db.rollback()` → return `None` idiom already proven correct under concurrency by `recurring-event-series`'s own simulated-race unit tests (see Test plan) — not a "check-then-insert without a backstop" pattern, which would have a genuine TOCTOU race under the now-hourly cron cadence if two ticks ever overlapped (`concurrencyPolicy: Forbid` prevents that at the k8s level too, defense in depth, not the sole guarantee).
- **Checked push-send-on-duplicate is impossible by construction.** `PushService.send_to_student` is only ever called from a trigger routine immediately after `create_if_new` returns a non-`None` row — i.e., only by whichever concurrent attempt actually won the unique-constraint race. A losing/duplicate attempt (caught `IntegrityError`) never reaches the push-send call. This was checked explicitly because "exactly-once notification row" and "exactly-once push attempt" are two different guarantees that could silently diverge if wired incorrectly.
- **PWA scope — considered `vite-plugin-pwa`/Workbox for the manifest+service-worker generation.** Rejected: this app needs precisely two things — "installable" (a `manifest.json` linked from `index.html`) and "receives push while the tab is closed" (a service worker with just a `push` event listener) — neither requires offline caching, a build-time asset-precaching pipeline, or any new npm dependency at all. A hand-written, static `public/manifest.json` and `public/sw.js` (served as-is by Vite, no build step needed for either) is the simplest option that satisfies exactly what's asked, per the task's explicit "keep this minimal" instruction and CLAUDE.md's anti-overengineering rule.
- **Checked testability of every new piece:** every `NotificationTriggerService`/`NotificationService`/`PushService` method takes/returns plain models, dicts, or primitives, is callable directly from a unit test without HTTP or the CronJob wrapper, and `PushService.send_to_student` is the single seam a test mocks/monkeypatches to assert push was attempted without a real network call — matching this codebase's existing service-layer testing discipline exactly (no new abstraction layer introduced).

## Intended design — data model

### `Notification` model (new, in `app/models/__init__.py`)

```python
class Notification(UUIDMixin, TimestampMixin, Base):
    """A one-time, student-facing reminder for a single event/exam/mensalidade occurrence.

    ``message`` is fully rendered and frozen at creation time (NH-10) -- the
    history view never joins back to Event/MedicalExam/Mensalidade to display
    it. ``reference_id`` is the underlying record's id, deliberately not a FK
    (see plan.md Autocritica): it exists only as half of the idempotency key
    below, never dereferenced/joined at read time.

    The three-way UniqueConstraint set is this feature's concrete mechanism
    for NH-06 ("fires at most once per occurrence, ever"): student_id +
    notification_type + reference_id together identify one specific
    occurrence for one specific student, exactly once, enforced by the
    database, not just application logic (mirrors EventSeries' own
    UNIQUE(event_series_id, occurrence_date) idiom).
    """

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "notification_type", "reference_id", name="uq_notifications_student_type_reference"
        ),
    )

    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    notification_type: Mapped[str] = mapped_column(
        Enum("pre_checkin_reminder", "medical_exam_expiring", "mensalidade_due", name="notification_type"),
        nullable=False,
    )
    reference_id: Mapped[str] = mapped_column(String(36), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    student: Mapped["Student"] = relationship(back_populates="notifications")
```

### `PushSubscription` model (new, in `app/models/__init__.py`)

```python
class PushSubscription(UUIDMixin, TimestampMixin, Base):
    """One browser's Web Push subscription, linked to a student (NH-01/NH-02).

    No uniqueness constraint on ``endpoint`` -- NH-02 explicitly allows more
    than one subscription row per physical device (see plan.md Autocritica).
    Multiple rows per student are expected and all receive deliveries (NH-09).
    """

    __tablename__ = "push_subscriptions"

    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    p256dh_key: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_key: Mapped[str] = mapped_column(String(255), nullable=False)

    student: Mapped["Student"] = relationship(back_populates="push_subscriptions")
```

### `Student` model additions (in `app/models/__init__.py`, additive)

```python
notifications: Mapped[list["Notification"]] = relationship(back_populates="student")
push_subscriptions: Mapped[list["PushSubscription"]] = relationship(back_populates="student")
```

### `app/core/config.py` additions (VAPID settings)

```python
vapid_private_key: str = ""
vapid_public_key: str = ""
vapid_subject: str = "mailto:admin@example.com"
```

Generated once via `pywebpush`'s bundled `py_vapid` CLI (`vapid --gen`) as a one-time deployment step; keys stored in the existing `backend-secret`/`dojo-secrets` Kubernetes Secret objects (`vapid_private_key`) and `backend-config` ConfigMap (`vapid_public_key`, non-sensitive by design — VAPID public keys are meant to be exposed to the browser).

## Intended design — services

### `app/services/notification_service.py` (new)

CRUD/query layer used by both the public API and the trigger-detection job:

```python
"""Identify students, create idempotent notifications, and serve/read history."""

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models import Notification, PushSubscription, Student
from app.services.student_service import StudentService


class NotificationService:
    @staticmethod
    def authenticate_student(db: Session, registration_number: str, pin: str) -> Student | None:
        """Return the active student for valid public credentials, otherwise ``None``.

        Identical idiom to PreCheckInService/MedicalExamService's own
        authenticate_student (a third, deliberate copy -- see plan.md Autocritica).
        """
        student = StudentService.get_student_by_registration(db, registration_number)
        if not student or not student.is_active or not verify_password(pin, student.pin):
            return None
        return student

    @staticmethod
    def create_if_new(
        db: Session, student_id: str, notification_type: str, reference_id: str, message: str
    ) -> Notification | None:
        """Insert a Notification, or return None if this occurrence already fired (NH-06)."""
        notification = Notification(
            student_id=student_id, notification_type=notification_type, reference_id=reference_id, message=message
        )
        db.add(notification)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return None
        db.refresh(notification)
        return notification

    @staticmethod
    def add_subscription(db: Session, student_id: str, endpoint: str, p256dh: str, auth: str) -> PushSubscription:
        subscription = PushSubscription(student_id=student_id, endpoint=endpoint, p256dh_key=p256dh, auth_key=auth)
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        return subscription

    @staticmethod
    def get_history(db: Session, student_id: str) -> list[Notification]:
        return (
            db.query(Notification)
            .filter(Notification.student_id == student_id)
            .order_by(Notification.created_at.desc())
            .all()
        )

    @staticmethod
    def mark_read(db: Session, notification_id: str, student_id: str) -> Notification | None:
        """Mark read, scoped to the authenticated student_id (NH-08 cross-device persistence).

        Scoping by student_id (not just notification_id) prevents one student's
        credentials from marking another student's notification read -- a real
        authorization boundary given there is no session/login (mirrors how
        PreCheckInService.cancel always scopes by the authenticated student).
        """
        notification = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.student_id == student_id)
            .first()
        )
        if not notification:
            return None
        if notification.read_at is None:
            notification.read_at = datetime.now(UTC)
            db.commit()
            db.refresh(notification)
        return notification
```

### `app/services/push_service.py` (new)

```python
"""Best-effort Web Push delivery via VAPID (RFC 8292), using pywebpush."""

import json
import logging

from pywebpush import WebPushException, webpush
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import PushSubscription, Student

logger = logging.getLogger(__name__)


class PushService:
    @staticmethod
    def send_to_student(db: Session, student: Student, title: str, body: str) -> None:
        """Send one push message to every active subscription for a student (NH-09).

        Best-effort: a failed/stale subscription is logged and skipped, never
        raised -- push delivery failure never blocks the in-app Notification
        row (already committed by the caller before this runs) from existing.
        Subscription-staleness cleanup is an explicit Open Question, not a v1
        requirement (requirements.md), and is deliberately not implemented here.
        """
        settings = get_settings()
        subscriptions = db.query(PushSubscription).filter(PushSubscription.student_id == student.id).all()
        payload = json.dumps({"title": title, "body": body})
        for subscription in subscriptions:
            try:
                webpush(
                    subscription_info={
                        "endpoint": subscription.endpoint,
                        "keys": {"p256dh": subscription.p256dh_key, "auth": subscription.auth_key},
                    },
                    data=payload,
                    vapid_private_key=settings.vapid_private_key,
                    vapid_claims={"sub": settings.vapid_subject},
                )
            except WebPushException:
                logger.warning("Push delivery failed for subscription %s", subscription.id, exc_info=True)
```

### `app/services/notification_trigger_service.py` (new) — the date-arithmetic trigger detection (NH-03/04/05/06/07)

```python
"""Daily/hourly threshold-crossing detection for the three notification types.

All three statuses this feature keys off of are computed on read, not stored
(requirements.md Constraints) -- each routine below performs its own
date-arithmetic against the exact calendar day a threshold is crossed, using
the same app-wide America/Sao_Paulo timezone module recurring-event-series
already introduced (app.core.timezone), not a bare datetime.now(UTC).

Each routine narrows its own SQL query to the single relevant calendar day
(mirroring MedicalExamService.get_dashboard/BalanceService.get_overdue_dashboard's
existing "narrow SQL filter, then a Python loop for anything conditional" style),
then applies NH-06's idempotent create-or-skip via NotificationService.create_if_new,
sending a push only for the row that actually just fired (see plan.md Autocritica).
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.core.timezone import APP_TIMEZONE, local_today
from app.models import Event, MedicalExam, Mensalidade, PreCheckIn, Student
from app.services.balance_service import BalanceService
from app.services.notification_service import NotificationService
from app.services.push_service import PushService

PRE_CHECKIN_LEAD = timedelta(days=1)
MEDICAL_EXAM_LEAD = timedelta(days=30)
MENSALIDADE_LEAD = timedelta(days=7)


def _day_bounds_utc(local_date: date) -> tuple[datetime, datetime]:
    """UTC instant range spanning one full America/Sao_Paulo calendar day."""
    start = datetime.combine(local_date, time.min, tzinfo=APP_TIMEZONE)
    end = datetime.combine(local_date, time.max, tzinfo=APP_TIMEZONE)
    return start, end


class NotificationTriggerService:
    @staticmethod
    def check_pre_checkin_reminders(db: Session) -> int:
        """NH-03: events starting exactly PRE_CHECKIN_LEAD from today, no exclusions by event_type_id."""
        target_date = local_today() + PRE_CHECKIN_LEAD
        start, end = _day_bounds_utc(target_date)
        events = (
            db.query(Event)
            .filter(Event.status != "cancelled", Event.start_datetime.between(start, end))
            .all()
        )
        active_students = db.query(Student).filter(Student.is_active.is_(True)).all()
        fired = 0
        for event in events:
            checked_in_ids = {
                pc.student_id
                for pc in db.query(PreCheckIn).filter(
                    PreCheckIn.event_id == event.id, PreCheckIn.status.in_(("confirmed", "converted"))
                )
            }
            for student in active_students:
                if student.id in checked_in_ids:
                    continue
                if event.minimum_belt_id and (
                    not student.current_belt or student.current_belt.sort_order < event.minimum_belt.sort_order
                ):
                    continue
                message = (
                    f'Falta pouco! Faça seu pré-check-in para "{event.title}" '
                    f"em {event.start_datetime.astimezone(APP_TIMEZONE):%d/%m/%Y %H:%M}."
                )
                notification = NotificationService.create_if_new(
                    db, student.id, "pre_checkin_reminder", event.id, message
                )
                if notification:
                    PushService.send_to_student(db, student, "Pré-check-in pendente", message)
                    fired += 1
        return fired

    @staticmethod
    def check_medical_exam_reminders(db: Session) -> int:
        """NH-04: active exams expiring exactly MEDICAL_EXAM_LEAD from today."""
        target_date = local_today() + MEDICAL_EXAM_LEAD
        start, end = _day_bounds_utc(target_date)
        exams = (
            db.query(MedicalExam)
            .filter(MedicalExam.status == "active", MedicalExam.expires_at.between(start, end))
            .all()
        )
        fired = 0
        for exam in exams:
            message = (
                f"Seu exame médico vence em {exam.expires_at.astimezone(APP_TIMEZONE):%d/%m/%Y}. "
                "Providencie a renovação."
            )
            notification = NotificationService.create_if_new(
                db, exam.student_id, "medical_exam_expiring", exam.id, message
            )
            if notification:
                PushService.send_to_student(db, exam.student, "Exame médico vencendo", message)
                fired += 1
        return fired

    @staticmethod
    def check_mensalidade_reminders(db: Session) -> int:
        """NH-05: mensalidades due exactly MENSALIDADE_LEAD from today, unless already fully paid.

        Reuses BalanceService.get_student_charges_with_status (the one
        authoritative paid/overdue/partial/open computation) rather than
        reimplementing "is this paid" -- directly addresses the Constraints
        section's warning against a second, subtly different computation.
        """
        target_date = local_today() + MENSALIDADE_LEAD
        start, end = _day_bounds_utc(target_date)
        mensalidades = db.query(Mensalidade).filter(Mensalidade.due_date.between(start, end)).all()
        fired = 0
        for mensalidade in mensalidades:
            charges = BalanceService.get_student_charges_with_status(db, mensalidade.student_id)
            charge = next((c for c in charges if c["id"] == mensalidade.id), None)
            if not charge or charge["status"] == "paid":
                continue
            message = (
                f"Sua mensalidade de {mensalidade.reference_month.astimezone(APP_TIMEZONE):%m/%Y} "
                f"vence em {mensalidade.due_date.astimezone(APP_TIMEZONE):%d/%m/%Y}."
            )
            notification = NotificationService.create_if_new(
                db, mensalidade.student_id, "mensalidade_due", mensalidade.id, message
            )
            if notification:
                PushService.send_to_student(db, mensalidade.student, "Mensalidade a vencer", message)
                fired += 1
        return fired
```

### `app/jobs/notification_check.py` (new package `app/jobs/`) — the CronJob entrypoint

```python
"""Standalone entrypoint for the notification-trigger check.

Invoked by a Kubernetes CronJob (dojo-infra/k8s/backend/notification-check-cronjob.yaml,
the confirmed-live manifest set -- see plan.md Autocritica), not by the FastAPI
app -- this codebase has no in-process scheduler and none is introduced for
this feature.
"""

import logging

from app.core.database import SessionLocal
from app.services.notification_trigger_service import NotificationTriggerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    db = SessionLocal()
    try:
        pre_checkin_count = NotificationTriggerService.check_pre_checkin_reminders(db)
        medical_exam_count = NotificationTriggerService.check_medical_exam_reminders(db)
        mensalidade_count = NotificationTriggerService.check_mensalidade_reminders(db)
        logger.info(
            "Notification check complete: pre_checkin=%d medical_exam=%d mensalidade=%d",
            pre_checkin_count,
            medical_exam_count,
            mensalidade_count,
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

Run via `python -m app.jobs.notification_check` (same interpreter/venv as the backend image — no new entrypoint script needed beyond this module).

## Intended design — API

### `app/schemas/notification.py` (new)

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StudentCredentials(BaseModel):
    registration_number: str
    pin: str


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscribeRequest(StudentCredentials):
    endpoint: str
    keys: PushSubscriptionKeys


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    notification_type: str
    message: str
    created_at: datetime
    read_at: datetime | None


class VapidPublicKeyResponse(BaseModel):
    public_key: str
```

### `app/api/notifications.py` (new), registered in `app/main.py`

Mirrors `pre_checkins.py`/`medical_exams.py`'s public-route conventions (rate-limited by IP + `registration_number`), but returns a **distinguishable 401 on invalid credentials**, per NH-01/NH-08's explicit acceptance criteria — a deliberate divergence from the generic-accepted-response idiom used by those two files (see Autocrítica):

```python
"""Public endpoints for the Notification Hub: opt-in, subscription, and history."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limiter import RateLimiter
from app.schemas import NotificationResponse, PushSubscribeRequest, StudentCredentials, VapidPublicKeyResponse
from app.services import NotificationService

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])
notification_rate_limiter = RateLimiter()
INVALID_CREDENTIALS = "Matrícula ou PIN inválidos."


def _rate_limit(request: Request, registration_number: str) -> None:
    client_ip = request.client.host if request.client else "unknown"
    notification_rate_limiter.check_rate_limit(f"ip:{client_ip}")
    notification_rate_limiter.check_rate_limit(f"registration:{registration_number}")


def _authenticate_or_401(db: Session, data: StudentCredentials, request: Request):
    _rate_limit(request, data.registration_number)
    student = NotificationService.authenticate_student(db, data.registration_number, data.pin)
    if not student:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_CREDENTIALS)
    return student


@router.get("/vapid-public-key", response_model=VapidPublicKeyResponse)
def get_vapid_public_key():
    """Public by design -- a VAPID public key is meant to be exposed to the browser."""
    return VapidPublicKeyResponse(public_key=get_settings().vapid_public_key)


@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
def subscribe(data: PushSubscribeRequest, request: Request, db: Session = Depends(get_db)):
    """Link a browser push subscription to a student (NH-01/NH-02)."""
    student = _authenticate_or_401(db, data, request)
    NotificationService.add_subscription(db, student.id, data.endpoint, data.keys.p256dh, data.keys.auth)
    return {"status": "subscribed"}


@router.post("/history", response_model=list[NotificationResponse])
def get_history(data: StudentCredentials, request: Request, db: Session = Depends(get_db)):
    """Return a student's full notification history (NH-08)."""
    student = _authenticate_or_401(db, data, request)
    return NotificationService.get_history(db, student.id)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: str, data: StudentCredentials, request: Request, db: Session = Depends(get_db)
):
    """Mark one notification read, persisted across sessions/devices (NH-08)."""
    student = _authenticate_or_401(db, data, request)
    notification = NotificationService.mark_read(db, notification_id, student.id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notification
```

`app/main.py` gains one import + `app.include_router(notifications.router)`. `app/schemas/__init__.py` gains the four new schema imports. `app/services/__init__.py` gains `NotificationService`, `PushService`, `NotificationTriggerService`.

## Intended design — frontend

- **New, wholly public page:** `dojo-app/frontend/src/pages/NotificationHubPage.tsx`, structurally mirroring `PreCheckInPage.tsx` (same dark-card layout, same `registration_number`/`pin` form pattern, same `publicApi` client — never the authenticated `api` client, since there is no login here).
  - Form: `registration_number` + `pin` → on submit, `publicApi.post('/api/v1/notifications/history', {...})`.
    - 200: store credentials in component state only (never `localStorage` — one-shot per visit, exactly like `PreCheckInPage.tsx`'s own `pin` handling), render the returned list (type label, message, formatted `created_at`, unread/read badge), and reveal an "Ativar notificações" (enable push) call-to-action.
    - 401: show the returned `detail` ("Matrícula ou PIN inválidos.") in the existing red-error card pattern (`feedback.kind === 'error'`).
  - Clicking an unread item calls `publicApi.post(`/api/v1/notifications/${id}/read`, credentials)`, then updates that item's local state to read (NH-08).
  - "Ativar notificações" button (only rendered if `'serviceWorker' in navigator && 'PushManager' in window`):
    1. `navigator.serviceWorker.register('/sw.js')`.
    2. `Notification.requestPermission()`.
    3. Granted → `publicApi.get('/api/v1/notifications/vapid-public-key')`, convert the base64 public key to a `Uint8Array` (the standard, widely-used `urlBase64ToUint8Array` snippet — no new npm dependency), `registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey })`, then `publicApi.post('/api/v1/notifications/subscribe', { ...credentials, ...subscription.toJSON() })`.
    4. Denied/dismissed → show "Notificações push indisponíveis neste dispositivo, mas você pode continuar acompanhando seu histórico aqui." (NH-01's third Given/When/Then) — history stays visible regardless, no re-authentication needed since it's already loaded.
- **`App.tsx`** — add `<Route path="/notifications" element={<NotificationHubPage />} />` as a flat, unauthenticated route (same level as `/precheckin`, `/medical-exam` — not wrapped in `PrivateRoute`/`AdminRoute`). No `Layout.tsx` change — this page has no admin nav entry, per the Non-Goals ("no admin UI").
- **PWA shell, hand-written, no new npm dependency (`vite-plugin-pwa`/Workbox rejected — see Autocrítica):**
  - `dojo-app/frontend/public/manifest.json` (new): minimal — `name`, `short_name`, `start_url: "/notifications"`, `display: "standalone"`, `background_color`/`theme_color`, and an `icons` array (implementer adds at least a 192×192 and 512×512 PNG under `public/`; the existing `vite.svg` alone is not sufficient for most browsers' installability checks — flagged as a small implementer task, not a design gap).
  - `dojo-app/frontend/index.html` — add `<link rel="manifest" href="/manifest.json" />` and a `<meta name="theme-color" content="..." />`.
  - `dojo-app/frontend/public/sw.js` (new, static, not built by Vite): a minimal service worker — a `push` listener calling `self.registration.showNotification(data.title, { body: data.body })`, and a `notificationclick` listener that focuses/opens `/notifications`. No caching/offline strategy (explicitly out of scope — "just enough for push delivery + add to home screen").
- **Requires HTTPS** (a secure context) for `pushManager.subscribe` — already satisfied by this app's existing ingress + `cert-manager-issuer.yaml` TLS setup; no new infra needed for this, just confirmed as a real, already-met precondition, not assumed.

## Migration plan

One new Alembic revision, generated via `alembic revision -m "add_notification_hub"` (chained on the current head `6c95b3a8815d`, not a hand-picked ID, per this project's existing convention):

**Upgrade:**
1. `op.create_table("notifications", ...)` — `id` PK, `student_id` FK to `students`, `notification_type` enum, `reference_id String(36) not null` (no FK, by design), `message Text not null`, `read_at DateTime(timezone=True) nullable`, `created_at`/`updated_at`.
2. `op.create_unique_constraint("uq_notifications_student_type_reference", "notifications", ["student_id", "notification_type", "reference_id"])`.
3. `op.create_table("push_subscriptions", ...)` — `id` PK, `student_id` FK to `students`, `endpoint String(500) not null`, `p256dh_key String(255) not null`, `auth_key String(255) not null`, `created_at`/`updated_at`. No unique index on `endpoint` (by design).

**Downgrade:**
1. `op.drop_table("push_subscriptions")`
2. `op.drop_constraint("uq_notifications_student_type_reference", "notifications", type_="unique")`
3. `op.drop_table("notifications")`

No data migration needed — both tables start empty; no existing table is altered.

## Test plan

Per `CLAUDE.md`'s layered mandate and `requirements.md`'s Constraints section's explicit coverage list.

### Pytest unit — `tests/unit/test_notification_trigger_service.py` (new); extend `tests/unit/conftest.py` with `make_notification`/`make_push_subscription` factories

- **NH-03 (all five Given/When/Then branches):** fires exactly once for an eligible active student with no `PreCheckIn`, for an event exactly 1 day out, regardless of `event_type_id`; does not fire for a belt-ineligible student; does not fire when the student's only `PreCheckIn` is `confirmed`/`converted`; does not fire for a `cancelled` event; **does** fire when the student's only `PreCheckIn` is `cancelled` (treated as not-checked-in).
- **NH-04 (three branches):** fires for an `active` exam expiring in exactly 30 days; does not fire for a `superseded` exam; does not fire for a student with no exam on file at all.
- **NH-05 (two branches):** fires for a `Mensalidade` due in exactly 7 days regardless of partial payment; does not fire once `BalanceService.compute_status` reports `"paid"` before the threshold.
- **NH-06 (idempotency, the required concurrency test per `requirements.md`):** calling the same `check_*` routine twice in a row for the same data produces exactly one `Notification` row the second time raises no exception and returns `fired=0`; a simulated two-writer race on `NotificationService.create_if_new` (second independent `Session` commits a competing row between the first session's existing-row-implicit-check and its own `db.commit()`) — assert no exception propagates, exactly one row exists afterward. Mirrors `recurring-event-series`'s own simulated-race test pattern for `_get_or_create_occurrence`.
- **NH-07 (no backfill):** an event/exam/mensalidade whose threshold day is in the past relative to "today" (simulated via `freezegun`, already a dev dependency) never fires, even on the very first-ever call of the routine — proving the exact-day-match query itself, not a launch-date flag, is what prevents backfill.
- **Push-attempted-only-on-actual-fire:** `PushService.send_to_student` (monkeypatched/mocked) is called exactly once per newly created `Notification`, and is **not** called when `create_if_new` returns `None` (the duplicate/losing-race path) — the explicit "push send is impossible on a duplicate" check from Autocrítica, asserted directly.
- **Timezone boundary:** freeze a UTC instant that is a different calendar date in `America/Sao_Paulo` (mirroring `recurring-event-series`'s own such test) and assert all three routines' target-date computation uses the São Paulo date, not the UTC date.

### Pytest unit — `tests/unit/test_notification_service.py` (new)

- `authenticate_student`: valid credentials return the student; wrong PIN, unknown `registration_number`, and inactive student all return `None`.
- `create_if_new`: first call creates and returns a row; a second call with identical `(student_id, notification_type, reference_id)` returns `None` and leaves exactly one row.
- `add_subscription`: creates a `PushSubscription`; calling it twice for the same `(student_id, endpoint)` creates two rows (no dedup, per NH-02 — asserted as intended, not a bug).
- `get_history`: returns all notifications for a student, most recent first; excludes another student's notifications.
- `mark_read`: sets `read_at` on first call; a second call is a no-op (does not change an already-set `read_at`); scoped so a different `student_id` cannot mark another student's notification read (returns `None`).

### Pytest — `tests/unit/test_push_service.py` (new)

- `send_to_student` calls `webpush` once per subscription with the correct `subscription_info`/`vapid_*` kwargs (mock `pywebpush.webpush`).
- A `WebPushException` from one subscription is caught and logged, and does **not** prevent delivery attempts to the student's other subscriptions (NH-02/NH-09).
- Zero subscriptions → zero `webpush` calls, no exception (NH-09's "still appears in history" branch is exercised at the trigger-service level, not here).

### Pytest — `tests/unit/test_api_notifications.py` (new, mirrors `test_api_precheckins.py`/`test_api_medical_exams.py`)

- `POST /subscribe`: valid credentials + subscription payload → 201, row created; invalid credentials → 401 with `INVALID_CREDENTIALS` detail (NH-01's explicit divergence from the generic-message pattern, asserted directly, not assumed).
- `POST /history`: valid credentials → 200 with the student's notifications; invalid → 401; a second student's history is never returned for the wrong credentials.
- `POST /{id}/read`: valid credentials + own notification → 200, `read_at` set; another student's notification id → 404; invalid credentials → 401.
- `GET /vapid-public-key`: 200, no auth required.
- Rate limiting: the 6th rapid attempt for the same `registration_number` (or same IP) returns 429, mirroring `test_rate_limiter.py`'s existing style.

### Behave (BDD) — `tests/bdd/features/notification_hub.feature` (new), `tests/bdd/steps/notification_hub_steps.py` (new)

End-to-end trigger-to-history flow, in this suite's existing Given/When/Then style:

```gherkin
Feature: Notification Hub end-to-end trigger and history

  Scenario: A pre-check-in reminder fires once and appears in history
    Given an active student "Ana Silva" eligible for all events
    And an event "Aula de Aikido" starting in exactly 1 day
    When the daily notification check runs
    Then exactly one notification of type "pre_checkin_reminder" exists for the student
    When the student views their notification history with valid credentials
    Then the response includes a notification referencing "Aula de Aikido"

  Scenario: Running the check twice in the same day does not duplicate
    Given an active student "Ana Silva" eligible for all events
    And an event "Aula de Aikido" starting in exactly 1 day
    When the daily notification check runs twice
    Then exactly one notification of type "pre_checkin_reminder" exists for the student
```

### Jest (frontend) — `dojo-app/frontend/src/pages/NotificationHubPage.test.tsx` (new), mirrors `PreCheckInPage`-adjacent existing tests

- Submitting valid credentials renders the returned notification list.
- Submitting invalid credentials renders the error message from the 401 response.
- Clicking an unread notification calls the read endpoint and updates its badge.
- The "Ativar notificações" button is not rendered when `PushManager`/`serviceWorker` are absent from a mocked `window`/`navigator` (progressive-enhancement check).
- The subscribe flow posts the expected payload shape (`endpoint`, `keys.p256dh`, `keys.auth`, plus credentials) given a mocked `navigator.serviceWorker.register`/`pushManager.subscribe`.

### Cypress — `dojo-app/frontend/cypress/e2e/notification-hub.cy.ts` (new)

- Full opt-in-then-view-history flow: visit `/notifications`, submit valid credentials, assert the history list renders (seeded via a fixture/test-data setup mirroring existing Cypress specs' convention).
- Submit invalid credentials, assert the clear error message renders (not a generic "accepted" message — regression-guards NH-01's specific behavior).

## File-level task breakdown

1. **`dojo-app/backend/app/models/__init__.py`** (modify) — add `Notification`, `PushSubscription` models; add `notifications`/`push_subscriptions` relationships to `Student`.
2. **`dojo-app/backend/app/core/config.py`** (modify) — add `vapid_private_key`, `vapid_public_key`, `vapid_subject` settings.
3. **`dojo-app/backend/pyproject.toml`** (modify) — add `pywebpush = "^2.3.0"` to `[tool.poetry.dependencies]`.
4. **`dojo-app/backend/alembic/versions/<new>_add_notification_hub.py`** (new, via `alembic revision`) — as designed in "Migration plan."
5. **`dojo-app/backend/app/schemas/notification.py`** (new) — `StudentCredentials`, `PushSubscriptionKeys`, `PushSubscribeRequest`, `NotificationResponse`, `VapidPublicKeyResponse`.
6. **`dojo-app/backend/app/schemas/__init__.py`** (modify) — export the new schemas.
7. **`dojo-app/backend/app/services/notification_service.py`** (new) — `NotificationService`, as designed above.
8. **`dojo-app/backend/app/services/push_service.py`** (new) — `PushService`, as designed above.
9. **`dojo-app/backend/app/services/notification_trigger_service.py`** (new) — `NotificationTriggerService`, the three trigger routines.
10. **`dojo-app/backend/app/services/__init__.py`** (modify) — export `NotificationService`, `PushService`, `NotificationTriggerService`.
11. **`dojo-app/backend/app/jobs/__init__.py`** (new, empty) + **`app/jobs/notification_check.py`** (new) — the CronJob entrypoint.
12. **`dojo-app/backend/app/api/notifications.py`** (new) — the four routes designed above.
13. **`dojo-app/backend/app/main.py`** (modify) — register the new router.
14. **`dojo-app/backend/tests/unit/conftest.py`** (modify) — add `make_notification`/`make_push_subscription` factories.
15. **`dojo-app/backend/tests/unit/test_notification_trigger_service.py`** (new) — all NH-03/04/05/06/07 cases in "Test plan."
16. **`dojo-app/backend/tests/unit/test_notification_service.py`** (new) — CRUD/idempotency/authz cases.
17. **`dojo-app/backend/tests/unit/test_push_service.py`** (new) — delivery/best-effort-failure cases.
18. **`dojo-app/backend/tests/unit/test_api_notifications.py`** (new) — route/auth/rate-limit cases.
19. **`dojo-app/backend/tests/bdd/factories.py`** (modify) — add `NotificationFactory`/`PushSubscriptionFactory` if needed by the new feature file.
20. **`dojo-app/backend/tests/bdd/features/notification_hub.feature`** (new) + **`tests/bdd/steps/notification_hub_steps.py`** (new).
21. **`dojo-app/frontend/src/pages/NotificationHubPage.tsx`** (new).
22. **`dojo-app/frontend/src/pages/NotificationHubPage.test.tsx`** (new).
23. **`dojo-app/frontend/src/App.tsx`** (modify) — new public `/notifications` route.
24. **`dojo-app/frontend/public/manifest.json`** (new) + at least two PNG icon files under `public/`.
25. **`dojo-app/frontend/public/sw.js`** (new).
26. **`dojo-app/frontend/index.html`** (modify) — `<link rel="manifest">` + theme-color meta tag.
27. **`dojo-app/frontend/cypress/e2e/notification-hub.cy.ts`** (new).
28. **`dojo-app/frontend/package.json`** — **no new dependency** (confirmed: no PWA/push npm library needed, per Autocrítica). Listed here explicitly so the implementer doesn't add one unprompted.
29. **`dojo-infra/k8s/database/secret.example.yaml`-equivalent for the backend, and `dojo-infra/k8s/backend/deployment.yaml`'s env list** (modify) — add `VAPID_PUBLIC_KEY`/`VAPID_SUBJECT` (non-sensitive) and `VAPID_PRIVATE_KEY` (secret) environment entries to the live manifest set.
30. **`dojo-infra/k8s/backend/notification-check-cronjob.yaml`** (new) + **`dojo-infra/k8s/kustomization.yaml`** (modify, add the new resource) — the CronJob, added to the one, confirmed-live manifest set. This is the **first** `CronJob`/`Job` resource in `dojo-infra/k8s/` — there is no existing sibling file there to structurally mirror; the implementer can consult git history before commit `952c5f0` for the now-deleted `k8s/mysql-backup-cronjob.yaml`/`k8s/backend-migration-job.yaml` as a reference example if useful, but neither exists in the current working tree. **Not modified:** `dojo-app/backend/app/services/pre_checkin_service.py`, `medical_exam_service.py`, `balance_service.py` (all three are read-only dependencies of this feature, called but never changed), `DashboardPage.tsx`, `Layout.tsx` — listed explicitly as a "did not need to touch" checklist per the Non-Goals' backward-compatibility requirement.

## Risk assessment

- **Resolved (was flagged as an open ambiguity during design, confirmed by checking actual run history):** two Kubernetes manifest sets exist in this repo (`k8s/`, `dojo-infra/k8s/`), but only one is actually live. `deploy.yml` (applies `k8s/`) triggers on `push: branches: [main]` — this repo has no `main` branch (its default is `master`) — and `gh run list --workflow=deploy.yml` shows zero runs ever; `deploy-k8s.yml` (applies `dojo-infra/k8s/`) has a real, recent, successful run history against `master`. `dojo-infra/k8s/` is therefore the live manifest set, and `k8s/` is dead/vestigial code. This feature's CronJob is added only to `dojo-infra/k8s/` (task #30). **Already actioned, independent of this feature:** `k8s/` was confirmed dead code across the whole repo, not just for this feature, and the user had it (plus its now-orphaned `deploy.yml` workflow) removed during this planning pass, commit `952c5f0` — not merely flagged as a future cleanup candidate.
- **A missed CronJob execution silently and permanently skips that day's threshold crossings** (an exact-day-match query, not a lookback window, by design — see Autocrítica). Mitigated by running hourly (24 chances/day) rather than daily and by `backoffLimit`/`activeDeadlineSeconds` on the Job template, but not eliminated — a multi-hour node/DB outage spanning an entire calendar day would still cause a silent, permanent miss for any occurrence whose threshold fell that day. Accepted for v1 per "prefer simple architectures"; a future, more robust design (a small "last successfully processed date" watermark table, checked and caught up on the next run) is a low-cost enhancement if this proves to matter in practice, deliberately not built now since it wasn't asked for and doing so risks reintroducing NH-07's backfill concern if built carelessly.
- **NH-01's literal "clear error message" requirement reintroduces a registration_number/PIN validity oracle** that this codebase's other two public flows (`pre_checkins.py`, `medical_exams.py`) deliberately avoid. Mitigated identically to how every other public, credential-bearing endpoint in this app already is (the existing `RateLimiter` idiom, 5/60s per IP and per `registration_number`) — not a new or weaker bar than what's already accepted elsewhere for a PIN-bearing endpoint, but genuinely a different security posture than its two sibling public flows. Worth the user/security-reviewer being aware this was a deliberate, requirements-driven choice, not an oversight.
- **Push delivery to browsers that revoke permission or garbage-collect a stale subscription is never cleaned up** (explicitly out of scope per `requirements.md`'s own Open Questions) — the `push_subscriptions` table will grow monotonically with dead rows over time. Not a correctness problem (NH-09's in-app history never depends on push succeeding) and not large at this dojo's scale, but flagged as a known, accepted small operational debt, not a design gap.
- **`Notification.reference_id` has no database-level FK**, a deliberate divergence from this codebase's otherwise-universal "always use a real FK" convention (see Autocrítica) — flagged explicitly so a future maintainer doesn't "fix" this into a polymorphic three-FK design without first re-reading why it was rejected here (NH-10's frozen-message-at-creation-time design makes the join it would support unnecessary).
- **`NotificationService.authenticate_student` is now a third near-identical copy** of `PreCheckInService`/`MedicalExamService`'s own credential-check method (see Autocrítica) — flagged as a candidate follow-up refactor (extract a shared `student_service.py` helper), deliberately not done as part of this feature to keep its own change footprint minimal and low-risk.
- **`generate_occurrences`-scale reasoning does not apply here in reverse** — this feature's per-run row counts (events/exams/mensalidades crossing a threshold on one specific day) are naturally small and bounded by the dojo's actual daily class/exam/billing volume, not by any configurable window; no batching/commit-granularity decision analogous to `recurring-event-series`'s 365-row case was needed here, and none is introduced.

## Next Agent

Next Agent: doc-writer (to write ADRs for: (1) the Kubernetes CronJob scheduling choice over in-process APScheduler/Celery, including the hourly-cadence-vs-lookback-window reasoning; (2) the standard Web Push + VAPID via `pywebpush` choice over Firebase Cloud Messaging; (3) the `Notification.reference_id` non-FK/frozen-message design and its rejection of a three-FK polymorphic alternative; and (4) the NH-01 clear-error-vs-anti-enumeration security trade-off, since it deliberately diverges from this codebase's existing public-endpoint convention and should be recorded, not silently discovered later), then issue-creator to break the "File-level task breakdown" above into implementable issues, then `implementer` to build against this plan. Architecture is complete and self-reviewed; no further tech-analyst decision gate is expected. The two-manifest-set question raised during design is already resolved (confirmed via `gh run list`: `dojo-infra/k8s/` is live, `k8s/` is dead/vestigial) and does not need to be treated as an open item by any downstream agent.
