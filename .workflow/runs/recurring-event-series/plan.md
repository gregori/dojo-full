# Implementation Plan — Recurring Event Series with Persistent Check-In QR (RES)

## Status

Design complete (2026-07-27); **redesigned in place (2026-07-27, same day) against the amended `requirements.md`** (RES-01–RES-09, D1-D3 all resolved, verdict "APPROVED WITH FOLLOW-UPS" in `review-requirements.md`'s Amendment Review). Three sections changed: RES-02's generation window default and commit granularity, RES-05's edit-propagation mechanism (fully reversed from the original design), and a new RES-09 cross-cutting `PreCheckIn`-cancellation cascade. Everything else in this document (the `EventSeries` model, `app/core/timezone.py`, the `UNIQUE(event_series_id, occurrence_date)` constraint, the `check_in_qr` integration, the API route list, the migration plan's overall shape) is unchanged from the first design pass — only the sections below are touched. Standalone, bounded feature. House style follows `.workflow/runs/contract-markdown-rendering/plan.md` (Requirements review / Autocrítica / Intended design / Test plan / File-level task breakdown / Risk assessment).

## Requirements review / ground truth re-confirmed

Re-verified directly against the current codebase before designing (2026-07-27):

- `Event` (`app/models/__init__.py:174-200`), `EventType` (`:121-132`), `Attendance` (`:203-220`) confirmed exactly as `requirements.md` describes. `Event.check_in_token` is **not** DB-unique today (`String(36), default=lambda: str(uuid.uuid4())`, no `unique=True`) — an existing latent gap, not something this feature needs to fix, but noted so the new `EventSeries.check_in_token` is deliberately built *with* `unique=True` rather than copying the gap forward (see Autocrítica).
- `EventService`/`AttendanceService` (`event_service.py`, `attendance_service.py`) confirmed matching the cited line numbers; `check_in`/`check_in_qr`'s cancelled-event guard is at lines 51-52 and 98-99 respectively, exactly as requirements state, and is reused unmodified.
- `GET /events/{event_id}/qr-code` (`app/api/events.py:105-111`) confirmed returning `{"check_in_token": ..., "url": f"/checkin?token={token}"}`.
- `MensalidadeService.generate_monthly_charges` (`app/services/mensalidade_service.py:44-100`) confirmed as the idiom to mirror: per-row `db.add()` + `db.commit()` inside a loop, catching `IntegrityError` on the unique-constraint race and treating it as "already exists, skip" — not a batch commit. This exact per-row commit/catch pattern is reused (generalized to re-fetch, not just skip — see below).
- **New finding — no reusable "QR-code rendering component" exists.** Grepped the entire frontend for `qrcode`/`QRCode`/`qr-code`: zero matches. `EventsPage.tsx`'s "QR" affordance (`:415-423`) is a plain `<a href="/checkin?token=...">` anchor with a `QrCode` lucide icon that opens `/checkin` in a new tab — there is no QR *image* generation anywhere in this codebase (no `qrcode`/`qrcode.react` dependency, no canvas/SVG rendering). RES-08's "reusing the existing per-event QR-code modal/rendering component" assumed a component that does not exist. This is corrected in the frontend design below: the series "View/print QR code" action reuses the *only* thing that actually exists today — the anchor-link pattern — not a fabricated new component. Flagged in Risk assessment as a pre-existing gap, not something this feature is scoped to fix.
- **`Student.class_days` is not a usable structural precedent.** It is a fully free-text `Text` column (`app/models/__init__.py:157`), never parsed anywhere in `student_service.py` or elsewhere — purely descriptive. `EventSeries.days_of_week` needs actual machine parseable day-of-week matching (RES-02/RES-04), so a comma-separated string of small integers is used instead (see below) — same storage simplicity level as `class_days` (a delimited string in one column, no new join table), but actually parseable, which `class_days` deliberately is not.
- `docker-compose.yml` confirms MySQL 8.4 (`mysql+pymysql`) in dev/prod; `tests/unit/conftest.py` confirms unit tests run against **SQLite in-memory** (`StaticPool`), not MySQL. Confirmed both engines' unique-index NULL semantics are the same for this feature's purposes: standard SQL treats NULL as distinct from any other value (including another NULL) for uniqueness checking, so a composite `UNIQUE(event_series_id, occurrence_date)` index does **not** need to be a filtered/partial index — rows where `event_series_id IS NULL` (every existing and future one-off `Event`) never collide with each other or with series rows, in both MySQL and SQLite. No special-cased index is needed; a plain composite unique index suffices on both engines the codebase actually uses. (MySQL does not support partial/filtered indexes at all, so this finding also forecloses that as an option — moot, since it isn't needed.)
- Alembic head is `56d1afc5972f` (`add_contracts.py`) — the new migration chains on top of it.
- `tests/bdd/` uses **Behave** (not pytest-bdd) with `.feature` files, `factories.py` (Factory Boy + `SQLAlchemyModelFactory`), and per-domain `steps/*.py` — `checkin.feature` is the closest existing precedent for the new series check-in scenarios.
- `App.tsx` registers pages as flat `<Route>` entries inside `PrivateRoute`/`AdminRoute` wrappers; `Layout.tsx` has a flat nav array (`{ path, label, icon }`). Adding a new page is a two-line change in each file — low risk, no restructuring needed.

**Re-confirmed for the 2026-07-27 amendment redesign (RES-09), read directly, not trusted from `requirements.md`'s own citations:**

- `app/services/event_service.py:110-117` (`delete_event`) sets only `event.status = "cancelled"` and `event.updated_at` — confirmed, never touches `PreCheckIn`. This is the pre-existing gap RES-09 fixes.
- `app/services/event_service.py:82-108` (`update_event`) has its `PreCheckIn`-cancellation cascade inline inside the `if "start_datetime" in update_data:` block (lines 98-103) — a `for` loop over `db.query(PreCheckIn).filter(event_id=..., status="confirmed")`, setting `status="cancelled"` and `cancelled_at=datetime.now(UTC)`. This exact loop body is what gets extracted into the new shared helper (see Autocrítica and the new PreCheckIn-cascade design subsection below) — not reinvented, just factored out and reused.
- `app/services/pre_checkin_service.py` imports `EventService` from `event_service.py` (`from app.services.event_service import EventService`) — confirmed this is a one-directional import today. This is the concrete reason the new shared cascade helper is placed in `event_service.py` itself rather than in `pre_checkin_service.py`: if it lived in `PreCheckInService` instead, `event_service.py` would need to import back from `pre_checkin_service.py`, creating a two-file import cycle (`event_service.py` → `pre_checkin_service.py` → `event_service.py`) that does not exist today. Placing the helper in `event_service.py` and having `event_series_service.py` import `EventService` from it introduces no such cycle (`event_service.py` does not, and will not, import `event_series_service.py`).

## Autocrítica (self-review, performed before committing the design below)

- **Timezone mechanism — sanity-checked hardest, per the task's own instruction.** Considered converting *every* datetime comparison in the new code (including RES-05's "past/future" phrasing and RES-06's "not-yet-occurred" cancellation check) through the `America/Sao_Paulo` wall clock. **Rejected as overengineering, fixed to a narrower, still-fully-correct design:** timezone-aware `datetime` comparison (`event.start_datetime > now`) is instant-based, not wall-clock-based — it produces the identical true/false result whether `now` is expressed as `datetime.now(UTC)` or `datetime.now(ZoneInfo("America/Sao_Paulo"))`, because both denote the same instant. RES-02/RES-04's requirement to use `America/Sao_Paulo` is load-bearing *only* where a **calendar date or day-of-week** is derived from "now" (the generation window's start date, day-of-week matching, same-day occurrence lookup) — there, `datetime.now(UTC).date()` and `datetime.now(ZoneInfo("America/Sao_Paulo")).date()` can genuinely disagree (e.g., 22:30 in São Paulo on a Tuesday is already Wednesday in UTC), so the conversion is required and correctly applied there (see `local_today()` below). For RES-05/RES-06's plain instant comparisons, using the same `APP_TIMEZONE`-aware "now" is harmless and consistent (so the design does exactly that, for uniformity — one shared "now" source, see below), but it is not doing any different *work* there than a bare UTC comparison would; this is documented explicitly so the implementer doesn't over-build timezone-conversion machinery where the requirement doesn't actually need it.
- **Considered a per-organization/per-dojo timezone field.** Rejected — explicit Non-Goal in `requirements.md`. A single module-level `ZoneInfo("America/Sao_Paulo")` constant is used, not a configurable setting.
- **Considered representing `days_of_week` as a normalized join table (`event_series_days`, one row per series+weekday).** Rejected: over-engineered for a bounded set (≤7 values, never queried independently of its owning series, no relational integrity need beyond "is this weekday in the set"). A single delimited string column (mirroring `class_days`'s storage simplicity, but parseable) is simpler and sufficient — consistent with "avoid unjustifiably heavy" modeling for a small, flat set, the same reasoning CTM's plan applied to rejecting a general Markdown library.
- **Considered making `occurrence_date` derivable from `start_datetime` instead of a separate stored column** (e.g., unique constraint on `(event_series_id, DATE(start_datetime))` via a functional index). Rejected: (1) MySQL/SQLite functional/expression indexes are more fragile and less portable across this codebase's two engines than a plain column; (2) `start_datetime` can later be edited via the existing single-event edit flow (RES-05's accepted workaround explicitly allows this), which would silently change what "the occurrence's date" means for uniqueness purposes if derived — a stored, snapshot-once `occurrence_date` decouples the uniqueness key from any later edit to `start_datetime`, which is exactly the RES-03 "snapshot, not live reference" principle applied one field further. **Fixed:** `Event` gains an explicit nullable `occurrence_date` (Date) column, populated once at generation time and never touched again, alongside `event_series_id`.
- **Considered a fully generic `check-in-qr` "series-or-event" resolution as a *new*, separate endpoint** rather than extending `POST /checkin/qr`. Rejected: RES-04's own text is explicit ("The existing check-in-by-QR flow ... is extended, not replaced ... first looked up as `Event.check_in_token` ... if not found, looked up as `EventSeries.check_in_token`") — this is not a genuinely open design question, it is a stated requirement. **Fixed:** `AttendanceService.check_in_qr` gains one `if not event:` fallback branch; no new endpoint, no `CheckInQRRequest` schema change, no frontend change to `CheckInPage.tsx`/`api.ts` (the same token, POSTed to the same URL, works for both an `Event` token and an `EventSeries` token).
- **Considered a blanket `try/except` around occurrence creation to "be safe."** Rejected per CLAUDE.md's "don't program defensively" — the `IntegrityError` catch is the one, specific, justified exception handler (mirrors `mensalidade_service.py`'s own precedent exactly), not a broad safety net. No other new code path in this feature can raise an unexpected exception that needs suppressing.
- **Considered letting `generate_occurrences` on an inactive series raise a 400.** Rejected: RES-06 only says deactivation "stops... producing any further occurrences," not that a manual trigger against an inactive series is an error condition worth surfacing distinctly. **Fixed:** `generate_occurrences` on an inactive series is a documented no-op (`created_count=0`), consistent with "no further occurrences," without adding an extra error path nobody asked for.
- **Checked testability:** every new function (`EventSeriesService.*`) takes/returns plain models, dicts, or primitives — no new abstraction layer; `_get_or_create_occurrence` is the single choke point for the concurrency-critical logic, callable directly from a unit test without going through HTTP, matching this codebase's existing service-layer testing discipline exactly.
- **(2026-07-27 amendment) RES-05's reconciliation branching — considered three separate code paths (update-in-place for Case A, cancel for Case B, a distinct "reactivate" path for the new re-added-day-of-week gap) vs. one unified method.** Rejected three separate paths: walking through the combined rule shows Case A/Case B/reactivate are the same underlying test applied to every not-yet-occurred occurrence — "does this occurrence's `occurrence_date` currently match the series' schedule (day-of-week in `days_of_week`, within the active date range, `is_active`)?" — with exactly two outcomes (matches → sync fields, un-cancel if needed; doesn't match → cancel if not already). Reactivation isn't a third case, it's what Case A's "sync fields" naturally does when the row happens to currently be `cancelled`. **Fixed:** one method, `_reconcile_future_occurrences`, replaces the old `_cancel_future_occurrences` entirely, built on one shared predicate (`_matches_schedule`, a rename/generalization of the original `_is_scheduled_today` to accept any date, not just today — reused by `resolve_today_occurrence` too, so there is exactly one place "does this date match this series' current schedule" is ever computed). This also means RES-06 (deactivation) is no longer special-cased at all: setting `is_active=False` simply makes `_matches_schedule` return `False` for every future date, so the existing Case-B cancel branch (with its `PreCheckIn` cascade) handles deactivation automatically — one cohesive method, not three ad-hoc ones, per the task's explicit ask.
  - **Consequence surfaced by this unification, checked deliberately, not accidental:** because `is_active` is now part of the same match predicate as day-of-week/date-range, flipping a series back from `is_active=False` to `is_active=True` will, on that same update, resync/reactivate any previously deactivation-cancelled future occurrence whose day-of-week and date range still match — the exact same mechanism as the re-added-day-of-week case, not a special exception for it. The original (pre-amendment) plan's test-plan note ("re-activating later does not un-cancel anything") is **no longer true** and is corrected in the Test plan section below. This is treated as a deliberate, desirable consequence of one uniform rule rather than a bug to special-case away — a series being reactivated and a day-of-week being re-added are the same product situation ("this schedule slot is scheduled again"), so they get the same recovery behavior for free, which is a simplicity win, not scope creep.
  - **Resolves the amendment review's two follow-up gaps explicitly:** (a) "kept consistent" now has one concrete answer — an already-cancelled occurrence whose date matches the current schedule again has its non-status fields resynced **and** its `status` flipped back to `scheduled` (not left cancelled-with-stale-fields, and not left cancelled-with-synced-fields either — full reactivation, the more useful of the two readings, since a resurrected-but-still-cancelled row would be a confusing intermediate state with no clear purpose). (b) the recovery path for a removed-then-re-added day-of-week is now this exact mechanism, not a manual single-event-edit workaround — re-adding the day to `days_of_week` in a subsequent series edit is itself sufficient; no separate admin action is needed. Confirmed this interacts correctly with generation: `_get_or_create_occurrence`'s existing-row check (`Event.event_series_id == series.id, Event.occurrence_date == occurrence_date`, no status filter) already treats a reactivated `scheduled` row exactly like any other existing row — a later `generate_occurrences` pass for that same date finds it and skips it, with zero code changes needed to that method.
  - **Considered whether reactivation should also un-cancel the occurrence's already-cancelled `PreCheckIn` rows.** Rejected — see Risk assessment: those `PreCheckIn` cancellations reflect a real, separate fact (a student's confirmed intent was invalidated at that moment) that reactivating the class slot doesn't retroactively undo; a student who wants to attend the reinstated class re-confirms through the normal pre-checkin flow. Stated explicitly in Risk assessment so a future maintainer doesn't "fix" this as an oversight.
