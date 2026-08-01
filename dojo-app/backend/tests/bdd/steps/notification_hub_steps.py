"""Step definitions for the Notification Hub end-to-end trigger-to-history feature."""

from datetime import datetime, time

from behave import given, then, when

from app.core.security import get_password_hash
from app.core.timezone import APP_TIMEZONE, local_today
from app.models import Belt, Event, EventType, Notification, Student, User
from app.services.notification_trigger_service import PRE_CHECKIN_LEAD, NotificationTriggerService


def _ensure_user(db):
    user = db.query(User).first()
    if not user:
        user = User(
            email="notif-test@dojo.com",
            password_hash=get_password_hash("test123"),
            full_name="Test User",
            role="admin",
        )
        db.add(user)
        db.commit()
    return user


@given('an active student "{name}" eligible for all events')
def step_active_student_eligible_for_all_events(context, name):
    db = context.db
    belt = Belt(name=f"Belt for {name}", category="adult", sort_order=1)
    db.add(belt)
    db.commit()

    student = Student(
        full_name=name,
        registration_number="NHUB-001",
        pin=get_password_hash("1234"),
        category="adult",
        current_belt_id=belt.id,
        is_active=True,
    )
    db.add(student)
    db.commit()

    context.current_student = student
    context.current_student_credentials = {"registration_number": student.registration_number, "pin": "1234"}


@given('an event "{title}" starting in exactly 1 day')
def step_event_starting_in_exactly_one_day(context, title):
    db = context.db
    event_type = db.query(EventType).first()
    if not event_type:
        event_type = EventType(name="Aula Regular", color="#3498db", counts_for_belt=True)
        db.add(event_type)
        db.commit()
    user = _ensure_user(db)

    start_datetime = datetime.combine(local_today() + PRE_CHECKIN_LEAD, time(10, 0), tzinfo=APP_TIMEZONE)
    event = Event(
        title=title,
        event_type_id=event_type.id,
        start_datetime=start_datetime,
        created_by=user.id,
        status="scheduled",
    )
    db.add(event)
    db.commit()
    context.current_event = event


@when("the daily notification check runs")
def step_notification_check_runs(context):
    NotificationTriggerService.check_pre_checkin_reminders(context.db)


@when("the daily notification check runs twice")
def step_notification_check_runs_twice(context):
    NotificationTriggerService.check_pre_checkin_reminders(context.db)
    NotificationTriggerService.check_pre_checkin_reminders(context.db)


@then('exactly one notification of type "{notification_type}" exists for the student')
def step_exactly_one_notification_of_type(context, notification_type):
    db = context.db
    count = (
        db.query(Notification)
        .filter(
            Notification.student_id == context.current_student.id,
            Notification.notification_type == notification_type,
        )
        .count()
    )
    assert count == 1, f"Expected exactly one {notification_type} notification, found {count}"


@when("the student views their notification history with valid credentials")
def step_student_views_history(context):
    context.response = context.client.post("/api/v1/notifications/history", json=context.current_student_credentials)


@then('the response includes a notification referencing "{title}"')
def step_response_includes_notification_referencing(context, title):
    data = context.response.json()
    assert any(title in item["message"] for item in data), f"No notification referencing '{title}' in {data}"
