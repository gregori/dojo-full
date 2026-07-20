"""API tests for public and instructor medical-exam endpoints."""

import io
import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.core.database import get_db
from app.core.rate_limiter import medical_exam_rate_limiter
from app.core.security import get_password_hash
from app.dependencies.auth import get_current_instructor_or_admin
from app.main import app
from app.models import Base, Belt, Student, User


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Isolate rate-limit state between tests, since the limiter is a module-level singleton."""
    medical_exam_rate_limiter._attempts.clear()
    yield
    medical_exam_rate_limiter._attempts.clear()


@pytest.fixture
def api_context():
    """Provide a fresh in-memory database with one active student and instructor."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    belt = Belt(name="Blue", category="adult", sort_order=3)
    instructor = User(
        email="instructor@dojo.test",
        password_hash="unused",
        full_name="Instructor",
        role="instructor",
    )
    session.add_all([belt, instructor])
    session.commit()
    student = Student(
        registration_number="MED-101",
        full_name="Medical Exam Student",
        category="adult",
        current_belt_id=belt.id,
        pin=get_password_hash("1234"),
    )
    session.add(student)
    session.commit()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_instructor_or_admin] = lambda: instructor
    yield TestClient(app), student, instructor
    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


def _pdf_file():
    return {"file": ("exam.pdf", io.BytesIO(b"%PDF-1.4 pdf-bytes"), "application/pdf")}


def test_public_submission_hides_invalid_credentials(api_context, monkeypatch):
    """Invalid credentials get the same generic response as valid ones."""
    monkeypatch.setattr("app.services.medical_exam_service.upload_document", lambda *a, **k: None)
    client, student, _instructor = api_context

    invalid_response = client.post(
        "/api/v1/medical-exams/public/submit",
        data={"registration_number": student.registration_number, "pin": "wrong", "exam_date": "2026-01-01"},
        files=_pdf_file(),
    )
    valid_response = client.post(
        "/api/v1/medical-exams/public/submit",
        data={"registration_number": student.registration_number, "pin": "1234", "exam_date": "2026-01-01"},
        files=_pdf_file(),
    )

    assert invalid_response.status_code == 200
    assert valid_response.status_code == 200
    assert invalid_response.json() == valid_response.json()


def test_public_submission_persists_exam_for_valid_credentials(api_context, monkeypatch):
    """A valid public submission creates an active medical exam record."""
    monkeypatch.setattr("app.services.medical_exam_service.upload_document", lambda *a, **k: None)
    client, student, instructor = api_context

    client.post(
        "/api/v1/medical-exams/public/submit",
        data={"registration_number": student.registration_number, "pin": "1234", "exam_date": "2026-01-01"},
        files=_pdf_file(),
    )

    status_response = client.get(f"/api/v1/medical-exams/students/{student.id}/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "valido"


def test_public_submission_is_rate_limited_per_ip_and_registration(api_context, monkeypatch):
    """After the configured attempt threshold, further requests are rejected with 429."""
    monkeypatch.setattr("app.services.medical_exam_service.upload_document", lambda *a, **k: None)
    client, student, _instructor = api_context

    responses = [
        client.post(
            "/api/v1/medical-exams/public/submit",
            data={"registration_number": student.registration_number, "pin": "wrong", "exam_date": "2026-01-01"},
            files=_pdf_file(),
        )
        for _ in range(medical_exam_rate_limiter.max_attempts + 1)
    ]

    assert [r.status_code for r in responses[:-1]] == [200] * medical_exam_rate_limiter.max_attempts
    assert responses[-1].status_code == 429


def test_instructor_can_record_exam_without_file(api_context):
    """An instructor can record a medical exam without attaching a file."""
    client, student, _instructor = api_context

    response = client.post(
        f"/api/v1/medical-exams/students/{student.id}",
        data={"exam_date": "2026-01-01"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "active"
    assert body["document"] is None


def test_instructor_upload_supersedes_prior_record_and_history_grows(api_context, monkeypatch):
    """A second instructor submission supersedes the first, keeping both in history."""
    monkeypatch.setattr("app.services.medical_exam_service.upload_document", lambda *a, **k: None)
    client, student, _instructor = api_context

    client.post(f"/api/v1/medical-exams/students/{student.id}", data={"exam_date": "2025-01-01"}, files=_pdf_file())
    client.post(f"/api/v1/medical-exams/students/{student.id}", data={"exam_date": "2026-01-01"}, files=_pdf_file())

    history = client.get(f"/api/v1/medical-exams/students/{student.id}").json()
    statuses = {record["status"] for record in history}

    assert len(history) == 2
    assert statuses == {"active", "superseded"}


def test_dashboard_lists_students_with_expiring_or_expired_exams(api_context, monkeypatch):
    """The dashboard surfaces only vencendo/vencido students, not valido ones."""
    monkeypatch.setattr("app.services.medical_exam_service.upload_document", lambda *a, **k: None)
    client, student, _instructor = api_context

    overdue_date = (datetime.now(UTC) - timedelta(days=400)).date().isoformat()
    client.post(f"/api/v1/medical-exams/students/{student.id}", data={"exam_date": overdue_date})

    dashboard = client.get("/api/v1/medical-exams/dashboard").json()

    assert any(item["student_id"] == student.id and item["status"] == "vencido" for item in dashboard)


def test_medical_exam_endpoints_require_authentication():
    """Instructor endpoints reject unauthenticated requests."""
    client = TestClient(app)

    response = client.get("/api/v1/medical-exams/dashboard")

    assert response.status_code == 401