- **(2026-07-27 amendment) Shared `PreCheckIn`-cancellation helper placement — considered `PreCheckInService` vs. `event_service.py` vs. a new standalone module.** Rejected `PreCheckInService`: `pre_checkin_service.py` already imports `EventService` from `event_service.py` (confirmed above); placing the helper in `PreCheckInService` instead would force `event_service.py` to import back from `pre_checkin_service.py` for `delete_event`'s fix, a genuine new circular import. Rejected a new standalone module (e.g. `app/services/event_cancellation.py`): unjustified indirection for a four-line function with exactly one real caller pattern (query `PreCheckIn` by `event_id`+`status="confirmed"`, flip to `cancelled`+`cancelled_at`) that already lives, inline, inside `event_service.py` today (`update_event`'s existing cascade) — extracting it one file further than necessary would be over-engineering a genuinely small piece of logic. **Fixed:** a new `EventService.cancel_pre_checkins_for_event(db, event)` static method in the existing `event_service.py`, extracted verbatim from `update_event`'s current inline loop; `update_event` is refactored to call it (behavior-preserving, not a behavior change) and `delete_event` is fixed to call it too (the actual RES-09 bug fix); `event_series_service.py` imports `EventService` from `event_service.py` to call the same helper from `_reconcile_future_occurrences`'s Case B branch — one import, no cycle (confirmed above), one implementation, three call sites.
- **Checked the day-of-week numbering convention for a frontend/backend mismatch risk.** Python's `date.weekday()` is Monday=0..Sunday=6; JavaScript's `Date.prototype.getDay()` is **Sunday=0..Saturday=6** — a real, easy-to-get-wrong mismatch if the frontend ever computed a weekday index at runtime and sent it to the API. **Fixed by construction, not by a runtime conversion:** the frontend never calls `getDay()` for this feature at all; the day-of-week checkbox UI is built from one static, hardcoded, Monday-first label array (`['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']` at indices `0..6`) whose index *is* the value sent to the API — sidestepping the mismatch entirely rather than requiring anyone to remember a conversion. Documented explicitly in "Intended design — frontend" and flagged again in Risk assessment as an implementer gotcha.

## Intended design — data model

### New timezone constant module: `app/core/timezone.py` (new file)

```python
"""The single, hardcoded application-wide timezone this feature computes 'today'/'now' against.

Per RES-02: no per-organization/per-dojo timezone concept exists or is added.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

APP_TIMEZONE = ZoneInfo("America/Sao_Paulo")


def local_now() -> datetime:
    """Current timezone-aware instant, expressed in the application's fixed timezone."""
    return datetime.now(APP_TIMEZONE)


def local_today() -> date:
    """Current wall-clock calendar date in the application's fixed timezone.

    This is the one place a UTC-vs-local distinction is actually load-bearing
    (see plan.md Autocrítica) -- every "today"/day-of-week computation in
    EventSeriesService goes through this function, not a bare datetime.now(UTC).
    """
    return local_now().date()
```

Uses Python's stdlib `zoneinfo` (already available, no new dependency, per the task's own note). `date.weekday()` (Monday=0..Sunday=6) is the day-of-week convention used everywhere in this feature — on `EventSeries.days_of_week` values, and matched directly against `local_today().weekday()`, with no translation layer.

### `EventSeries` model (new, in `app/models/__init__.py`)

