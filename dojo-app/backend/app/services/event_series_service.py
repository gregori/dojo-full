"""Business rules for recurring EventSeries: CRUD, idempotent occurrence generation, and same-day resolution."""

from datetime import UTC, datetime, timedelta

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
    def get_all_series(
        db: Session, is_active: bool | None = None, skip: int = 0, limit: int = 100
    ) -> list[EventSeries]:
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
        utc_now = datetime.now(UTC)
        occurrences = db.query(Event).filter(Event.event_series_id == series.id, Event.start_datetime > now).all()
        for event in occurrences:
            if EventSeriesService._matches_schedule(series, event.occurrence_date):
                event.title = series.title
                event.event_type_id = series.event_type_id
                event.description = series.description
                event.location = series.location
                event.minimum_belt_id = series.minimum_belt_id
                event.start_datetime = datetime.combine(event.occurrence_date, series.start_time, tzinfo=APP_TIMEZONE)
                event.end_datetime = (
                    event.start_datetime + timedelta(minutes=series.duration_minutes)
                    if series.duration_minutes
                    else None
                )
                if event.status == "cancelled":
                    event.status = "scheduled"
                event.updated_at = utc_now
            elif event.status != "cancelled":
                event.status = "cancelled"
                event.updated_at = utc_now
                EventService.cancel_pre_checkins_for_event(db, event)

    @staticmethod
    def generate_occurrences(db: Session, series_id: str, window_days: int = DEFAULT_GENERATION_WINDOW_DAYS) -> dict:
        """RES-02 primary path: idempotently create one Event per matching date in the
        rolling window, one row-level commit per date (see plan.md's batching
        decision below -- deliberately kept at per-row granularity, not batched).
        """
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
        existing = db.query(Event).filter(Event.event_series_id == series.id, Event.occurrence_date == today).first()
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
            db.query(Event).filter(Event.event_series_id == series.id, Event.occurrence_date == occurrence_date).first()
        )
        if existing:
            return existing, False

        start_datetime = datetime.combine(occurrence_date, series.start_time, tzinfo=APP_TIMEZONE)
        end_datetime = start_datetime + timedelta(minutes=series.duration_minutes) if series.duration_minutes else None
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
