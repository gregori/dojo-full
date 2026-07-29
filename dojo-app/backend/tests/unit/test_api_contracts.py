"""API tests for contract template authoring and the contract lifecycle (D1-D7)."""

import base64
import io
import os
from datetime import UTC, datetime
from decimal import Decimal

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

MINIMAL_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="


@pytest.fixture
def api_context(monkeypatch):
    """Provide a fresh in-memory database with one active student and instructor."""
    monkeypatch.setattr("app.services.contract_service.upload_document", lambda *a, **k: None)
    monkeypatch.setattr("app.services.contract_service.download_document", lambda key: b"%PDF-1.4 pdf-bytes")

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    belt = Belt(name="Blue", category="adult", sort_order=3)
    instructor = User(
        email="contracts-instructor@dojo.test",
        password_hash="unused",
        full_name="Instructor",
        role="instructor",
    )
    session.add_all([belt, instructor])
    session.commit()
    student = Student(
        registration_number="CON-101",
        full_name="Contract Student",
        contract_name="Responsavel Legal",
        contract_cpf="123.456.789-00",
        address_street="Rua Teste, 100",
        address_neighborhood="Centro",
        address_city="Sao Paulo",
        address_zip="01000-000",
        birth_date=datetime(2000, 1, 1, tzinfo=UTC),
        phone="(11) 99999-9999",
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


def _setup_catalog(client):
    client.post("/api/v1/plans", json={"weekly_frequency": 2, "name": "2x por semana", "price": "150.00"})
    client.post(
        "/api/v1/contract-templates",
        json={
            "body": "Contrato de {{ student.contract_name }}, valor {{ plan_version.price }}.",
            "effective_from": datetime.now(UTC).isoformat(),
        },
    )


class TestAuthorization:
    """No contract endpoint is public; every route requires instructor/admin auth (D5)."""

    def test_contract_template_endpoints_require_authentication(self):
        client = TestClient(app)
        assert client.get("/api/v1/contract-templates").status_code == 401
        assert client.get("/api/v1/contract-templates/active").status_code == 401
        assert client.post("/api/v1/contract-templates", json={}).status_code == 401

    def test_contract_endpoints_require_authentication(self):
        client = TestClient(app)
        assert client.post("/api/v1/students/some-id/contracts/matricular").status_code == 401
        assert client.get("/api/v1/students/some-id/contracts").status_code == 401
        assert client.get("/api/v1/students/some-id/contracts/current").status_code == 401
        assert client.post("/api/v1/contracts/some-id/regenerate").status_code == 401
        assert client.post("/api/v1/contracts/some-id/sign/on-screen", json={}).status_code == 401
        assert client.post("/api/v1/contracts/some-id/sign/upload").status_code == 401
        assert client.get("/api/v1/contracts/some-id/download").status_code == 401


class TestContractTemplateFlow:
    def test_create_and_list_versions(self, api_context):
        client, _student, _instructor = api_context

        create_response = client.post(
            "/api/v1/contract-templates",
            json={"body": "Corpo v1", "effective_from": datetime.now(UTC).isoformat()},
        )
        assert create_response.status_code == 201
        assert create_response.json()["status"] == "active"

        active_response = client.get("/api/v1/contract-templates/active")
        assert active_response.status_code == 200
        assert active_response.json()["body"] == "Corpo v1"

        history_response = client.get("/api/v1/contract-templates")
        assert history_response.status_code == 200
        assert len(history_response.json()) == 1

    def test_active_returns_404_when_none_exists(self, api_context):
        client, _student, _instructor = api_context

        response = client.get("/api/v1/contract-templates/active")

        assert response.status_code == 404


class TestMatriculaFlow:
    def test_matricular_creates_draft_contract(self, api_context):
        client, student, _instructor = api_context
        _setup_catalog(client)

        response = client.post(f"/api/v1/students/{student.id}/contracts/matricular")

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "draft"
        assert body["document"] is not None

    def test_matricular_fails_without_active_template(self, api_context):
        client, student, _instructor = api_context
        client.post("/api/v1/plans", json={"weekly_frequency": 2, "name": "2x por semana", "price": "150.00"})

        response = client.post(f"/api/v1/students/{student.id}/contracts/matricular")

        assert response.status_code == 400

    def test_current_contract_returns_404_when_none_exists(self, api_context):
        client, student, _instructor = api_context

        response = client.get(f"/api/v1/students/{student.id}/contracts/current")

        assert response.status_code == 404

    def test_rerunning_matricular_keeps_a_single_draft_in_history(self, api_context):
        client, student, _instructor = api_context
        _setup_catalog(client)

        first = client.post(f"/api/v1/students/{student.id}/contracts/matricular")
        second = client.post(f"/api/v1/students/{student.id}/contracts/matricular")

        assert first.json()["id"] == second.json()["id"]
        history = client.get(f"/api/v1/students/{student.id}/contracts").json()
        assert len(history) == 1

    def test_current_contract_returns_the_draft_during_a_renewal(self, api_context):
        """Regression (review finding 2): a signed+draft pair legitimately coexists mid-renewal.

        "current" must surface the draft awaiting action, not the stale signed row.
        """
        client, student, _instructor = api_context
        _setup_catalog(client)
        first_id = client.post(f"/api/v1/students/{student.id}/contracts/matricular").json()["id"]
        client.post(
            f"/api/v1/contracts/{first_id}/sign/on-screen",
            json={"signature_png": f"data:image/png;base64,{MINIMAL_PNG_B64}"},
        )
        renewal_id = client.post(f"/api/v1/students/{student.id}/contracts/matricular").json()["id"]

        current = client.get(f"/api/v1/students/{student.id}/contracts/current")

        assert current.status_code == 200
        assert current.json()["id"] == renewal_id
        assert current.json()["status"] == "draft"


class TestSigningFlow:
    def test_sign_on_screen_then_download(self, api_context):
        client, student, _instructor = api_context
        _setup_catalog(client)
        contract_id = client.post(f"/api/v1/students/{student.id}/contracts/matricular").json()["id"]

        sign_response = client.post(
            f"/api/v1/contracts/{contract_id}/sign/on-screen",
            json={"signature_png": f"data:image/png;base64,{MINIMAL_PNG_B64}"},
        )
        assert sign_response.status_code == 200
        assert sign_response.json()["status"] == "signed"
        assert sign_response.json()["signature_method"] == "on_screen"

        download_response = client.get(f"/api/v1/contracts/{contract_id}/download")
        assert download_response.status_code == 200
        assert download_response.content == b"%PDF-1.4 pdf-bytes"

    def test_sign_by_upload(self, api_context):
        client, student, _instructor = api_context
        _setup_catalog(client)
        contract_id = client.post(f"/api/v1/students/{student.id}/contracts/matricular").json()["id"]

        response = client.post(
            f"/api/v1/contracts/{contract_id}/sign/upload",
            files={"file": ("signed.pdf", io.BytesIO(b"%PDF-1.4 pdf-bytes"), "application/pdf")},
        )

        assert response.status_code == 200
        assert response.json()["signature_method"] == "uploaded"

    def test_regenerate_draft(self, api_context):
        client, student, _instructor = api_context
        _setup_catalog(client)
        contract_id = client.post(f"/api/v1/students/{student.id}/contracts/matricular").json()["id"]

        response = client.post(f"/api/v1/contracts/{contract_id}/regenerate")

        assert response.status_code == 200
        assert response.json()["status"] == "draft"

    def test_regenerate_signed_contract_returns_409(self, api_context):
        client, student, _instructor = api_context
        _setup_catalog(client)
        contract_id = client.post(f"/api/v1/students/{student.id}/contracts/matricular").json()["id"]
        client.post(
            f"/api/v1/contracts/{contract_id}/sign/on-screen",
            json={"signature_png": f"data:image/png;base64,{MINIMAL_PNG_B64}"},
        )

        response = client.post(f"/api/v1/contracts/{contract_id}/regenerate")

        assert response.status_code == 409

    def test_sign_upload_rejects_disallowed_mime_type(self, api_context):
        client, student, _instructor = api_context
        _setup_catalog(client)
        contract_id = client.post(f"/api/v1/students/{student.id}/contracts/matricular").json()["id"]

        response = client.post(
            f"/api/v1/contracts/{contract_id}/sign/upload",
            files={"file": ("x.txt", io.BytesIO(b"not a pdf"), "text/plain")},
        )

        assert response.status_code == 400

    def test_sign_on_screen_rejects_malformed_base64(self, api_context):
        """Regression (review finding 3): invalid base64 must be a clean 400, not an unhandled 500."""
        client, student, _instructor = api_context
        _setup_catalog(client)
        contract_id = client.post(f"/api/v1/students/{student.id}/contracts/matricular").json()["id"]

        response = client.post(
            f"/api/v1/contracts/{contract_id}/sign/on-screen",
            json={"signature_png": "not-valid-base64!!!"},
        )

        assert response.status_code == 400

    def test_sign_on_screen_rejects_oversized_payload(self, api_context):
        """Regression (review finding 3): the signature payload is bounded, like the sibling upload path."""
        client, student, _instructor = api_context
        _setup_catalog(client)
        contract_id = client.post(f"/api/v1/students/{student.id}/contracts/matricular").json()["id"]

        response = client.post(
            f"/api/v1/contracts/{contract_id}/sign/on-screen",
            json={"signature_png": "a" * 700_001},
        )

        assert response.status_code == 422

    def test_download_filename_extension_matches_the_uploaded_mime_type(self, api_context):
        """Regression (review finding 4): a JPEG-uploaded signed scan must not be advertised as .pdf."""
        client, student, _instructor = api_context
        _setup_catalog(client)
        contract_id = client.post(f"/api/v1/students/{student.id}/contracts/matricular").json()["id"]
        client.post(
            f"/api/v1/contracts/{contract_id}/sign/upload",
            files={"file": ("signed.jpg", io.BytesIO(b"\xff\xd8\xffjpeg-bytes"), "image/jpeg")},
        )

        response = client.get(f"/api/v1/contracts/{contract_id}/download")

        assert response.status_code == 200
        assert ".jpg" in response.headers["content-disposition"]
