"""API tests for the instructor/admin report endpoints (REP-01-REP-05)."""

import os
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.core.database import get_db
from app.core.security import get_password_hash
from app.dependencies.auth import get_current_instructor_or_admin, get_current_user
from app.main import app
from app.models import (
    Attendance,
    Base,
    Belt,
    Event,
    EventType,
    Exam,
    ExamParticipant,
    Payment,
    PlanTier,
    PlanVersion,
    Student,
    StudentPlan,
    User,
)


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
        email="reports-instructor@dojo.test",
        password_hash="unused",
        full_name="Instructor",
        role="instructor",
    )
    session.add_all([belt, instructor])
    session.commit()
    student = Student(
        registration_number="REP-101",
        full_name="Report Student",
        category="adult",
        current_belt_id=belt.id,
        pin=get_password_hash("1234"),
        classes_per_week=2,
        is_active=True,
    )
    session.add(student)
    session.commit()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_instructor_or_admin] = lambda: instructor
    yield TestClient(app), session, student, instructor, belt
    app.dependency_overrides.clear()
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


class TestAuthorization:
    """No report endpoint is public; every route requires instructor/admin auth."""

    def test_report_endpoints_require_authentication(self):
        client = TestClient(app)
        assert client.get("/api/v1/reports/belt-exams/some-id").status_code == 401
        assert client.get("/api/v1/reports/attendance/student/some-id").status_code == 401
        assert client.get("/api/v1/reports/attendance/class?event_type_id=some-id").status_code == 401
        assert client.get("/api/v1/reports/finance").status_code == 401

    def test_report_endpoints_reject_wrong_role_with_403(self):
        """An authenticated user whose role is neither instructor nor admin is rejected by
        the shared get_current_instructor_or_admin dependency (real dependency chain, not bypassed).
        """
        wrong_role_user = MagicMock(spec=User)
        wrong_role_user.role = "student"
        wrong_role_user.is_active = True

        app.dependency_overrides[get_current_user] = lambda: wrong_role_user
        try:
            client = TestClient(app)
            assert client.get("/api/v1/reports/belt-exams/some-id").status_code == 403
            assert client.get("/api/v1/reports/attendance/student/some-id").status_code == 403
            assert client.get("/api/v1/reports/attendance/class?event_type_id=some-id").status_code == 403
            assert client.get("/api/v1/reports/finance").status_code == 403
        finally:
            app.dependency_overrides.pop(get_current_user, None)


class TestBeltExamReportEndpoint:
    def test_happy_path_json(self, api_context):
        client, session, student, _instructor, belt = api_context
        event = Event(
            title="Exame",
            event_type_id=_make_event_type(session).id,
            start_datetime=datetime.now(UTC),
            created_by=_instructor.id,
        )
        session.add(event)
        session.commit()
        exam = Exam(event_id=event.id, belt_id=belt.id, exam_date=datetime.now(UTC), created_by=_instructor.id)
        session.add(exam)
        session.commit()
        participant = ExamParticipant(exam_id=exam.id, student_id=student.id, role="candidate", status="pending")
        session.add(participant)
        session.commit()

        response = client.get(f"/api/v1/reports/belt-exams/{student.id}")

        assert response.status_code == 200
        body = response.json()
        assert body["student_id"] == student.id
        assert len(body["participations"]) == 1

    def test_404_for_nonexistent_student(self, api_context):
        client, *_ = api_context

        response = client.get("/api/v1/reports/belt-exams/nonexistent-id")

        assert response.status_code == 404

    def test_empty_participations_returns_200(self, api_context):
        client, session, student, _instructor, belt = api_context

        response = client.get(f"/api/v1/reports/belt-exams/{student.id}")

        assert response.status_code == 200
        assert response.json()["participations"] == []

    def test_pdf_format_returns_pdf_bytes(self, api_context):
        client, session, student, _instructor, belt = api_context

        response = client.get(f"/api/v1/reports/belt-exams/{student.id}?format=pdf")

        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")
        assert "attachment" in response.headers["content-disposition"]

    def test_csv_format_returns_csv_content(self, api_context):
        client, session, student, _instructor, belt = api_context

        response = client.get(f"/api/v1/reports/belt-exams/{student.id}?format=csv")

        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]

    def test_invalid_format_returns_400(self, api_context):
        client, session, student, _instructor, belt = api_context

        response = client.get(f"/api/v1/reports/belt-exams/{student.id}?format=xml")

        assert response.status_code == 400