```python
class EventSeries(UUIDMixin, TimestampMixin, Base):
    """A recurring weekly class template that produces ordinary Event occurrences.

    Fields mirror Event's own single-occurrence fields (RES-01/RES-03); days_of_week
    is a simple sorted comma-separated string of Monday=0..Sunday=6 integers -- not a
    join table, mirroring Student.class_days's storage simplicity but, unlike
    class_days, machine-parseable (see plan.md ground-truth notes).
    """

    __tablename__ = "event_series"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type_id: Mapped[str] = mapped_column(ForeignKey("event_types.id"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    minimum_belt_id: Mapped[str | None] = mapped_column(ForeignKey("belts.id"), nullable=True)
    days_of_week: Mapped[str] = mapped_column(String(20), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    series_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    series_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    check_in_token: Mapped[str] = mapped_column(
        String(36), unique=True, default=lambda: str(uuid.uuid4())
    )
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"), nullable=True)

    event_type: Mapped["EventType"] = relationship()
    minimum_belt: Mapped[Belt | None] = relationship(foreign_keys=[minimum_belt_id])
    organization: Mapped[Organization | None] = relationship()
    occurrences: Mapped[list["Event"]] = relationship(back_populates="event_series")
```

Note: `check_in_token` is given `unique=True` deliberately here (unlike `Event.check_in_token`, which lacks it today) — a fresh table is the right place to close that latent gap rather than propagate it, without touching `Event`'s existing column (out of this feature's scope to "fix").

### `Event` model changes (additive, RES-07/RES-08)

```python
event_series_id: Mapped[str | None] = mapped_column(ForeignKey("event_series.id"), nullable=True)
occurrence_date: Mapped[date | None] = mapped_column(Date, nullable=True)
```

```python
__table_args__ = (
    UniqueConstraint("event_series_id", "occurrence_date", name="uq_events_series_occurrence_date"),
)
```

```python
event_series: Mapped[Optional["EventSeries"]] = relationship(back_populates="occurrences")
```

- Both columns are `NULL` for every pre-existing row and every newly created one-off event (RES-07) — the unique constraint never fires for them, confirmed both engines treat `NULL` as distinct (see ground-truth notes).
- `occurrence_date` is the `America/Sao_Paulo` calendar date this occurrence represents, set once at generation time (pre-generated or lazy-created) and never mutated afterward — the RES-03 "snapshot, not live reference" principle extended to the uniqueness key itself (see Autocrítica).
- This single `UNIQUE(event_series_id, occurrence_date)` constraint is the concrete mechanism satisfying RES-02/RES-04's "impossible for two `Event` rows to ever exist for the same `(event_series_id, occurrence_date)` pair, no matter how requests are timed" requirement.

## Intended design — occurrence generation & resolution (the concurrency-critical path)

### New service: `app/services/event_series_service.py` (new file)

Single choke point for idempotent creation, shared by both the pre-generation path (RES-02) and the lazy-create/scan-time resolution path (RES-04) — this is what makes "generation and resolution write through the same guarantee, not two separate correctness requirements" (requirements.md's own framing) literally true in code, not just in prose:

```python
"""Business rules for recurring EventSeries: CRUD, idempotent occurrence generation, and same-day resolution."""

from datetime import datetime, timedelta, UTC

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.timezone import APP_TIMEZONE, local_now, local_today
from app.models import Event, EventSeries
from app.schemas import EventSeriesCreate, EventSeriesUpdate
from app.services.event_service import EventService

# Pinned to an exact integer per the amendment review's testability follow-up --
# 365 calendar days, inclusive of today, not leap-year-adjusted (window_end below
# is `today + 364 days`, always exactly 365 candidate dates regardless of whether
# a leap day falls inside the window). Revised from 28 -> 365, Amendment 1
# (requirements.md, 2026-07-27): a short rolling window silently breaks
# pre-checkin (pre_checkin_service.py has no virtual-occurrence fallback) once
# generation isn't re-triggered; the per-request override mechanism is unchanged.
DEFAULT_GENERATION_WINDOW_DAYS = 365


def _serialize_days(days: list[int]) -> str:
    return ",".join(str(d) for d in sorted(set(days)))


def _parse_days(days_of_week: str) -> set[int]:
    return {int(d) for d in days_of_week.split(",") if d != ""}


class EventSeriesService:
    @staticmethod
    def get_series(db: Session, series_id: str) -> EventSeries | None:
        return db.query(EventSeries).filter(EventSeries.id == series_id).first()

    @staticmethod
    def get_series_by_token(db: Session, token: str) -> EventSeries | None:
        return db.query(EventSeries).filter(EventSeries.check_in_token == token).first()

    @staticmethod
    def get_all_series(db: Session, is_active: bool | None = None, skip: int = 0, limit: int = 100) -> list[EventSeries]:
        query = db.query(EventSeries)
        if is_active is not None:
            query = query.filter(EventSeries.is_active == is_active)
        return query.order_by(EventSeries.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def create_series(db: Session, data: EventSeriesCreate, created_by: str) -> EventSeries:
        series = EventSeries(
            title=data.title,
            event_type_id=data.event_type_id,
            description=data.description,
            location=data.location,
            minimum_belt_id=data.minimum_belt_id,
            organization_id=data.organization_id,
            days_of_week=_serialize_days(data.days_of_week),
            start_time=data.start_time,
            duration_minutes=data.duration_minutes,
            series_start_date=data.series_start_date or local_today(),
            series_end_date=data.series_end_date,
            is_active=data.is_active,
            created_by=created_by,
        )
        db.add(series)
        db.commit()
        db.refresh(series)
        return series

    @staticmethod
    def update_series(db: Session, series_id: str, data: EventSeriesUpdate) -> EventSeries:
        """RES-05 (amended): propagates in place to every not-yet-occurred generated
        occurrence, regardless of when it was generated -- Case A update-in-place,
        Case B cancel, or reactivation, per `_reconcile_future_occurrences`.
        RES-06 (deactivation) is not special-cased here: `is_active=False` simply
        makes every future occurrence fail the same match predicate, so the Case-B
        cancel branch (with its PreCheckIn cascade, RES-09) handles it automatically.
        """
        series = EventSeriesService.get_series(db, series_id)
        if not series:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event series not found")

        update_data = data.model_dump(exclude_unset=True)
        if "days_of_week" in update_data:
            update_data["days_of_week"] = _serialize_days(update_data["days_of_week"])
        for field, value in update_data.items():
            setattr(series, field, value)
        series.updated_at = datetime.now(UTC)

        EventSeriesService._reconcile_future_occurrences(db, series)

        db.commit()
        db.refresh(series)
        return series

    @staticmethod
    def deactivate_series(db: Session, series_id: str) -> EventSeries:
        """RES-06 'end series' action: sets is_active False, cascading via update_series."""
        return EventSeriesService.update_series(db, series_id, EventSeriesUpdate(is_active=False))

    @staticmethod
    def _reconcile_future_occurrences(db: Session, series: EventSeries) -> None:
        """RES-05's combined rule (Case A / Case B / reactivation) and RES-06's
        deactivation cascade -- one cohesive method, not three ad-hoc paths.

        For every not-yet-occurred Event belonging to this series (start_datetime
        still ahead of "now"; already-occurred/past occurrences, including ones
        with recorded attendance, are never touched, matching or not):

          - if the occurrence's own occurrence_date still matches the series'
            (possibly just-updated) current schedule (`_matches_schedule`: day-of-
            week in days_of_week, within [series_start_date, series_end_date or
            unbounded], and series.is_active) -> Case A: sync its snapshotted
            fields to the series' new values and recompute start_datetime/
            end_datetime from the occurrence's *own* occurrence_date + the
            series' new start_time/duration_minutes. If the row is currently
            `cancelled`, this is also the reactivation path (the amendment
            review's resolved gap): flip it back to `scheduled` -- a previously
            removed-then-re-added day-of-week, or a deactivated-then-reactivated
            series, recovers this way, with no separate admin action needed.
            An already-`scheduled` matching row is simply re-synced (normal
            Case A, no status change).
          - otherwise -> Case B: if not already `cancelled`, cancel it and
            cascade-cancel its confirmed PreCheckIns (RES-09). An already-
            cancelled, still-non-matching row is left as-is (already correct,
            no redundant write, no PreCheckIn re-cascade needed).

        Note: this rule never resurrects/re-cancels based on PreCheckIn state --
        PreCheckIns cancelled by a prior Case-B cancellation stay cancelled even
        when their Event is later reactivated here (see plan.md Risk assessment).
        """
        now = local_now()
        occurrences = (
            db.query(Event)
            .filter(Event.event_series_id == series.id, Event.start_datetime > now)
            .all()
        )
        for event in occurrences:
            if EventSeriesService._matches_schedule(series, event.occurrence_date):
                event.title = series.title
                event.event_type_id = series.event_type_id
                event.description = series.description
                event.location = series.location
                event.minimum_belt_id = series.minimum_belt_id
                event.start_datetime = datetime.combine(
                    event.occurrence_date, series.start_time, tzinfo=APP_TIMEZONE
                )
                event.end_datetime = (
                    event.start_datetime + timedelta(minutes=series.duration_minutes)
                    if series.duration_minutes
                    else None
                )
                if event.status == "cancelled":
                    event.status = "scheduled"
                event.updated_at = now
            elif event.status != "cancelled":
                event.status = "cancelled"
                event.updated_at = now
                EventService.cancel_pre_checkins_for_event(db, event)

    @staticmethod
    def generate_occurrences(db: Session, series_id: str, window_days: int = DEFAULT_GENERATION_WINDOW_DAYS) -> dict:
        """RES-02 primary path: idempotently create one Event per matching date in the
        rolling window, one row-level commit per date (see plan.md's batching
        decision below -- deliberately kept at per-row granularity, not batched)."""
        series = EventSeriesService.get_series(db, series_id)
        if not series:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event series not found")

        today = local_today()
        window_start = max(today, series.series_start_date)
        window_end = today + timedelta(days=window_days - 1)
        if series.series_end_date and series.series_end_date < window_end:
            window_end = series.series_end_date

        created_count = 0
        skipped_count = 0
        if series.is_active and window_start <= window_end:
            days_of_week = _parse_days(series.days_of_week)
            current = window_start
            while current <= window_end:
                if current.weekday() in days_of_week:
                    _event, created = EventSeriesService._get_or_create_occurrence(db, series, current)
                    created_count += int(created)
                    skipped_count += int(not created)
                current += timedelta(days=1)

        return {
            "series_id": series.id,
            "window_start": window_start,
            "window_end": window_end,
            "created_count": created_count,
            "skipped_count": skipped_count,
        }

    @staticmethod
    def resolve_today_occurrence(db: Session, series: EventSeries) -> Event:
        """RES-04 scan-time resolution -- the four enumerated edge cases, in order."""
        today = local_today()

        # Case 1: existing row for today wins, regardless of status (cancelled included).
        existing = (
            db.query(Event)
            .filter(Event.event_series_id == series.id, Event.occurrence_date == today)
            .first()
        )
        if existing:
            return existing

        # Case 3: not a scheduled day (or series inactive/out of date range) -- reject, never create off-schedule.
        if not EventSeriesService._matches_schedule(series, today):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No occurrence scheduled today for this series",
            )

        # Case 2: scheduled today, nothing generated yet -- lazy-create exactly one, race-safe.
        event, _created = EventSeriesService._get_or_create_occurrence(db, series, today)
        return event

    @staticmethod
    def _matches_schedule(series: EventSeries, occurrence_date) -> bool:
        """Does `occurrence_date` currently fall on one of this series' configured
        days, within its active date range, while the series is active?

        Generalized (2026-07-27 amendment) from the original `_is_scheduled_today`
        to accept any date, not just today -- this is now the single predicate
        shared by RES-04's same-day resolution (`resolve_today_occurrence`, called
        with `local_today()`) and RES-05/RES-06's reconciliation
        (`_reconcile_future_occurrences`, called with each occurrence's own
        `occurrence_date`). One place computes "does this date match this
        series' current schedule," not two.
        """
        if not series.is_active:
            return False
        if occurrence_date < series.series_start_date:
            return False
        if series.series_end_date and occurrence_date > series.series_end_date:
            return False
        return occurrence_date.weekday() in _parse_days(series.days_of_week)

    @staticmethod
    def _get_or_create_occurrence(db: Session, series: EventSeries, occurrence_date) -> tuple[Event, bool]:
        """The single idempotent-creation choke point (RES-02 + RES-04 share it).

        Check-then-insert, with the DB's UNIQUE(event_series_id, occurrence_date)
        constraint as the race-safety backstop: on IntegrityError (a concurrent
        caller won the race), roll back and re-fetch -- same row either way,
        exactly one caller's insert ever succeeds.
        """
        existing = (
            db.query(Event)
            .filter(Event.event_series_id == series.id, Event.occurrence_date == occurrence_date)
            .first()
        )
        if existing:
            return existing, False

        start_datetime = datetime.combine(occurrence_date, series.start_time, tzinfo=APP_TIMEZONE)
        end_datetime = (
            start_datetime + timedelta(minutes=series.duration_minutes)
            if series.duration_minutes
            else None
        )
        event = Event(
            title=series.title,
            event_type_id=series.event_type_id,
            description=series.description,
            location=series.location,
            minimum_belt_id=series.minimum_belt_id,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            event_series_id=series.id,
            occurrence_date=occurrence_date,
            created_by=series.created_by,
            organization_id=series.organization_id,
            status="scheduled",
        )
        db.add(event)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = (
                db.query(Event)
                .filter(Event.event_series_id == series.id, Event.occurrence_date == occurrence_date)
                .first()
            )
            return existing, False
        db.refresh(event)
        return event, True
```

Notes:

- `generate_occurrences`'s 365-day-inclusive-of-today window matches RES-02 exactly (Amendment 1, 2026-07-27): `window_start = max(today, series.series_start_date)`, `window_end = today + 364 days` (365 dates total, today counted as day 1, not leap-year-adjusted — see the constant's own comment above), clipped down by `series_end_date` if set. This is a pure config-value change from the original 28/27-day arithmetic; the loop and idempotency mechanism are otherwise unchanged.
- `generate_occurrences` on an inactive series is a documented no-op (`created_count=0, skipped_count=0`), per Autocrítica.
- Every generated `Event` gets its own independently generated `check_in_token` via `Event`'s existing model-level `default=lambda: str(uuid.uuid4())` — no special-casing needed, since `Event(...)` is constructed the same way `EventService.create_event` constructs it (RES-04's "additive, not a replacement" per-occurrence token).
- `_reconcile_future_occurrences` compares `Event.start_datetime > now` where `now` is a timezone-aware instant — correct regardless of which timezone `now` is expressed in (see Autocrítica); using `local_now()` here is for consistency of "one shared now source" in this module, not because the comparison needs the `America/Sao_Paulo` conversion specifically.

