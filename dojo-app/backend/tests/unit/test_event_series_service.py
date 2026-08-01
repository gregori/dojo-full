"""Unit tests for app.services.event_series_service module."""

from datetime import UTC, date, datetime, time, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

import app.services.event_series_service as event_series_service_module
from app.core.timezone import APP_TIMEZONE, local_today
from app.models import Event, PreCheckIn
from app.schemas import CheckInRequest, EventSeriesCreate, EventSeriesUpdate
from app.services.attendance_service import AttendanceService
from app.services.event_series_service import DEFAULT_GENERATION_WINDOW_DAYS, EventSeriesService
from tests.unit.conftest import (
    make_belt,
    make_dojo,
    make_event,
    make_event_series,
    make_event_type,
    make_student,
    make_user,
)


def _weekday_not_in(days: set[int]) -> int:
    for candidate in range(7):
        if candidate not in days:
            return candidate
    raise AssertionError("all weekdays configured")


def _next_date_for_weekday(start: date, weekday: int) -> date:
    """First date on or after `start` (inclusive) matching `weekday`."""
    days_ahead = (weekday - start.weekday()) % 7
    return start + timedelta(days=days_ahead)


class TestEventSeriesServiceCRUD:
    """CRUD and 404 behaviour."""

    def test_create_series_defaults_start_date_to_today(self, db_session):
        et = make_event_type(db_session)
        user = make_user(db_session)
        db_session.commit()

        data = EventSeriesCreate(
            title="Aikido Geral",
            event_type_id=et.id,
            days_of_week=[0, 2, 5],
            start_time=time(7, 0),
        )
        series = EventSeriesService.create_series(db_session, data, created_by=user.id)
        assert series.id is not None
        assert series.days_of_week == "0,2,5"
        assert series.series_start_date == local_today()
        assert series.is_active is True
        assert series.check_in_token is not None

    def test_create_series_explicit_start_date(self, db_session):
        et = make_event_type(db_session)
        user = make_user(db_session)
        db_session.commit()

        explicit_start = local_today() + timedelta(days=10)
        data = EventSeriesCreate(
            title="Aikido Geral",
            event_type_id=et.id,
            days_of_week=[1],
            start_time=time(19, 0),
            series_start_date=explicit_start,
        )
        series = EventSeriesService.create_series(db_session, data, created_by=user.id)
        assert series.series_start_date == explicit_start

    def test_get_nonexistent_series_returns_none(self, db_session):
        assert EventSeriesService.get_series(db_session, "nonexistent") is None

    def test_update_nonexistent_series_404(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            EventSeriesService.update_series(db_session, "nonexistent", EventSeriesUpdate(title="Ghost"))
        assert exc_info.value.status_code == 404

    def test_generate_nonexistent_series_404(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            EventSeriesService.generate_occurrences(db_session, "nonexistent")
        assert exc_info.value.status_code == 404

    def test_deactivate_nonexistent_series_404(self, db_session):
        with pytest.raises(HTTPException) as exc_info:
            EventSeriesService.deactivate_series(db_session, "nonexistent")
        assert exc_info.value.status_code == 404

    def test_generate_occurrences_on_inactive_series_is_a_noop(self, db_session):
        series = make_event_series(db_session, days_of_week="0,1,2,3,4,5,6", is_active=False)
        db_session.commit()

        result = EventSeriesService.generate_occurrences(db_session, series.id)
        assert result["created_count"] == 0
        assert result["skipped_count"] == 0


class TestEventSeriesSchemaValidation:
    """Pydantic-level validation, mirrors EventCreate.validate_dates's existing style."""

    def test_days_of_week_empty_rejected(self):
        with pytest.raises(ValueError):
            EventSeriesCreate(title="X", event_type_id="et-1", days_of_week=[], start_time=time(7, 0))

    def test_days_of_week_out_of_range_rejected(self):
        with pytest.raises(ValueError):
            EventSeriesCreate(title="X", event_type_id="et-1", days_of_week=[7], start_time=time(7, 0))
        with pytest.raises(ValueError):
            EventSeriesCreate(title="X", event_type_id="et-1", days_of_week=[-1], start_time=time(7, 0))

    def test_series_end_date_before_start_date_rejected(self):
        with pytest.raises(ValueError):
            EventSeriesCreate(
                title="X",
                event_type_id="et-1",
                days_of_week=[0],
                start_time=time(7, 0),
                series_start_date=date(2026, 1, 10),
                series_end_date=date(2026, 1, 1),
            )

    def test_series_end_date_before_defaulted_start_date_rejected(self):
        """Omitting series_start_date must not bypass the end-before-start check --
        the effective start date defaults to today (see create_series), so a past
        series_end_date should still be rejected even when series_start_date is None.
        """
        with pytest.raises(ValueError):
            EventSeriesCreate(
                title="X",
                event_type_id="et-1",
                days_of_week=[0],
                start_time=time(7, 0),
                series_end_date=date(2020, 1, 1),
            )

    def test_duration_minutes_zero_rejected(self):
        with pytest.raises(ValueError):
            EventSeriesCreate(
                title="X",
                event_type_id="et-1",
                days_of_week=[0],
                start_time=time(7, 0),
                duration_minutes=0,
            )

    def test_duration_minutes_negative_rejected(self):
        with pytest.raises(ValueError):
            EventSeriesCreate(
                title="X",
                event_type_id="et-1",
                days_of_week=[0],
                start_time=time(7, 0),
                duration_minutes=-5,
            )

    def test_update_duration_minutes_zero_rejected(self):
        with pytest.raises(ValueError):
            EventSeriesUpdate(duration_minutes=0)

    def test_update_days_of_week_empty_rejected(self):
        with pytest.raises(ValueError):
            EventSeriesUpdate(days_of_week=[])

    def test_update_days_of_week_none_is_a_partial_update(self):
        update = EventSeriesUpdate(title="New Title")
        assert update.days_of_week is None


class TestEventSeriesFieldSnapshot:
    """RES-03 -- snapshot at generation time, not a live reference."""

    def test_snapshot_is_frozen_until_explicit_series_edit(self, db_session):
        today = local_today()
        series = make_event_series(
            db_session, title="Old Title", days_of_week=str(today.weekday()), series_start_date=today
        )
        db_session.commit()

        first_event, created = EventSeriesService._get_or_create_occurrence(db_session, series, today)
        assert created is True
        assert first_event.title == "Old Title"

        # Mutate the series directly, bypassing update_series -- isolates the
        # snapshot-at-generation-time claim from RES-05's automatic propagation.
        series.title = "New Title"
        db_session.commit()

        db_session.refresh(first_event)
        assert first_event.title == "Old Title"

        next_date = today + timedelta(days=7)
        second_event, created2 = EventSeriesService._get_or_create_occurrence(db_session, series, next_date)
        assert created2 is True
        assert second_event.title == "New Title"


class TestGenerateOccurrencesWindow:
    """RES-02 -- 365-day generation window mechanics."""

    def test_window_inclusive_of_today(self, db_session):
        today = local_today()
        series = make_event_series(db_session, days_of_week=str(today.weekday()), series_start_date=today)
        db_session.commit()

        EventSeriesService.generate_occurrences(db_session, series.id)

        created = db_session.query(Event).filter(Event.event_series_id == series.id).all()
        assert any(e.occurrence_date == today for e in created)

    def test_window_produces_exactly_365_candidate_dates_for_daily_series(self, db_session):
        series = make_event_series(db_session, days_of_week="0,1,2,3,4,5,6")
        db_session.commit()

        result = EventSeriesService.generate_occurrences(db_session, series.id)
        assert (result["window_end"] - result["window_start"]).days == 364
        assert result["created_count"] == 365

    def test_window_clipped_by_series_end_date(self, db_session):
        today = local_today()
        end_date = today + timedelta(days=10)
        series = make_event_series(
            db_session, days_of_week="0,1,2,3,4,5,6", series_start_date=today, series_end_date=end_date
        )
        db_session.commit()

        result = EventSeriesService.generate_occurrences(db_session, series.id)
        assert result["window_end"] == end_date

    def test_window_respects_future_series_start_date(self, db_session):
        today = local_today()
        future_start = today + timedelta(days=20)
        series = make_event_series(db_session, days_of_week="0,1,2,3,4,5,6", series_start_date=future_start)
        db_session.commit()

        EventSeriesService.generate_occurrences(db_session, series.id)
        earliest = (
            db_session.query(Event)
            .filter(Event.event_series_id == series.id)
            .order_by(Event.occurrence_date.asc())
            .first()
        )
        assert earliest.occurrence_date == future_start

    def test_non_matching_weekdays_produce_no_extra_rows(self, db_session):
        today = local_today()
        chosen_day = today.weekday()
        series = make_event_series(db_session, days_of_week=str(chosen_day), series_start_date=today)
        db_session.commit()

        EventSeriesService.generate_occurrences(db_session, series.id)

        created = db_session.query(Event).filter(Event.event_series_id == series.id).all()
        assert len(created) in (52, 53)
        assert all(e.occurrence_date.weekday() == chosen_day for e in created)

    def test_rerunning_generation_is_idempotent(self, db_session):
        today = local_today()
        series = make_event_series(db_session, days_of_week=str(today.weekday()), series_start_date=today)
        db_session.commit()

        first = EventSeriesService.generate_occurrences(db_session, series.id)
        assert first["created_count"] > 0
        count_after_first = db_session.query(Event).filter(Event.event_series_id == series.id).count()

        second = EventSeriesService.generate_occurrences(db_session, series.id)
        assert second["created_count"] == 0
        count_after_second = db_session.query(Event).filter(Event.event_series_id == series.id).count()
        assert count_after_second == count_after_first

    def test_full_window_commits_once_per_created_row(self, db_session):
        """Proves the per-row commit granularity decision actually delivers one
        commit per created row, even at the full 365-row worst-case scale.
        """
        series = make_event_series(db_session, days_of_week="0,1,2,3,4,5,6")
        db_session.commit()

        commit_calls = {"count": 0}
        original_commit = db_session.commit

        def counting_commit():
            commit_calls["count"] += 1
            original_commit()

        db_session.commit = counting_commit
        try:
            result = EventSeriesService.generate_occurrences(db_session, series.id)
        finally:
            db_session.commit = original_commit

        assert result["created_count"] == 365
        assert commit_calls["count"] == 365


class TestConcurrencySafeIdempotency:
    """RES-02/RES-04 -- never a duplicate Event for (event_series_id, occurrence_date)."""

    def test_unique_constraint_enforced_directly(self, db_session):
        et = make_event_type(db_session)
        user = make_user(db_session)
        series = make_event_series(db_session, event_type_id=et.id, created_by=user.id)
        db_session.commit()
        today = local_today()
        start_datetime = datetime.combine(today, series.start_time, tzinfo=APP_TIMEZONE)

        first = Event(
            title="A",
            event_type_id=et.id,
            start_datetime=start_datetime,
            event_series_id=series.id,
            occurrence_date=today,
            created_by=user.id,
            status="scheduled",
        )
        db_session.add(first)
        db_session.commit()

        second = Event(
            title="B",
            event_type_id=et.id,
            start_datetime=start_datetime,
            event_series_id=series.id,
            occurrence_date=today,
            created_by=user.id,
            status="scheduled",
        )
        db_session.add(second)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_get_or_create_occurrence_survives_simulated_race(self, db_session, db_engine):
        et = make_event_type(db_session)
        user = make_user(db_session)
        series = make_event_series(db_session, event_type_id=et.id, created_by=user.id)
        db_session.commit()
        today = local_today()

        competitor_session = sessionmaker(bind=db_engine)()
        competitor = Event(
            title="Competitor",
            event_type_id=et.id,
            start_datetime=datetime.combine(today, series.start_time, tzinfo=APP_TIMEZONE),
            event_series_id=series.id,
            occurrence_date=today,
            created_by=user.id,
            status="scheduled",
        )

        original_commit = db_session.commit

        def racing_commit():
            # Simulate a concurrent request winning the race between our own
            # existing-row check and our own commit.
            competitor_session.add(competitor)
            competitor_session.commit()
            original_commit()

        db_session.commit = racing_commit
        try:
            event, created = EventSeriesService._get_or_create_occurrence(db_session, series, today)
        finally:
            db_session.commit = original_commit

        assert created is False
        assert event.id == competitor.id
        count = (
            db_session.query(Event).filter(Event.event_series_id == series.id, Event.occurrence_date == today).count()
        )
        assert count == 1
        competitor_session.close()

    def test_resolve_today_occurrence_survives_simulated_race(self, db_session, db_engine):
        today = local_today()
        et = make_event_type(db_session)
        user = make_user(db_session)
        series = make_event_series(
            db_session,
            event_type_id=et.id,
            created_by=user.id,
            days_of_week=str(today.weekday()),
            series_start_date=today,
        )
        db_session.commit()

        competitor_session = sessionmaker(bind=db_engine)()
        competitor = Event(
            title="Competitor",
            event_type_id=et.id,
            start_datetime=datetime.combine(today, series.start_time, tzinfo=APP_TIMEZONE),
            event_series_id=series.id,
            occurrence_date=today,
            created_by=user.id,
            status="scheduled",
        )

        original_commit = db_session.commit

        def racing_commit():
            competitor_session.add(competitor)
            competitor_session.commit()
            original_commit()

        db_session.commit = racing_commit
        try:
            resolved = EventSeriesService.resolve_today_occurrence(db_session, series)
        finally:
            db_session.commit = original_commit

        assert resolved.id == competitor.id
        count = (
            db_session.query(Event).filter(Event.event_series_id == series.id, Event.occurrence_date == today).count()
        )
        assert count == 1
        competitor_session.close()


class TestResolveTodayOccurrence:
    """RES-04's four enumerated edge cases."""

    def test_existing_row_wins_regardless_of_status(self, db_session):
        today = local_today()
        et = make_event_type(db_session)
        user = make_user(db_session)
        series = make_event_series(
            db_session,
            event_type_id=et.id,
            created_by=user.id,
            days_of_week=str(today.weekday()),
            series_start_date=today,
        )
        db_session.commit()
        existing = make_event(
            db_session,
            event_type_id=et.id,
            created_by=user.id,
            event_series_id=series.id,
            occurrence_date=today,
            start_datetime=datetime.combine(today, series.start_time, tzinfo=APP_TIMEZONE),
            status="cancelled",
        )
        db_session.commit()

        result = EventSeriesService.resolve_today_occurrence(db_session, series)
        assert result.id == existing.id
        assert result.status == "cancelled"
        count = db_session.query(Event).filter(Event.event_series_id == series.id).count()
        assert count == 1

    def test_lazy_creates_exactly_one_when_scheduled(self, db_session):
        today = local_today()
        series = make_event_series(db_session, days_of_week=str(today.weekday()), series_start_date=today)
        db_session.commit()

        result = EventSeriesService.resolve_today_occurrence(db_session, series)
        assert result.occurrence_date == today
        assert result.event_series_id == series.id
        count = db_session.query(Event).filter(Event.event_series_id == series.id).count()
        assert count == 1

    def test_rejects_non_scheduled_weekday(self, db_session):
        today = local_today()
        series = make_event_series(
            db_session, days_of_week=str(_weekday_not_in({today.weekday()})), series_start_date=today
        )
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            EventSeriesService.resolve_today_occurrence(db_session, series)
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "No occurrence scheduled today for this series"
        assert db_session.query(Event).filter(Event.event_series_id == series.id).count() == 0

    def test_rejects_inactive_series(self, db_session):
        today = local_today()
        series = make_event_series(
            db_session, days_of_week=str(today.weekday()), series_start_date=today, is_active=False
        )
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            EventSeriesService.resolve_today_occurrence(db_session, series)
        assert exc_info.value.status_code == 400

    def test_rejects_before_series_start_date(self, db_session):
        today = local_today()
        series = make_event_series(
            db_session, days_of_week=str(today.weekday()), series_start_date=today + timedelta(days=1)
        )
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            EventSeriesService.resolve_today_occurrence(db_session, series)
        assert exc_info.value.status_code == 400

    def test_rejects_after_series_end_date(self, db_session):
        today = local_today()
        series = make_event_series(
            db_session,
            days_of_week=str(today.weekday()),
            series_start_date=today - timedelta(days=10),
            series_end_date=today - timedelta(days=1),
        )
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            EventSeriesService.resolve_today_occurrence(db_session, series)
        assert exc_info.value.status_code == 400

    def test_resolved_cancelled_occurrence_then_check_in_rejected(self, db_session):
        today = local_today()
        et = make_event_type(db_session)
        user = make_user(db_session)
        series = make_event_series(
            db_session,
            event_type_id=et.id,
            created_by=user.id,
            days_of_week=str(today.weekday()),
            series_start_date=today,
        )
        db_session.commit()
        make_event(
            db_session,
            event_type_id=et.id,
            created_by=user.id,
            event_series_id=series.id,
            occurrence_date=today,
            start_datetime=datetime.combine(today, series.start_time, tzinfo=APP_TIMEZONE),
            status="cancelled",
        )
        db_session.commit()

        resolved = EventSeriesService.resolve_today_occurrence(db_session, series)
        assert resolved.status == "cancelled"

        with pytest.raises(HTTPException) as exc_info:
            AttendanceService.check_in(db_session, CheckInRequest(registration_number="none", pin="1234"), resolved.id)
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Event is cancelled"


class TestReconcileFutureOccurrences:
    """RES-05's amended propagation rule (Case A / Case B / reactivation) and RES-06's cascade."""

    def test_case_a_syncs_fields_and_recomputes_datetimes(self, db_session):
        et = make_event_type(db_session)
        et2 = make_event_type(db_session, name="New Type")
        belt = make_belt(db_session)
        user = make_user(db_session)
        new_dojo = make_dojo(db_session, name="New Dojo")
        db_session.commit()

        today = local_today()
        future_date = today + timedelta(days=7)
        series = make_event_series(
            db_session,
            event_type_id=et.id,
            created_by=user.id,
            days_of_week=str(future_date.weekday()),
            start_time=time(7, 0),
            duration_minutes=60,
            series_start_date=today,
        )
        db_session.commit()

        future_event, _ = EventSeriesService._get_or_create_occurrence(db_session, series, future_date)
        past_event = make_event(
            db_session,
            event_type_id=et.id,
            created_by=user.id,
            event_series_id=series.id,
            occurrence_date=today - timedelta(days=7),
            start_datetime=datetime.now(UTC) - timedelta(days=7),
            title="Old Past Title",
        )
        db_session.commit()

        EventSeriesService.update_series(
            db_session,
            series.id,
            EventSeriesUpdate(
                title="New Title",
                event_type_id=et2.id,
                dojo_id=new_dojo.id,
                minimum_belt_id=belt.id,
                start_time=time(19, 30),
                duration_minutes=90,
            ),
        )

        db_session.refresh(future_event)
        assert future_event.title == "New Title"
        assert future_event.event_type_id == et2.id
        assert future_event.location == "New Dojo"
        assert future_event.minimum_belt_id == belt.id
        expected_start = datetime.combine(future_date, time(19, 30), tzinfo=APP_TIMEZONE).replace(tzinfo=None)
        assert future_event.start_datetime == expected_start
        assert future_event.end_datetime == expected_start + timedelta(minutes=90)
        assert future_event.status == "scheduled"

        db_session.refresh(past_event)
        assert past_event.title == "Old Past Title"

    def test_case_b_cancels_occurrence_on_removed_weekday_and_cascades_pre_checkins(self, db_session):
        et = make_event_type(db_session)
        user = make_user(db_session)
        db_session.commit()

        today = local_today()
        day_a = today.weekday()
        day_b = (day_a + 1) % 7
        series = make_event_series(
            db_session,
            event_type_id=et.id,
            created_by=user.id,
            days_of_week=f"{day_a},{day_b}",
            series_start_date=today,
        )
        db_session.commit()

        date_a = _next_date_for_weekday(today + timedelta(days=1), day_a)
        date_b = _next_date_for_weekday(today + timedelta(days=1), day_b)
        event_a, _ = EventSeriesService._get_or_create_occurrence(db_session, series, date_a)
        event_b, _ = EventSeriesService._get_or_create_occurrence(db_session, series, date_b)

        student = make_student(db_session)
        db_session.commit()
        pre_checkin = PreCheckIn(event_id=event_b.id, student_id=student.id, status="confirmed")
        db_session.add(pre_checkin)
        db_session.commit()

        EventSeriesService.update_series(db_session, series.id, EventSeriesUpdate(days_of_week=[day_a]))

        db_session.refresh(event_b)
        assert event_b.status == "cancelled"
        db_session.refresh(pre_checkin)
        assert pre_checkin.status == "cancelled"
        assert pre_checkin.cancelled_at is not None

        db_session.refresh(event_a)
        assert event_a.status == "scheduled"

    def test_combined_rule_shortened_end_date_cancels_out_of_range_occurrence(self, db_session):
        today = local_today()
        future_date = today + timedelta(days=30)
        series = make_event_series(db_session, days_of_week=str(future_date.weekday()), series_start_date=today)
        db_session.commit()
        event, _ = EventSeriesService._get_or_create_occurrence(db_session, series, future_date)

        EventSeriesService.update_series(
            db_session, series.id, EventSeriesUpdate(series_end_date=today + timedelta(days=10))
        )

        db_session.refresh(event)
        assert event.status == "cancelled"

    def test_reactivation_of_re_added_weekday_syncs_fields_but_not_pre_checkins(self, db_session):
        today = local_today()
        day_a = today.weekday()
        day_b = (day_a + 1) % 7
        series = make_event_series(db_session, days_of_week=f"{day_a},{day_b}", series_start_date=today)
        db_session.commit()

        date_b = _next_date_for_weekday(today + timedelta(days=1), day_b)
        event_b, _ = EventSeriesService._get_or_create_occurrence(db_session, series, date_b)

        student = make_student(db_session)
        db_session.commit()
        pre_checkin = PreCheckIn(event_id=event_b.id, student_id=student.id, status="confirmed")
        db_session.add(pre_checkin)
        db_session.commit()

        EventSeriesService.update_series(db_session, series.id, EventSeriesUpdate(days_of_week=[day_a]))
        db_session.refresh(event_b)
        assert event_b.status == "cancelled"

        EventSeriesService.update_series(
            db_session, series.id, EventSeriesUpdate(title="Updated Title", days_of_week=[day_a, day_b])
        )
        db_session.refresh(event_b)
        assert event_b.status == "scheduled"
        assert event_b.title == "Updated Title"

        db_session.refresh(pre_checkin)
        assert pre_checkin.status == "cancelled"

    def test_reactivation_via_whole_series_deactivate_then_reactivate(self, db_session):
        today = local_today()
        future_date = today + timedelta(days=7)
        series = make_event_series(db_session, days_of_week=str(future_date.weekday()), series_start_date=today)
        db_session.commit()
        event, _ = EventSeriesService._get_or_create_occurrence(db_session, series, future_date)

        EventSeriesService.deactivate_series(db_session, series.id)
        db_session.refresh(event)
        assert event.status == "cancelled"
        db_session.refresh(series)
        assert series.is_active is False

        EventSeriesService.update_series(db_session, series.id, EventSeriesUpdate(is_active=True))
        db_session.refresh(event)
        assert event.status == "scheduled"

    def test_reconciliation_with_no_field_changes_is_idempotent(self, db_session):
        today = local_today()
        future_date = today + timedelta(days=7)
        series = make_event_series(db_session, days_of_week=str(future_date.weekday()), series_start_date=today)
        db_session.commit()
        event, _ = EventSeriesService._get_or_create_occurrence(db_session, series, future_date)

        EventSeriesService.update_series(db_session, series.id, EventSeriesUpdate())
        db_session.refresh(event)
        assert event.status == "scheduled"

        EventSeriesService.update_series(db_session, series.id, EventSeriesUpdate())
        db_session.refresh(event)
        assert event.status == "scheduled"


class TestTimezoneBoundary:
    """RES-02/RES-04 -- 'today' is the America/Sao_Paulo wall-clock date, not raw UTC."""

    def test_generate_and_resolve_use_sao_paulo_date_not_utc(self, db_session, monkeypatch):
        # 2026-03-10 02:30 UTC is 2026-03-09 23:30 in America/Sao_Paulo (UTC-3) --
        # a different calendar date AND a different weekday (Tue vs Mon), so a
        # regression to bare UTC would make this test fail, not pass by luck.
        fixed_utc = datetime(2026, 3, 10, 2, 30, tzinfo=UTC)
        fixed_local = fixed_utc.astimezone(APP_TIMEZONE)
        expected_today = fixed_local.date()
        assert expected_today != fixed_utc.date()

        monkeypatch.setattr(event_series_service_module, "local_now", lambda: fixed_local)
        monkeypatch.setattr(event_series_service_module, "local_today", lambda: expected_today)

        series = make_event_series(
            db_session, days_of_week=str(expected_today.weekday()), series_start_date=expected_today
        )
        db_session.commit()

        result = EventSeriesService.generate_occurrences(db_session, series.id, window_days=1)
        assert result["window_start"] == expected_today
        assert result["created_count"] == 1

        created_event = db_session.query(Event).filter(Event.event_series_id == series.id).first()
        assert created_event.occurrence_date == expected_today

        resolved = EventSeriesService.resolve_today_occurrence(db_session, series)
        assert resolved.id == created_event.id