class TestStudentAttendanceReportEndpoint:
    def test_happy_path_json(self, api_context):
        client, session, student, instructor, belt = api_context
        event_type = _make_event_type(session)
        event = Event(
            title="Aula",
            event_type_id=event_type.id,
            start_datetime=datetime(2026, 1, 10, tzinfo=UTC),
            created_by=instructor.id,
        )
        session.add(event)
        session.commit()
        attendance = Attendance(
            event_id=event.id,
            student_id=student.id,
            check_in_method="tablet",
            check_in_at=datetime(2026, 1, 10, tzinfo=UTC),
        )
        session.add(attendance)
        session.commit()

        response = client.get(
            f"/api/v1/reports/attendance/student/{student.id}"
            "?start_date=2026-01-01T00:00:00Z&end_date=2026-01-31T00:00:00Z"
        )

        assert response.status_code == 200
        assert response.json()["total_attendances"] == 1

    def test_404_for_nonexistent_student(self, api_context):
        client, *_ = api_context

        response = client.get("/api/v1/reports/attendance/student/nonexistent-id")

        assert response.status_code == 404

    def test_400_when_start_after_end(self, api_context):
        client, session, student, _instructor, belt = api_context

        response = client.get(
            f"/api/v1/reports/attendance/student/{student.id}"
            "?start_date=2026-02-01T00:00:00Z&end_date=2026-01-01T00:00:00Z"
        )

        assert response.status_code == 400

    def test_pdf_format_returns_pdf_bytes(self, api_context):
        client, session, student, _instructor, belt = api_context

        response = client.get(f"/api/v1/reports/attendance/student/{student.id}?format=pdf")

        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")

    def test_csv_format_returns_csv_content(self, api_context):
        client, session, student, _instructor, belt = api_context

        response = client.get(f"/api/v1/reports/attendance/student/{student.id}?format=csv")

        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]


class TestClassAttendanceReportEndpoint:
    def test_happy_path_json(self, api_context):
        client, session, student, instructor, belt = api_context
        event_type = _make_event_type(session)
        event = Event(
            title="Aula",
            event_type_id=event_type.id,
            start_datetime=datetime(2026, 1, 10, tzinfo=UTC),
            created_by=instructor.id,
        )
        session.add(event)
        session.commit()
        attendance = Attendance(
            event_id=event.id,
            student_id=student.id,
            check_in_method="tablet",
            check_in_at=datetime(2026, 1, 10, tzinfo=UTC),
        )
        session.add(attendance)
        session.commit()

        response = client.get(
            f"/api/v1/reports/attendance/class?event_type_id={event_type.id}"
            "&start_date=2026-01-01T00:00:00Z&end_date=2026-01-31T00:00:00Z"
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["events"]) == 1
        assert len(body["roster"]) == 1

    def test_404_for_nonexistent_event_type(self, api_context):
        client, *_ = api_context

        response = client.get("/api/v1/reports/attendance/class?event_type_id=nonexistent-id")

        assert response.status_code == 404

    def test_400_when_start_after_end(self, api_context):
        client, session, student, instructor, belt = api_context
        event_type = _make_event_type(session)

        response = client.get(
            f"/api/v1/reports/attendance/class?event_type_id={event_type.id}"
            "&start_date=2026-02-01T00:00:00Z&end_date=2026-01-01T00:00:00Z"
        )

        assert response.status_code == 400

    def test_pdf_format_returns_pdf_bytes(self, api_context):
        client, session, student, instructor, belt = api_context
        event_type = _make_event_type(session)

        response = client.get(f"/api/v1/reports/attendance/class?event_type_id={event_type.id}&format=pdf")

        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")

    def test_csv_format_returns_csv_content(self, api_context):
        client, session, student, instructor, belt = api_context
        event_type = _make_event_type(session)

        response = client.get(f"/api/v1/reports/attendance/class?event_type_id={event_type.id}&format=csv")

        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]


class TestFinancialReportEndpoint:
    def test_happy_path_json(self, api_context):
        client, session, student, instructor, belt = api_context
        tier = PlanTier(weekly_frequency=2, name="2x", is_active=True)
        session.add(tier)
        session.commit()
        version = PlanVersion(
            plan_tier_id=tier.id,
            price=Decimal("150.00"),
            status="active",
            effective_from=datetime.now(UTC),
            created_by=instructor.id,
        )
        session.add(version)
        session.commit()
        session.add(StudentPlan(student_id=student.id, plan_version_id=version.id, status="active"))
        session.add(
            Payment(
                student_id=student.id,
                amount=Decimal("150.00"),
                payment_date=datetime(2026, 1, 5, tzinfo=UTC),
                recorded_by=instructor.id,
                status="active",
            )
        )
        session.commit()

        response = client.get(
            "/api/v1/reports/finance?start_date=2026-01-01T00:00:00Z&end_date=2026-01-31T00:00:00Z&months_ahead=3"
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["payments"]) == 1
        assert body["projection"]["monthly_total"] == "150.00"
        assert body["projection"]["projected_total"] == "450.00"

    def test_400_when_start_after_end(self, api_context):
        client, *_ = api_context

        response = client.get("/api/v1/reports/finance?start_date=2026-02-01T00:00:00Z&end_date=2026-01-01T00:00:00Z")

        assert response.status_code == 400

    def test_400_when_months_ahead_below_minimum(self, api_context):
        client, *_ = api_context

        response = client.get("/api/v1/reports/finance?months_ahead=0")

        assert response.status_code == 400

    def test_pdf_format_returns_pdf_bytes(self, api_context):
        client, *_ = api_context

        response = client.get("/api/v1/reports/finance?format=pdf")

        assert response.status_code == 200
        assert response.content.startswith(b"%PDF-")

    def test_csv_format_contains_all_three_section_headers(self, api_context):
        client, *_ = api_context

        response = client.get("/api/v1/reports/finance?format=csv")

        assert response.status_code == 200
        text = response.content.decode("utf-8")
        assert "Pagamentos" in text
        assert "Inadimplência" in text
        assert "Projeção" in text


def _make_event_type(session) -> EventType:
    event_type = EventType(name="Regular", counts_for_belt=True)
    session.add(event_type)
    session.commit()
    return event_type