**Batching/commit-granularity decision for the ~365-row scale (Amendment 1's explicit flag, resolved here, not left ambiguous):**

`_get_or_create_occurrence` keeps its existing per-row `db.add()` + `db.commit()` + catch-`IntegrityError` granularity, unchanged from the original 28-day-scale design — **no batching is introduced.** Reasoning:

- **Actual worst-case scale is still small.** The window length (365 dates), not the number of `days_of_week`, bounds the loop: at most one `Event` row per calendar date, so even a (unlikely, per RES-01, but not disallowed) 7-day/week series tops out at 365 commits in one request; a realistic 2-3 day/week series is ~104-156. This is "a few hundred simple single-row inserts," not a scale where per-commit overhead dominates.
- **Steady-state re-triggers are far smaller than the worst case.** After a series' first "Generate occurrences" fully populates the window, re-triggering it later (to roll the window forward) only inserts the handful of newly-in-range dates at the leading edge — every previously-generated date is skipped by the existing-row check before it ever reaches `db.add()`. The 365-commit case is effectively a one-time cost per series (its first generation), not a recurring one.
- **This is an explicit, human-triggered button click (RES-02/Constraints — no cron, no hot path), not a request an end user is blocked on.** An admin clicking "Gerar ocorrências" behind this frontend's existing `LoadingSpinner.tsx` and waiting a few seconds is an acceptable interaction for an infrequent administrative action — nothing in this feature's usage pattern (Mensalidade's own precedent included) requires sub-second response times for this specific action.
- **Batching would trade a correctness/complexity cost for a performance gain this scale doesn't need.** Committing every N rows (e.g. 25-50) would require deciding what happens when a batch itself partially fails (catch `IntegrityError` per-batch, per the task's own suggested fallback, then retry per-row *within* that one failed batch) — a second commit-boundary concept and a second failure-handling branch, on top of the existing per-row one, for a scale that is not a demonstrated bottleneck. Per CLAUDE.md's "don't overengineer," this is unjustified complexity: the existing per-row design's "blast radius" of a mid-loop failure is actually a non-issue given idempotency — a partial failure simply leaves earlier dates committed, and re-clicking "Generate occurrences" (or the next scheduled re-trigger) picks up exactly where it left off via the same existing-row check, with no compensating logic needed either way.
- **This reasoning is stated as an estimate, not a benchmark** — no load test was run against the actual MySQL dev container as part of this design pass. If `implementer`'s manual testing surfaces genuinely unacceptable latency (e.g., multiple seconds with no visible progress indicator) against real MySQL, batching every 25-50 rows is the documented fallback to reach for at that point — not a sign this decision was wrong, just a threshold this design pass doesn't have empirical grounds to pre-emptively engineer around.
- A single bulk-insert operation (e.g. SQLAlchemy Core `insert().values([...])` for the whole window in one statement) was also considered and rejected: it would need its own conflict-handling strategy (e.g. `ON DUPLICATE KEY` / `INSERT ... ON CONFLICT DO NOTHING`, engine-specific SQL) to preserve the idempotency guarantee, diverging from the one idiom (`IntegrityError` catch-and-refetch) this feature otherwise uses uniformly across `_get_or_create_occurrence` and mirrors from `mensalidade_service.py` — not worth a second, engine-specific concurrency mechanism for a request that already finishes in a few seconds worst-case.

### Cross-cutting: centralized `PreCheckIn`-cancellation cascade (RES-09, new, Amendment 3)

**Existing file, real change:** `app/services/event_service.py` (modify) — not a new file, and not previously listed as a modified file in this plan's first pass (see File-level task breakdown below, which now adds it explicitly).

```python
class EventService:
    ...

    @staticmethod
    def cancel_pre_checkins_for_event(db: Session, event: Event) -> None:
        """Cancel every confirmed PreCheckIn for an event, setting cancelled_at.

        Extracted from update_event's existing reschedule-cutoff cascade (the
        loop body below is unchanged, just given a name and a second caller) so
        every path that cancels an Event -- this service's own delete_event
        (RES-09's actual bug fix), update_event's pre-existing reschedule-cutoff
        trigger, and EventSeriesService's Case B / deactivation cascade -- shares
        one implementation instead of three copies of the same loop.
        """
        now = datetime.now(UTC)
        for pre_checkin in (
            db.query(PreCheckIn).filter(PreCheckIn.event_id == event.id, PreCheckIn.status == "confirmed").all()
        ):
            pre_checkin.status = "cancelled"
            pre_checkin.cancelled_at = now

    @staticmethod
    def update_event(db: Session, event_id: str, event_data: EventUpdate) -> Event:
        event = EventService.get_event(db, event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        update_data = event_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(event, field, value)

        # A reschedule into the one-hour cutoff invalidates existing intent;
        # attendees must explicitly confirm again once the event is reopened.
        if "start_datetime" in update_data:
            start_datetime = event.start_datetime
            if start_datetime.tzinfo is None:
                start_datetime = start_datetime.replace(tzinfo=UTC)
            if start_datetime <= datetime.now(UTC) + timedelta(hours=1):
                EventService.cancel_pre_checkins_for_event(db, event)

        event.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def delete_event(db: Session, event_id: str) -> None:
        """RES-09 fix: cancelling an Event now also cascades to its confirmed
        PreCheckIns -- this was the pre-existing gap (this method previously
        only set event.status, never touching PreCheckIn)."""
        event = EventService.get_event(db, event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        event.status = "cancelled"
        event.updated_at = datetime.now(UTC)
        EventService.cancel_pre_checkins_for_event(db, event)
        db.commit()
```

- **`update_event`'s change is a behavior-preserving refactor**, not a behavior change: the exact same loop body (previously inline at lines 98-103) now lives in `cancel_pre_checkins_for_event`, called from the same `if` condition, at the same point in the transaction (before the single `db.commit()` at the end of `update_event` — unchanged, the helper does not commit itself, since `delete_event` and `update_event` each manage their own single commit at their existing call sites, and `_reconcile_future_occurrences`'s callers similarly commit once at the end of `update_series`).
- **`delete_event`'s change is the actual RES-09 bug fix** — one new line, `EventService.cancel_pre_checkins_for_event(db, event)`, added before its existing single `db.commit()`.
- **`event_series_service.py` imports `EventService`** (`from app.services.event_service import EventService`, added to its existing import list) and calls `EventService.cancel_pre_checkins_for_event(db, event)` from `_reconcile_future_occurrences`'s Case B branch — no new logic duplicated in `EventSeriesService`, per RES-09's explicit centralization requirement. Confirmed no circular import: `event_service.py` imports only `app.models`/`app.schemas`, never `app.services.event_series_service` or `app.services.pre_checkin_service` (see ground-truth re-confirmation above).
- **Scope boundary respected:** `cancel_pre_checkins_for_event` is called only from the three sites RES-09 names (`delete_event`, `update_event`'s existing trigger, `EventSeriesService`'s Case B/deactivation cascade) — it does not fire on any other `Event` status transition (`scheduled` → `in_progress` → `finished`), and it does not touch `PreCheckIn`'s own independent cancellation flow (`PreCheckInService.cancel`, a student/admin directly cancelling a still-confirmed pre-checkin) — both explicitly out of RES-09's stated scope boundary.

