"""Unit tests for the pre-check-in lifecycle and attendance conversion."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.security import get_password_hash
from app.models import Attendance, Belt, Event, EventType, PreCheckIn, Student, User
from app.schemas import CheckInRequest, EventUpdate
from app.services import AttendanceService, EventService, PreCheckInService


@pytest.fixture
def pre_checkin_context(db_session):
    """Create an eligible student and an open event."""
    belt = Belt(name="Blue", category="adult", sort_order=3)
    event_type = EventType(name="Training")
    user = User(email="instructor@example.com", password_hash="unused", full_name="Instructor", role="instructor")
    db_session.add_all([belt, event_type, user])
    db_session.commit()

    student = Student(
        registration_number="A-123",
        full_name="Student One",
        category="adult",
        current_belt_id=belt.id,
        pin=get_password_hash("1234"),
    )
    event = Event(
        title="Open Training",
        event_type_id=event_type.id,
        created_by=user.id,
        start_datetime=datetime.now(UTC) + timedelta(days=1),
        status="scheduled",
        minimum_belt_id=belt.id,
    )
    db_session.add_all([student, event])
    db_session.commit()
    db_session.refresh(student)
    db_session.refresh(event)
    return student, event


def test_confirm_cancel_and_reconfirm_reuses_single_record(db_session, pre_checkin_context):
    """The lifecycle keeps one student/event record and permits reconfirmation before cutoff."""
    student, event = pre_checkin_context

    confirmed = PreCheckInService.confirm(db_session, event.id, student)
    cancelled = PreCheckInService.cancel(db_session, event.id, student)
    reconfirmed = PreCheckInService.confirm(db_session, event.id, student)

    assert confirmed.id == cancelled.id == reconfirmed.id
    assert reconfirmed.status == "confirmed"
    assert db_session.query(PreCheckIn).count() == 1


def test_confirm_is_rejected_at_one_hour_cutoff(db_session, pre_checkin_context):
    """Public confirmation is unavailable from exactly one hour before the event."""
    student, event = pre_checkin_context
    event.start_datetime = datetime.now(UTC) + timedelta(hours=1)
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        PreCheckInService.confirm(db_session, event.id, student)

    assert exc_info.value.status_code == 400


def test_physical_attendance_converts_confirmed_pre_checkin(db_session, pre_checkin_context):
    """Physical check-in remains attendance and converts only the prior confirmation."""
    student, event = pre_checkin_context
    PreCheckInService.confirm(db_session, event.id, student)

    attendance = AttendanceService.check_in(
        db_session,
        CheckInRequest(registration_number=student.registration_number, pin="1234", check_in_method="tablet"),
        event.id,
    )
    record = db_session.query(PreCheckIn).one()

    assert attendance.check_in_method == "tablet"
    assert record.status == "converted"
    assert record.converted_at is not None


def test_second_physical_attendance_is_rejected_by_unique_constraint(db_session, pre_checkin_context):
    """The database constraint prevents duplicate attendance writes."""
    student, event = pre_checkin_context
    request = CheckInRequest(registration_number=student.registration_number, pin="1234", check_in_method="tablet")
    AttendanceService.check_in(db_session, request, event.id)
    db_session.add(Attendance(event_id=event.id, student_id=student.id, check_in_method="tablet"))

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_confirm_rejects_student_below_event_minimum_belt(db_session, pre_checkin_context):
    """Configured event belt thresholds are enforced before a confirmation is recorded."""
    student, event = pre_checkin_context
    higher_belt = Belt(name="Purple", category="adult", sort_order=5)
    db_session.add(higher_belt)
    db_session.commit()
    event.minimum_belt_id = higher_belt.id
    db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        PreCheckInService.confirm(db_session, event.id, student)

    assert exc_info.value.status_code == 403


def test_reschedule_into_cutoff_invalidates_confirmation(db_session, pre_checkin_context):
    """Rescheduling into the cutoff cancels confirmations so a new action is required."""
    student, event = pre_checkin_context
    PreCheckInService.confirm(db_session, event.id, student)

    EventService.update_event(
        db_session,
        event.id,
        EventUpdate(start_datetime=datetime.now(UTC) + timedelta(minutes=30)),
    )

    assert db_session.query(PreCheckIn).one().status == "cancelled"
