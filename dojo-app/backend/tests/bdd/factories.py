"""Factory Boy models for BDD test data generation.

Usage in step definitions:
    from tests.bdd.factories import UserFactory, StudentFactory, BeltFactory

    # Set the session before using factories
    from factory.alchemy import SQLAlchemyModelFactory
    from app.models import Session

    # In a step:
    user = UserFactory(email="test@dojo.com", role="admin")
"""

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.core.security import get_password_hash
from app.core.timezone import local_today
from app.models import Belt, Event, EventSeries, EventType, Exam, Notification, PushSubscription, Student, User


class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@dojo.com")
    password_hash = factory.LazyFunction(lambda: get_password_hash("test123"))
    full_name = factory.Sequence(lambda n: f"Test User {n}")
    role = "admin"
    is_active = True


class BeltFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Belt

    name = factory.Sequence(lambda n: f"Belt {n}")
    category = "adult"
    sort_order = factory.Sequence(lambda n: n)


class EventTypeFactory(SQLAlchemyModelFactory):
    class Meta:
        model = EventType

    name = factory.Sequence(lambda n: f"Event Type {n}")
    color = "#3498db"
    counts_for_belt = True


class StudentFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Student

    full_name = factory.Sequence(lambda n: f"Student {n}")
    registration_number = factory.Sequence(lambda n: f"2024{n:03d}")
    pin = factory.LazyFunction(lambda: get_password_hash("1234"))
    category = "adult"
    is_active = True
    current_belt_id = factory.LazyAttribute(lambda _: BeltFactory().id)


class EventFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Event

    title = factory.Sequence(lambda n: f"Event {n}")
    event_type_id = factory.LazyAttribute(lambda _: EventTypeFactory().id)
    start_datetime = factory.LazyFunction(
        lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    )
    created_by = factory.LazyAttribute(lambda _: UserFactory().id)
    check_in_token = factory.LazyFunction(lambda: str(__import__("uuid").uuid4()))
    status = "scheduled"


class EventSeriesFactory(SQLAlchemyModelFactory):
    class Meta:
        model = EventSeries

    title = factory.Sequence(lambda n: f"Event Series {n}")
    event_type_id = factory.LazyAttribute(lambda _: EventTypeFactory().id)
    days_of_week = "0,2,5"
    start_time = __import__("datetime").time(7, 0)
    series_start_date = factory.LazyFunction(local_today)
    is_active = True
    created_by = factory.LazyAttribute(lambda _: UserFactory().id)
    check_in_token = factory.LazyFunction(lambda: str(__import__("uuid").uuid4()))


class ExamFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Exam

    event_id = factory.LazyAttribute(lambda _: EventFactory().id)
    belt_id = factory.LazyAttribute(lambda _: BeltFactory().id)
    exam_date = factory.LazyFunction(lambda: __import__("datetime").datetime.now(__import__("datetime").timezone.utc))
    status = "scheduled"
    notes = ""
    created_by = factory.LazyAttribute(lambda _: UserFactory().id)


class NotificationFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Notification

    student_id = factory.LazyAttribute(lambda _: StudentFactory().id)
    notification_type = "pre_checkin_reminder"
    reference_id = factory.Sequence(lambda n: f"ref-{n}")
    message = factory.Sequence(lambda n: f"Notification message {n}")


class PushSubscriptionFactory(SQLAlchemyModelFactory):
    class Meta:
        model = PushSubscription

    student_id = factory.LazyAttribute(lambda _: StudentFactory().id)
    endpoint = factory.Sequence(lambda n: f"https://push.example.com/endpoint/{n}")
    p256dh_key = factory.Sequence(lambda n: f"p256dh-{n}")
    auth_key = factory.Sequence(lambda n: f"auth-{n}")