### Integration into `AttendanceService.check_in_qr` (RES-04 point 5)

`app/services/attendance_service.py` changes:

```python
@staticmethod
def check_in_qr(db: Session, check_in_data: CheckInQRRequest) -> Attendance:
    """Process check-in via QR code -- an Event token (unchanged) or an EventSeries token (new, RES-04)."""
    event = EventService.get_event_by_token(db, check_in_data.check_in_token)
    if not event:
        series = EventSeriesService.get_series_by_token(db, check_in_data.check_in_token)
        if not series:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid check-in token")
        event = EventSeriesService.resolve_today_occurrence(db, series)

    if event.status == "cancelled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event is cancelled")

    regular_check_in = CheckInRequest(
        registration_number=check_in_data.registration_number, pin=check_in_data.pin, check_in_method="qrcode"
    )
    return AttendanceService.check_in(db, regular_check_in, event.id)
```

This is the *only* change to `attendance_service.py`. The existing `Event.check_in_token` lookup happens first and is byte-for-byte unchanged; the cancelled-event guard (line 98-99 today) is reused unmodified, exactly satisfying RES-04's "a cancelled occurrence found this way is then rejected by the existing, unmodified `check_in_qr` cancelled-event guard — no new cancellation-checking logic is needed here." Adds one new import: `from app.services.event_series_service import EventSeriesService` (no circular import risk — `event_series_service.py` does not import `attendance_service.py`).

## Intended design — API

### New `EventSeriesCreate`/`EventSeriesUpdate`/`EventSeriesResponse`/`GenerateOccurrencesResponse` schemas: `app/schemas/event_series.py` (new file)

```python
from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class EventSeriesBase(BaseModel):
    title: str
    event_type_id: str
    description: str | None = None
    location: str | None = None
    minimum_belt_id: str | None = None
    organization_id: str | None = None
    days_of_week: list[int]
    start_time: time
    duration_minutes: int | None = None
    series_start_date: date | None = None
    series_end_date: date | None = None
    is_active: bool = True

    @field_validator("days_of_week")
    @classmethod
    def validate_days_of_week(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("days_of_week must have at least one day")
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("days_of_week values must be 0 (Monday) through 6 (Sunday)")
        return sorted(set(v))


class EventSeriesCreate(EventSeriesBase):
    @model_validator(mode="after")
    def validate_dates(self):
        if self.series_end_date and self.series_start_date and self.series_end_date < self.series_start_date:
            raise ValueError("series_end_date must be after series_start_date")
        return self


class EventSeriesUpdate(BaseModel):
    title: str | None = None
    event_type_id: str | None = None
    description: str | None = None
    location: str | None = None
    minimum_belt_id: str | None = None
    days_of_week: list[int] | None = None
    start_time: time | None = None
    duration_minutes: int | None = None
    series_end_date: date | None = None
    is_active: bool | None = None

    @field_validator("days_of_week")
    @classmethod
    def validate_days_of_week(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return v
        if not v:
            raise ValueError("days_of_week must have at least one day")
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("days_of_week values must be 0 (Monday) through 6 (Sunday)")
        return sorted(set(v))


class EventSeriesResponse(EventSeriesBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    check_in_token: str
    created_by: str
    series_start_date: date
    created_at: datetime
    updated_at: datetime

    @field_validator("days_of_week", mode="before")
    @classmethod
    def _split_days(cls, v):
        if isinstance(v, str):
            return [int(x) for x in v.split(",") if x != ""]
        return v


class GenerateOccurrencesResponse(BaseModel):
    series_id: str
    window_start: date
    window_end: date
    created_count: int
    skipped_count: int
```

`days_of_week` is `list[int]` at the API boundary (ergonomic for a checkbox-array frontend and for tests); the service layer does the `list[int] <-> "0,2,5"` string conversion, so the storage format never leaks into the API contract.

### New routes: `app/api/event_series.py` (new file), registered in `app/main.py`

Mirrors `events.py`'s conventions exactly — `get_current_instructor_or_admin` for every route (the same auth level `Event`'s own CRUD uses, not `EventType`'s admin-only level, since a series is analogous to an `Event`, not to an `EventType`):

```python
router = APIRouter(prefix="/api/v1/event-series", tags=["event-series"])

GET    ""                          list_series(is_active: bool | None = None, ...)
GET    "/{series_id}"              get_series(series_id)
POST   ""                          create_series(data: EventSeriesCreate)          -> 201
PUT    "/{series_id}"              update_series(series_id, data: EventSeriesUpdate)
DELETE "/{series_id}"              deactivate_series(series_id)                     -> 204  # RES-06 "end series" action
POST   "/{series_id}/generate"     generate_occurrences(series_id, window_days: int | None = None) -> GenerateOccurrencesResponse
GET    "/{series_id}/qr-code"      get_series_qr_code(series_id) -> {"check_in_token": ..., "url": f"/checkin?token={token}"}
```

`DELETE` mirrors `cancel_event`'s existing convention exactly (`events.py:99-102`: `DELETE` = soft cancel, not hard delete) — here `DELETE /event-series/{id}` is the "end series" action (RES-06: sets `is_active=False`, cascades auto-cancel), the same soft-terminal-state idiom already established for `Event`. `GET /{series_id}/qr-code` is byte-for-byte the same response shape as `GET /events/{event_id}/qr-code` (RES-04's explicit requirement), so `CheckInPage.tsx` and its QR-encoding/link logic need zero changes.

`app/main.py` gains one import + one `app.include_router(event_series.router)` line, alongside the existing router list.

`app/services/__init__.py` gains `from app.services.event_series_service import EventSeriesService`. `app/schemas/__init__.py` gains the four new schema imports.

## Intended design — frontend

