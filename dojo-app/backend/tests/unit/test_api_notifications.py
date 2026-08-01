"""API tests for public notification-hub endpoints."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import event as sql_event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.api.notifications import notification_rate_limiter
from app.core.database import get_db
from app.core.security import get_password_hash
from app.main import app
from app.models import Base, Belt, Notification, Student


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Isolate rate-limit state between tests, since the limiter is a module-level singleton."""
    notification_rate_limiter._attempts.clear()
    yield
    notification_rate_limiter._attempts.clear()


@pytest.fixture
def api_context():
    """Provide a fresh in-memory database with two active students."""
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
    session.add(belt)
    session.commit()
    student = Student(
        registration_number="NOTIF-101",
        full_name="Notification Student",
        category="adult",
        current_belt_id=belt.id,
        pin=get_password_hash("1234"),
    )
    other_student = Student(
        registration_number="NOTIF-102",
        full_name="Other Student",
        category="adult",
        current_belt_id=belt.id,
        pin=get_password_hash("5678"),
    )
    session.add_all([student, other_student])
    session.commit()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app), session, student, other_student
    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def _credentials(student, pin):
    return {"registration_number": student.registration_number, "pin": pin}


def test_subscribe_with_valid_credentials_creates_row(api_context):
    """A valid subscribe request creates a PushSubscription and returns 201."""
    client, _session, student, _other = api_context

    response = client.post(
        "/api/v1/notifications/subscribe",
        json={
            **_credentials(student, "1234"),
            "endpoint": "https://push.example.com/endpoint",
            "keys": {"p256dh": "p256dh-value", "auth": "auth-value"},
        },
    )

    assert response.status_code == 201
    assert response.json() == {"status": "subscribed"}


def test_subscribe_with_invalid_credentials_returns_401(api_context):
    """Invalid credentials get a real, distinguishable 401 (NH-01's divergence, see plan.md)."""
    client, _session, student, _other = api_context

    response = client.post(
        "/api/v1/notifications/subscribe",
        json={
            **_credentials(student, "wrong"),
            "endpoint": "https://push.example.com/endpoint",
            "keys": {"p256dh": "p256dh-value", "auth": "auth-value"},
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Matrícula ou PIN inválidos."


def test_history_returns_students_own_notifications(api_context):
    """A student's history request returns only their own notifications."""
    client, session, student, other_student = api_context
    session.add_all(
        [
            Notification(
                student_id=student.id,
                notification_type="pre_checkin_reminder",
                reference_id="ref-1",
                message="Your reminder",
            ),
            Notification(
                student_id=other_student.id,
                notification_type="pre_checkin_reminder",
                reference_id="ref-2",
                message="Someone else's reminder",
            ),
        ]
    )
    session.commit()

    response = client.post("/api/v1/notifications/history", json=_credentials(student, "1234"))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["message"] == "Your reminder"


def test_history_with_invalid_credentials_returns_401(api_context):
    client, _session, student, _other = api_context

    response = client.post("/api/v1/notifications/history", json=_credentials(student, "wrong"))

    assert response.status_code == 401


def test_mark_read_sets_read_at_for_own_notification(api_context):
    client, session, student, _other = api_context
    notification = Notification(
        student_id=student.id,
        notification_type="pre_checkin_reminder",
        reference_id="ref-1",
        message="Your reminder",
    )
    session.add(notification)
    session.commit()

    response = client.post(f"/api/v1/notifications/{notification.id}/read", json=_credentials(student, "1234"))

    assert response.status_code == 200
    assert response.json()["read_at"] is not None


def test_mark_read_for_another_students_notification_returns_404(api_context):
    client, session, student, other_student = api_context
    notification = Notification(
        student_id=other_student.id,
        notification_type="pre_checkin_reminder",
        reference_id="ref-1",
        message="Not yours",
    )
    session.add(notification)
    session.commit()

    response = client.post(f"/api/v1/notifications/{notification.id}/read", json=_credentials(student, "1234"))

    assert response.status_code == 404


def test_mark_read_with_invalid_credentials_returns_401(api_context):
    client, session, student, _other = api_context
    notification = Notification(
        student_id=student.id,
        notification_type="pre_checkin_reminder",
        reference_id="ref-1",
        message="Your reminder",
    )
    session.add(notification)
    session.commit()

    response = client.post(f"/api/v1/notifications/{notification.id}/read", json=_credentials(student, "wrong"))

    assert response.status_code == 401


def test_get_vapid_public_key_requires_no_auth(api_context):
    client, _session, _student, _other = api_context

    response = client.get("/api/v1/notifications/vapid-public-key")

    assert response.status_code == 200
    assert "public_key" in response.json()


def test_rate_limited_after_repeated_invalid_attempts(api_context):
    """After the configured attempt threshold, further requests are rejected with 429."""
    client, _session, student, _other = api_context

    responses = [
        client.post("/api/v1/notifications/history", json=_credentials(student, "wrong"))
        for _ in range(notification_rate_limiter.max_attempts + 1)
    ]

    assert [r.status_code for r in responses[:-1]] == [401] * notification_rate_limiter.max_attempts
    assert responses[-1].status_code == 429
