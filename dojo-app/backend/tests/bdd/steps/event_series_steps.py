"""Step definitions for the recurring event-series check-in feature.

Days-of-week are computed relative to the real current date at scenario
run-time (never hardcoded literals), mirroring how checkin.feature's own
steps avoid hardcoding dates -- no time-freezing needed for this suite.
"""

from behave import given, then, when

from app.core.security import get_password_hash
from app.core.timezone import local_today
from app.models import Belt, Event, EventType, Student, User
from app.schemas import EventSeriesCreate
from app.services.event_series_service import EventSeriesService


def _ensure_user(db):
    user = db.query(User).first()
    if not user:
        user = User(
            email="test@dojo.com",
            password_hash=get_password_hash("test123"),
            full_name="Test User",
            role="admin",
        )
        db.add(user)
        db.commit()
    return user


@given('a recurring event series "{title}" scheduled today at "{start_time}"')
def step_series_scheduled_today(context, title, start_time):
    db = context.db
    event_type = context.current_event_type or db.query(EventType).first()
    user = _ensure_user(db)
    today = local_today()

    data = EventSeriesCreate(
        title=title,
        event_type_id=event_type.id,
        days_of_week=[today.weekday()],
        start_time=f"{start_time}:00",
        series_start_date=today,
    )
    series = EventSeriesService.create_series(db, data, created_by=user.id)
    context.current_series = series
    context.current_series_token = series.check_in_token


@given('a recurring event series "{title}" not scheduled today')
def step_series_not_scheduled_today(context, title):
    db = context.db
    event_type = context.current_event_type or db.query(EventType).first()
    user = _ensure_user(db)
    today = local_today()
    not_today = (today.weekday() + 1) % 7

    data = EventSeriesCreate(
        title=title,
        event_type_id=event_type.id,
        days_of_week=[not_today],
        start_time="07:00:00",
        series_start_date=today,
    )
    series = EventSeriesService.create_series(db, data, created_by=user.id)
    context.current_series = series
    context.current_series_token = series.check_in_token


@given("the series QR has already been scanned once today by another student")
def step_series_already_scanned(context):
    db = context.db
    belt = context.current_belt or db.query(Belt).first()

    other_student = Student(
        full_name="Maria Souza",
        registration_number="2024899",
        pin=get_password_hash("9999"),
        category="adult",
        current_belt_id=belt.id if belt else None,
    )
    db.add(other_student)
    db.commit()

    EventSeriesService.resolve_today_occurrence(db, context.current_series)

    context.response = context.client.post(
        "/api/v1/checkin/qr",
        json={
            "registration_number": "2024899",
            "pin": "9999",
            "check_in_token": context.current_series_token,
        },
    )


@given("today's occurrence for the series has been cancelled")
def step_series_occurrence_cancelled(context):
    db = context.db
    occurrence = EventSeriesService.resolve_today_occurrence(db, context.current_series)
    occurrence.status = "cancelled"
    db.commit()


@when("the student checks in via the series QR code with:")
def step_student_checks_in_series_qr(context):
    data = {row["field"]: row["value"] for row in context.table}
    data["check_in_token"] = context.current_series_token
    context.response = context.client.post("/api/v1/checkin/qr", json=data)


@then("exactly one event occurrence should exist for the series today")
def step_exactly_one_occurrence_today(context):
    db = context.db
    today = local_today()
    count = (
        db.query(Event)
        .filter(Event.event_series_id == context.current_series.id, Event.occurrence_date == today)
        .count()
    )
    assert count == 1, f"Expected exactly one occurrence for today, found {count}"