- **New page, not a tab inside `EventsPage.tsx`.** `EventsPage.tsx`'s one-off flow must stay "completely untouched" (RES-08) — a wholly separate new page/route eliminates any risk of touching it, and keeps a single, cohesive, independently testable file (mirrors how `EventTypesPage.tsx`, `BeltsPage.tsx`, `DojosPage.tsx` are each their own page rather than tabs bolted onto a bigger page — the codebase's existing "one page per admin concept" convention).
- **`dojo-app/frontend/src/pages/EventSeriesPage.tsx` (new)** — same structural shape as `EventsPage.tsx` (list + create/edit form + table), adapted for series fields:
  - Form fields: `title`, `event_type_id` select (reuses `GET /api/v1/events/types`, already fetched the same way `EventsPage.tsx` does), `location`, `minimum_belt_id` select (reuses `GET /api/v1/belts`), a `days_of_week` checkbox group built from a **static, hardcoded, Monday-first label array** —
    ```tsx
    const WEEKDAY_LABELS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    // index i (0-6) is both the display order and the exact integer sent to the API --
    // matches Python's date.weekday() convention (Monday=0); this codebase never calls
    // JS's Date.getDay() (Sunday=0) anywhere in this feature, sidestepping the mismatch
    // entirely rather than requiring a runtime conversion (see plan.md Autocrítica).
    ```
    `start_time` (`<input type="time">`), `duration_minutes` (numeric input, or a "sem hora de término" checkbox that nulls it, mirroring how `EventsPage.tsx`'s `end_datetime` is already optional), `series_start_date`/`series_end_date` (`<input type="date">`, with a "sem data de término / até cancelar" checkbox that nulls `series_end_date`), `is_active` toggle (defaults checked).
  - Table lists series with title, days-of-week (rendered from `WEEKDAY_LABELS`), start time, active/inactive badge, and a row of actions: edit, "Gerar ocorrências" (calls `POST /event-series/{id}/generate`, shows `created_count`/`skipped_count` via a toast — reuses the existing `Toast`/`useToast` pattern already used elsewhere in this frontend), the QR/check-in link (see below), and "Encerrar série" (calls `DELETE /event-series/{id}`, the RES-06 action).
  - **QR code action — corrected per the ground-truth finding above.** There is no existing QR-*image* component to reuse; `EventsPage.tsx`'s own "QR" affordance is itself just an anchor link. The series page reuses that exact same pattern: `<a href={`/checkin?token=${series.check_in_token}`} target="_blank">` with the same `QrCode` lucide icon — faithfully "reusing whatever component already renders the per-event QR" once ground truth is corrected to what that actually is. No new dependency, no new component.
- **`App.tsx`** — add `<Route path="/event-series" element={<PrivateRoute><EventSeriesPage /></PrivateRoute>} />` (instructor/admin level, matching `/events`, not `/event-types`'s admin-only level, since series creation is an instructor/admin action per RES-01/requirements' persona).
- **`Layout.tsx`** — add one nav entry, e.g. `{ path: '/event-series', label: 'Aulas Recorrentes', icon: Repeat }` (lucide-react already exports `Repeat`), placed next to the existing `Eventos` entry.
- `CheckInPage.tsx` and `api.ts`: **no changes** — the same `POST /api/v1/checkin/qr` call with the same `check_in_token` field works unmodified for a series token, since resolution happens entirely server-side (RES-04's design).

## Migration plan

One new Alembic revision, generated via `uv run alembic revision -m "add_event_series"` (chained on the current head `56d1afc5972f`, not a hand-picked ID, per this project's existing autogenerated-hash-ID convention):

**Upgrade:**
1. `op.create_table("event_series", ...)` — all `EventSeries` columns as designed above (`id` PK, FKs to `event_types`, `belts`, `users`, `organizations`; `check_in_token` with its own unique index; `days_of_week String(20)`; `start_time Time`; `duration_minutes Integer nullable`; `series_start_date Date not null`; `series_end_date Date nullable`; `is_active Boolean not null default true`; `created_at`/`updated_at`).
2. `op.add_column("events", sa.Column("event_series_id", sa.String(36), nullable=True))`
3. `op.add_column("events", sa.Column("occurrence_date", sa.Date(), nullable=True))`
4. `op.create_foreign_key(..., "events", "event_series", ["event_series_id"], ["id"])`
5. `op.create_unique_constraint("uq_events_series_occurrence_date", "events", ["event_series_id", "occurrence_date"])`

**Downgrade** (mirrors the MySQL FK-supporting-index caution already documented in `56d1afc5972f`'s/`ea64c8751ff2`'s downgrades — a composite unique index backing an FK needs a plain index restored first, or the FK is left unsupported when the composite index is dropped):
1. `op.create_index("ix_events_event_series_id", "events", ["event_series_id"])` (plain, to keep FK support alive)
2. `op.drop_constraint("uq_events_series_occurrence_date", "events", type_="unique")`
3. `op.drop_constraint(<fk name>, "events", type_="foreignkey")`
4. `op.drop_column("events", "occurrence_date")`
5. `op.drop_column("events", "event_series_id")`
6. `op.drop_table("event_series")`

No data migration needed — every existing `Event` row naturally gets `event_series_id = NULL`, `occurrence_date = NULL` (RES-07).

## Test plan

### Pytest unit — `tests/unit/test_event_series_service.py` (new), mirroring `test_event_service.py`'s flat `TestX` class style; extend `tests/unit/conftest.py` with a `make_event_series` factory (same shape as `make_event`)

- **CRUD:** create with valid `days_of_week`; create defaults `series_start_date` to `local_today()` when omitted; 404s for get/update/generate/deactivate on a nonexistent series. (The old "update changes only future-facing schedule fields" case is **removed** — RES-05's reversal means an update now deliberately *does* touch already-generated future occurrences; see the new RES-05 reconciliation cases below, which replace it.)
- **Schema validation:** `days_of_week` empty list rejected; out-of-range values (e.g. `7`, `-1`) rejected; `series_end_date < series_start_date` rejected (mirrors `EventCreate.validate_dates`'s existing style).
- **RES-03 field snapshot (amended scope):** generate one occurrence, then mutate the series' `title`/`location`/`event_type_id` *without* calling `update_series` (i.e. mutate the ORM object directly, bypassing the service, to isolate the snapshot-at-generation-time claim from RES-05's now-automatic propagation) — assert the already-generated occurrence's fields are untouched and a newly generated later occurrence reflects the new values. A second, separate test proves the amended behavior instead: calling `update_series` **does** propagate to the already-generated future occurrence (this is exactly the RES-05 Case A test below — cross-referenced here, not duplicated).
- **RES-02 generation window:** 365-day window is inclusive of today when today matches a scheduled weekday, and produces exactly 365 candidate dates end-to-end (asserting the pinned literal, not just "approximately a year"); window clipped by `series_end_date`; window respects `series_start_date` in the future (no occurrences before it); non-matching weekdays produce no rows; re-running `generate_occurrences` twice in a row produces `created_count=0` the second time (sequential idempotency) with the same row count in the DB.
- **RES-02 365-row commit strategy:** a test asserting that generating a full 365-day window for a 7-day/week series (the worst case) commits exactly once per created row (e.g. by counting `Session.commit` calls via a monkeypatched/wrapped session, or asserting all 365 rows exist even if a simulated failure is injected partway through and the loop is simply re-run) — proves the chosen per-row-commit design (see plan.md's batching decision) actually delivers its claimed idempotent-resume property at this scale, not just at the original 28-row scale.
- **RES-02/RES-04 concurrency-safe idempotency (the required test, per CLAUDE.md/requirements.md):**
  1. **Direct constraint test:** insert two `Event` rows with identical `(event_series_id, occurrence_date)` directly (bypassing the service) and assert the second `db.commit()` raises `IntegrityError` — proves the DB constraint itself is real and enforced, independent of any application code.
  2. **Simulated-race test on `_get_or_create_occurrence`:** using a second, independent `Session` on the same `db_engine` fixture, insert-and-commit a competing `Event` for the same `(series_id, date)` *between* `EventSeriesService`'s existing-row check and its own `db.commit()` (achieved by calling the "existing" check, then manually committing the competitor via the second session, then letting the original session's `db.add`/`db.commit()` proceed and fail) — assert: no exception propagates out of `_get_or_create_occurrence`, it returns the competitor's row (same `id` as the second session's insert), and exactly one `Event` row exists for that `(series_id, date)` afterward. This exercises the actual catch-`IntegrityError`-then-refetch code path with a genuine two-writer scenario, per the task's own suggested approach (real thread-level concurrency not required).
  3. Same simulated-race pattern repeated once against `resolve_today_occurrence` directly (not just the private helper), asserting it also returns a single, consistent `Event` under the same race and never raises.
- **RES-04 four enumerated edge cases (direct `resolve_today_occurrence` tests):**
  1. Existing `Event` for today (any status) is returned as-is, no new row created — including explicitly with `status="cancelled"` (proves lazy-creation never resurrects/bypasses a cancelled occurrence).
  2. No existing row, today matches `days_of_week`, series active and in range — exactly one `Event` is created and returned.
  3. No existing row, today does **not** match `days_of_week` — raises `HTTPException(400)` with the "No occurrence scheduled today for this series" detail; no row created.
  3b. Same 400, additionally asserted for: `series.is_active = False`; `today < series_start_date`; `today > series_end_date`.
  4. Full-flow: `resolve_today_occurrence` returns a `cancelled` `Event`, then `AttendanceService.check_in` (called with that event's id) is rejected by the existing, unmodified cancelled-event guard — proves the two layers compose correctly end-to-end.
- **RES-05 reconciliation (`_reconcile_future_occurrences`), replacing the old "edits only affect future generation" tests entirely:**
  1. **Case A — schedule-preserving edit:** generate a future occurrence, then `update_series` with a new `title`/`location`/`event_type_id`/`minimum_belt_id`/`start_time`/`duration_minutes` — assert the occurrence's snapshotted fields are updated to match, and its `start_datetime`/`end_datetime` are recomputed from its own (unchanged) `occurrence_date` combined with the series' new `start_time`/`duration_minutes` (assert the exact recomputed value, not just "changed"). A past occurrence (already-occurred `start_datetime`), including one with recorded attendance, is asserted **unchanged** by the same edit.
  2. **Case B — day removed from `days_of_week`:** generate occurrences for two different configured weekdays, then `update_series` removing one of those weekdays from the pattern — assert every not-yet-occurred occurrence on the removed weekday is now `status="cancelled"`, its confirmed `PreCheckIn` rows (if any) are also `status="cancelled"` with `cancelled_at` set (RES-09 cascade, cross-referenced with the RES-09 test group below), and occurrences on the weekday(s) that remain are handled by Case A instead (fields synced, not cancelled).
  3. **Combined rule — `series_end_date` shortened:** generate an occurrence beyond a new, shorter `series_end_date`, then `update_series` with that shortened `series_end_date` — assert the now-out-of-range occurrence is cancelled (same as Case B), not left stale.
  4. **Reactivation — the amendment review's resolved gap, a re-added day-of-week:** generate occurrences on Monday+Wednesday, `update_series` removing Wednesday (asserted cancelled, per Case B above), then `update_series` again re-adding Wednesday — assert the previously-cancelled Wednesday occurrence is now `status="scheduled"` again **and** its snapshotted fields reflect the series' current values (both parts of the resolved gap: reactivation is real, and fields are synced, not left stale) — and assert its previously-cancelled confirmed `PreCheckIn` rows (if any existed) remain `status="cancelled"` and are **not** un-cancelled by this reactivation (the stated, intended behavior, not a bug — see Risk assessment).
  5. **Reactivation via whole-series deactivate/reactivate:** `deactivate_series` (asserts every future occurrence cancelled, RES-06, via the same reconciliation path — no separate `_cancel_future_occurrences` method exists anymore), then `update_series` with `is_active=True` — assert every future occurrence whose day-of-week/date-range still matches the current schedule is reactivated (`status="scheduled"`, fields resynced) exactly like case 4 above, since it is the same underlying mechanism, not a special case. This explicitly supersedes and corrects the original plan's test-plan note that "re-activating later does not un-cancel anything" — that is no longer the design's behavior, and this test asserts the corrected one.
  6. **Idempotency of reconciliation itself:** calling `update_series` twice in a row with no actual field changes (`exclude_unset` payload empty) leaves every occurrence's `updated_at` effectively a no-op from a data-correctness standpoint — i.e., running reconciliation repeatedly never double-cancels, never flips an already-`scheduled` matching row to some other state, and never re-cascades an already-cancelled `PreCheckIn`.
- **RES-09 `PreCheckIn`-cancellation cascade (new, all three trigger paths), `tests/unit/test_event_service.py` (extend) + `tests/unit/test_event_series_service.py` (new cases above):**
  1. **`EventService.delete_event` (the actual bug fix):** an event with one or more `confirmed` `PreCheckIn` rows, cancelled via `delete_event` — assert every `confirmed` row is now `status="cancelled"` with `cancelled_at` set; a `PreCheckIn` that was already `cancelled` or `converted` before the call is left untouched (no double-cancel, no resurrection of a `converted` row).
  2. **`EventService.update_event`'s existing reschedule-cutoff trigger, regression-guarded:** unchanged behavior after the refactor into `cancel_pre_checkins_for_event` — a reschedule into the one-hour cutoff still cancels confirmed `PreCheckIn` rows exactly as it did before this refactor (same assertions as the pre-existing test, now also confirming the shared helper didn't change the observable behavior).
  3. **`EventSeriesService`'s Case B cascade:** covered by the RES-05 Case B test above (case 2) — cross-referenced here, not duplicated, per RES-09's "one behavior, three trigger paths" framing.
  4. **`EventSeriesService`'s RES-06 deactivation cascade:** covered by the RES-05/RES-06 reactivation test group above (case 5's precondition) — cross-referenced here, not duplicated.
- **Timezone-boundary test (direct, isolated):** freeze/monkeypatch `app.core.timezone.local_now` (or inject a fixed `datetime` via a small seam) to a UTC instant that is a different calendar date in `America/Sao_Paulo` (e.g. `2026-03-10 02:30 UTC` == `2026-03-09 23:30` in São Paulo, UTC-3) and assert `local_today()`/`generate_occurrences`'s window start and `resolve_today_occurrence`'s day-of-week matching all use the São Paulo date, not the UTC date — this is the one test directly proving RES-02/RES-04's timezone requirement, not just asserting it works "most of the time."

### Pytest — `tests/unit/test_attendance_service.py` (extend existing `TestAttendanceServiceCheckInQR` class)

- A series token resolves to today's occurrence and records attendance exactly like an `Event` token does (reuses `make_event_series`/`make_event` factories).
- A series token on a non-scheduled day returns 400 (bubbled up from `resolve_today_occurrence`, not re-implemented in `attendance_service.py`).
- A series token whose resolved occurrence is `cancelled` returns 400 "Event is cancelled" (the existing guard, now exercised via the series path).
- An unrecognized token (neither an `Event` nor an `EventSeries` token) still returns 404 "Invalid check-in token" — unchanged behavior, regression-guarded.

### Pytest — `tests/unit/test_api_event_series.py` (new, mirrors the existing `test_api_belts.py`/`test_api_students.py` style for auth/route-level coverage)

- Instructor/admin auth required on every route (401/403 without it, mirroring `events.py`'s existing tests); CRUD round-trip through the actual FastAPI routes (not just the service layer) for at least create/list/get/update/deactivate/generate/qr-code, confirming schema (de)serialization (`days_of_week` list-in/list-out) works end-to-end through Pydantic, not just in the service layer directly.

### Behave (BDD) — `tests/bdd/features/event_series.feature` (new), `tests/bdd/steps/event_series_steps.py` (new), extend `tests/bdd/factories.py` with `EventSeriesFactory`

Mirrors `checkin.feature`'s Given/When/Then style:

```gherkin
Feature: Recurring event series check-in

  Background:
    Given the database is empty
    And belt "6º Kyu" exists for category "adult" with sort order 1
    And event type "Aula Regular" exists with color "#3498db"
    And a student "João Silva" exists with: ...

  Scenario: Scanning a series QR on a scheduled day checks in against today's occurrence
    Given a recurring event series "Aikido Geral" on Monday, Wednesday, Saturday at "07:00"
    And today is a scheduled day for the series
    When the student checks in via the series QR code with valid credentials
    Then the response status should be 200
    And exactly one event occurrence should exist for the series today

  Scenario: Scanning a series QR twice in the same day resolves to the same occurrence
    Given a recurring event series "Aikido Geral" on Monday, Wednesday, Saturday at "07:00"
    And today is a scheduled day for the series
    And the series QR has already been scanned once today by another student
    When the student checks in via the series QR code with valid credentials
    Then the response status should be 200
    And exactly one event occurrence should exist for the series today

  Scenario: Scanning a series QR on a non-scheduled day is rejected
    Given a recurring event series "Aikido Geral" on Monday, Wednesday, Saturday at "07:00"
    And today is not a scheduled day for the series
    When the student checks in via the series QR code with valid credentials
    Then the response status should be 400
    And the response should contain "detail" with value "No occurrence scheduled today for this series"

  Scenario: A cancelled occurrence blocks check-in even via the series QR
    Given a recurring event series "Aikido Geral" on Monday, Wednesday, Saturday at "07:00"
    And today's occurrence for the series has been cancelled
    When the student checks in via the series QR code with valid credentials
    Then the response status should be 400
    And the response should contain "detail" with value "Event is cancelled"
```

("today is/is not a scheduled day" steps drive the test by picking `days_of_week` relative to the real current date at test-run time — mirroring how `checkin.feature`'s existing steps avoid hardcoding dates; implementer's call on the exact mechanic, e.g. compute `days_of_week` from `date.today().weekday()` at scenario setup, not fixed literals, so this feature doesn't need to freeze time in Behave, consistent with this suite's existing style of not mocking `datetime.now` anywhere.)

### Jest (frontend) — `dojo-app/frontend/src/pages/EventSeriesPage.test.tsx` (new), mirrors `EventsPage`-adjacent existing tests (`StudentsPage.test.tsx`, `BeltsPage.test.tsx`, `BeltRequirementsPage.test.tsx` are the closest existing precedents for a list+form admin page)

- Renders the series list from a mocked `api.get('/api/v1/event-series')`.
- Submitting the create form posts the expected payload shape, including `days_of_week` as a `number[]` built from the checkbox group (assert the exact indices sent match `WEEKDAY_LABELS`' Monday-first order, guarding the JS/Python weekday-convention risk called out in Autocrítica).
- "Gerar ocorrências" button calls `POST /api/v1/event-series/{id}/generate` and surfaces `created_count`/`skipped_count` via the existing toast mechanism.
- "Encerrar série" calls `DELETE /api/v1/event-series/{id}`.
- The QR action renders an anchor to `/checkin?token=<series.check_in_token>` (not a modal/image component, matching the corrected ground truth above).

### Cypress — new `dojo-app/frontend/cypress/e2e/event-series.cy.ts`, following the existing `contracts.cy.ts` custom-command convention

- Create a series via the UI, trigger "Gerar ocorrências", and confirm at least one generated occurrence is visible/manageable via the existing `EventsPage.tsx` list (RES-07's "occurrences remain visible and manageable via the existing `EventsPage.tsx` list like any other `Event`" — a real assertion that the additive FK doesn't break anything on the untouched page).
- End the series ("Encerrar série") and confirm its QR link stops producing new occurrences going forward is out of scope for a same-session Cypress run (that's a multi-day behavior); instead assert the UI reflects the inactive state and the "Gerar ocorrências" action, if re-triggered, reports `created_count: 0`.

## File-level task breakdown

1. **`dojo-app/backend/app/core/timezone.py`** (new) — `APP_TIMEZONE`, `local_now()`, `local_today()`.
2. **`dojo-app/backend/app/models/__init__.py`** (modify) — add `EventSeries` model; add `event_series_id`/`occurrence_date` columns + `UniqueConstraint`/relationship to `Event`.
3. **`dojo-app/backend/alembic/versions/<new>_add_event_series.py`** (new, via `uv run alembic revision`) — as designed in "Migration plan."
4. **`dojo-app/backend/app/schemas/event_series.py`** (new) — `EventSeriesCreate`/`Update`/`Response`, `GenerateOccurrencesResponse`.
5. **`dojo-app/backend/app/schemas/__init__.py`** (modify) — export the four new schemas.
6. **`dojo-app/backend/app/services/event_series_service.py`** (new) — `EventSeriesService` as designed above, including `_reconcile_future_occurrences`/`_matches_schedule` (RES-05/RES-06) and the `EventService.cancel_pre_checkins_for_event` call from its Case B branch (RES-09).
7. **`dojo-app/backend/app/services/__init__.py`** (modify) — export `EventSeriesService`.
8. **`dojo-app/backend/app/services/event_service.py`** (modify — **new in this redesign pass, not in the original file-level breakdown**) — RES-09's actual fix: add `EventService.cancel_pre_checkins_for_event`, extracted from `update_event`'s existing inline cascade; call it from `delete_event` (the bug fix) and from the refactored `update_event` (behavior-preserving).
9. **`dojo-app/backend/app/services/attendance_service.py`** (modify) — `check_in_qr`'s new series-token fallback branch (the only change in this file).
10. **`dojo-app/backend/app/api/event_series.py`** (new) — the seven routes designed above.
11. **`dojo-app/backend/app/main.py`** (modify) — register the new router.
12. **`dojo-app/backend/tests/unit/conftest.py`** (modify) — add `make_event_series` factory.
13. **`dojo-app/backend/tests/unit/test_event_series_service.py`** (new) — all service-layer cases in "Test plan," including the RES-05 reconciliation cases (Case A/B/combined/reactivation) and the RES-02 365-row commit-strategy case.
14. **`dojo-app/backend/tests/unit/test_event_service.py`** (modify — **new in this redesign pass**) — add `delete_event`'s new `PreCheckIn`-cascade test (RES-09's bug-fix case) and a regression test confirming `update_event`'s existing cascade behavior is unchanged after the `cancel_pre_checkins_for_event` refactor.
15. **`dojo-app/backend/tests/unit/test_attendance_service.py`** (modify) — extend `TestAttendanceServiceCheckInQR` with the series-token cases.
16. **`dojo-app/backend/tests/unit/test_api_event_series.py`** (new) — route/auth-level tests.
17. **`dojo-app/backend/tests/bdd/factories.py`** (modify) — add `EventSeriesFactory`.
18. **`dojo-app/backend/tests/bdd/features/event_series.feature`** (new) + **`tests/bdd/steps/event_series_steps.py`** (new).
19. **`dojo-app/frontend/src/pages/EventSeriesPage.tsx`** (new).
20. **`dojo-app/frontend/src/pages/EventSeriesPage.test.tsx`** (new).
21. **`dojo-app/frontend/src/App.tsx`** (modify) — new `/event-series` route.
22. **`dojo-app/frontend/src/components/Layout.tsx`** (modify) — new nav entry.
23. **`dojo-app/frontend/cypress/e2e/event-series.cy.ts`** (new).
24. **`dojo-app/backend/app/services/mensalidade_service.py`, `app/api/events.py`, `EventsPage.tsx`, `CheckInPage.tsx`, `api.ts`, `app/services/pre_checkin_service.py`** — **not modified** (explicitly confirmed untouched, including `pre_checkin_service.py` — RES-09's cascade helper lives in `event_service.py` precisely so this file needs no change; listed here so the implementer has an explicit "did not need to touch" checklist matching RES-07/RES-08's backward-compatibility requirement).

## Risk assessment

- **No real QR-image rendering exists anywhere in this codebase today** (see ground-truth finding above) — the feature's own business motivation ("prints a QR code and posts it on the wall") is only partially served by a plain link today, for *both* one-off events and the new series. This is a pre-existing gap this feature does not introduce and is not scoped to fix (RES-08 only asks to reuse whatever exists), but it materially affects the literal "prints a QR code" business outcome. Worth surfacing back to the user/product as a candidate follow-up (e.g. adding a `qrcode` frontend dependency to render an actual scannable image) — not blocking this plan, documented so it isn't silently lost.
- **JS/Python weekday-numbering mismatch (`Date.getDay()` vs. `date.weekday()`)** — mitigated by construction (static label array, no runtime conversion), but is exactly the kind of off-by-convention bug that's easy to reintroduce in a future edit (e.g. if someone later "simplifies" the frontend by computing today's weekday index for a UI highlight). Flagged explicitly for the implementer and worth a code comment at the `WEEKDAY_LABELS` definition site, not just this plan.
- **Timezone edge case around DST-less Brazil vs. historical DST years:** `America/Sao_Paulo` has not observed DST since 2019, so `ZoneInfo("America/Sao_Paulo")` is currently a fixed UTC-3 offset in practice — but `zoneinfo` correctly handles the historical tzdata either way; no code in this feature hardcodes a numeric UTC offset, so a hypothetical future reintroduction of Brazilian DST would not require a code change, only a tzdata update. Documented, not a present risk.
- **`generate_occurrences`'s per-date commit loop** (mirroring `mensalidade_service.py`'s exact precedent, now at up to ~365 rows instead of ~28 — see the batching decision above) means a mid-loop failure leaves earlier dates committed and later ones not — identical behavior/risk profile to the existing, already-shipped Mensalidade generation, deliberately kept rather than engineered away at the larger scale (reasoning above); re-triggering "Generate occurrences" resumes cleanly, no cleanup step needed. Not a new risk class this feature introduces, just the same inherited profile at ~13x the row count.
- **`EventSeries.check_in_token` given `unique=True` while `Event.check_in_token` still lacks it** is a deliberate, small inconsistency (see Autocrítica) — flagged so a future cleanup pass on `Event.check_in_token` isn't mistaken for this feature's own scope creep if someone notices the asymmetry later.
- **(2026-07-27 amendment) Reactivation does not un-cancel already-cancelled `PreCheckIn` rows — stated explicitly as intended, not a bug to "fix" later.** When `_reconcile_future_occurrences` flips a previously-cancelled occurrence back to `scheduled` (a re-added day-of-week, or a deactivated-then-reactivated series), any `PreCheckIn` rows that were cancelled as part of that earlier cancellation (RES-09) stay `cancelled` — reactivating the class slot does not retroactively restore a student's prior confirmed intent. A student who wants to attend the reinstated class must re-confirm through the normal pre-checkin flow. This is a deliberate, correct asymmetry (an `Event`'s schedule state and a student's own confirmed intent are two different facts, and only the first is being restored here) — flagged explicitly so a future maintainer doesn't treat the lack of PreCheckIn-resurrection as an oversight and "fix" it into an unwanted auto-reconfirmation.
- **(2026-07-27 amendment) Unifying RES-05's edit-propagation and RES-06's deactivation cascade into one `_matches_schedule`/`_reconcile_future_occurrences` mechanism means re-activating a series (`is_active` False→True) now also resyncs/reactivates its previously deactivation-cancelled future occurrences**, which the original (pre-amendment) plan's own test-plan note explicitly said would *not* happen. This is a deliberate consequence of choosing one uniform rule over three special-cased ones (see Autocrítica) — surfaced here as a real, user-visible behavior change from the first design pass, not a regression: an admin re-activating a series now gets its future schedule fully restored in one step, consistent with how re-adding a single day-of-week already behaves.
- **RES-02's 365-day default significantly increases how many `Event` rows a single admin action can create and how many rows a single series edit can touch (`_reconcile_future_occurrences` now scans every not-yet-occurred row for the series, not just ones from a bounded 28-day window).** For a long-lived, frequently-edited series, this could accumulate to a few hundred rows scanned/updated per edit — still a single, bounded, in-process query+loop (no pagination or streaming needed at this scale), but worth the implementer being aware the "cheap 28-row loop" assumption from the first design pass no longer holds at either generation or edit time.
- **D1/D2/D3 defaults are now historical, resolved decisions, not open sign-off gates** (per `requirements.md`'s amended "Decisions Requiring Sign-Off" section — the user explicitly resolved all three in conversation) — deactivation auto-cancel (+ PreCheckIn cascade), edit-propagation reversed to "always propagate," and the window default raised to 365, all implemented exactly as specified; this plan does not re-litigate any of them.

## Next Agent

Next Agent: doc-writer (to write ADRs for: (1) the timezone-constant mechanism and the DB-unique-constraint concurrency-safety mechanism, from the first design pass; (2) the new unified `_matches_schedule`/`_reconcile_future_occurrences` reconciliation mechanism and its reactivation behavior, and (3) the centralized `EventService.cancel_pre_checkins_for_event` cascade helper and its placement rationale — the three decisions this redesign pass's Autocrítica scrutinized hardest), then issue-creator to break the "File-level task breakdown" above into implementable issues, then `implementer` to build against this plan. Architecture is complete and self-reviewed for both the original design and this amendment redesign; no further tech-analyst decision gate is expected unless `implementer` surfaces a genuine scope-changing ambiguity.
