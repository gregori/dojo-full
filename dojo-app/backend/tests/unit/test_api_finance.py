"""API tests for the financial foundation: authorization and idempotent generation."""

import os
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.core.database import get_db
from app.core.security import get_password_hash
from app.dependencies.auth import get_current_instructor_or_admin
from app.main import app
from app.models import Base, Belt, Student, User


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
        email="finance-instructor@dojo.test",
        password_hash="unused",
        full_name="Instructor",
        role="instructor",
    )
    session.add_all([belt, instructor])
    session.commit()
    student = Student(
        registration_number="FIN-101",
        full_name="Finance Student",
        category="adult",
        current_belt_id=belt.id,
        pin=get_password_hash("1234"),
        classes_per_week=2,
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


class TestAuthorization:
    """No FIN-0X endpoint is public; every route requires instructor/admin auth (D5)."""

    def test_plans_endpoints_require_authentication(self):
        client = TestClient(app)
        assert client.get("/api/v1/plans").status_code == 401
        assert (
            client.post("/api/v1/plans", json={"weekly_frequency": 2, "name": "x", "price": "1.00"}).status_code == 401
        )

    def test_student_plan_endpoints_require_authentication(self):
        client = TestClient(app)
        assert client.post("/api/v1/students/some-id/plan").status_code == 401
        assert client.get("/api/v1/students/some-id/plan").status_code == 401

    def test_mensalidade_endpoints_require_authentication(self):
        client = TestClient(app)
        assert client.post("/api/v1/mensalidades/generate").status_code == 401
        assert client.get("/api/v1/students/some-id/mensalidades").status_code == 401
        assert client.get("/api/v1/students/some-id/balance").status_code == 401
        assert client.get("/api/v1/finance/overdue").status_code == 401

    def test_payment_endpoints_require_authentication(self):
        client = TestClient(app)
        assert client.post("/api/v1/payments", json={}).status_code == 401
        assert client.post("/api/v1/payments/some-id/void").status_code == 401


class TestPlanTierAndAssignmentFlow:
    def test_create_tier_and_assign_student(self, api_context):
        client, student, _instructor = api_context

        create_response = client.post(
            "/api/v1/plans", json={"weekly_frequency": 2, "name": "2x por semana", "price": "150.00"}
        )
        assert create_response.status_code == 201
        assert create_response.json()["current_price"] == "150.00"

        assign_response = client.post(f"/api/v1/students/{student.id}/plan")
        assert assign_response.status_code == 201
        assert assign_response.json()["plan_version"]["price"] == "150.00"

    def test_assign_without_matching_tier_fails_loudly(self, api_context):
        client, student, _instructor = api_context

        response = client.post(f"/api/v1/students/{student.id}/plan")

        assert response.status_code == 400


class TestGenerateChargesIdempotency:
    def test_generating_twice_does_not_duplicate(self, api_context):
        client, student, _instructor = api_context
        client.post("/api/v1/plans", json={"weekly_frequency": 2, "name": "2x por semana", "price": "150.00"})
        client.post(f"/api/v1/students/{student.id}/plan")
        body = {"reference_month": datetime(2026, 5, 1, tzinfo=UTC).isoformat()}

        first = client.post("/api/v1/mensalidades/generate", json=body)
        second = client.post("/api/v1/mensalidades/generate", json=body)

        assert first.status_code == 200
        assert first.json()["created_count"] == 1
        assert second.json()["created_count"] == 0
        assert second.json()["skipped_count"] == 1

        history = client.get(f"/api/v1/students/{student.id}/mensalidades").json()
        assert len(history) == 1


class TestPaymentFlow:
    def test_record_and_void_payment(self, api_context):
        client, student, _instructor = api_context

        record_response = client.post(
            "/api/v1/payments",
            json={
                "student_id": student.id,
                "amount": "100.00",
                "payment_date": datetime.now(UTC).isoformat(),
                "method": "pix",
            },
        )
        assert record_response.status_code == 201
        payment_id = record_response.json()["id"]

        void_response = client.post(f"/api/v1/payments/{payment_id}/void")
        assert void_response.status_code == 200
        assert void_response.json()["status"] == "voided"
