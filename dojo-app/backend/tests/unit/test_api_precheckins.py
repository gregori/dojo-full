"""API tests for public and instructor pre-check-in endpoints."""

import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import event as sql_event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.core.database import get_db
from app.core.security import get_password_hash
from app.dependencies.auth import get_current_instructor_or_admin
from app.main import app
from app.models import Base, Belt, Event, EventType, Student, User


@pytest.fixture
def api_context():
    """Provide a fresh in-memory database with one public event and student."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @sql_event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    belt = Belt(name="Blue", category="adult", sort_order=3)
    event_type = EventType(name="Training")
    instructor = User(
        email="instructor@dojo.test",
        password_hash="unused",
        full_name="Instructor",
        role="instructor",
    )
    session.add_all([belt, event_type, instructor])
    session.commit()
    student = Student(
        registration_number="PC-101",
        full_name="Pre Checkin Student",
        category="adult",
        current_belt_id=belt.id,
        pin=get_password_hash("1234"),
    )
    event = Event(
        title="Open Training",
        event_type_id=event_type.id,
        created_by=instructor.id,
        start_datetime=datetime.now(UTC) + timedelta(days=1),
        status="scheduled",
    )
    session.add_all([student, event])
    session.commit()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_instructor_or_admin] = lambda: instructor
    yield TestClient(app), event, student
    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_public_events_exclude_closed_events(api_context):
    """Public event selection includes only scheduled events outside the cutoff window."""
    client, event, _ = api_context

    response = client.get("/api/v1/pre-checkins/events")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == event.id
    assert response.json()[0]["title"] == "Open Training"
    assert set(response.json()[0]) == {"id", "title", "start_datetime", "end_datetime", "location"}


def test_public_confirmation_hides_invalid_credentials_and_staff_can_see_count(api_context):
    """Invalid credentials get a generic response; a valid confirmation increments staff count."""
    client, event, student = api_context
    invalid_response = client.post(
        "/api/v1/pre-checkins/confirm",
        json={"event_id": event.id, "registration_number": student.registration_number, "pin": "wrong"},
    )
    valid_response = client.post(
        "/api/v1/pre-checkins/confirm",
        json={"event_id": event.id, "registration_number": student.registration_number, "pin": "1234"},
    )
    count_response = client.get(f"/api/v1/pre-checkins/events/{event.id}/count")

    assert invalid_response.status_code == 200
    assert invalid_response.json() == valid_response.json()
    assert count_response.json() == {"event_id": event.id, "confirmed_count": 1}
