"""Integration tests for the event-series API endpoints."""

import itertools
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Force test database URL before any app imports
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.core.database import get_db
from app.core.security import get_password_hash
from app.core.timezone import local_today
from app.dependencies.auth import (
    get_current_admin,
    get_current_instructor_or_admin,
    get_current_user,
)
from app.main import app
from app.models import Base, EventType, User

TEST_DATABASE_URL = "sqlite:///:memory:"
_counter = itertools.count(1)


def _next_id():
    return next(_counter)


@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


def _make_instructor(db, **kwargs):
    n = _next_id()
    defaults = {
        "email": f"instructor{n}@dojo.com",
        "password_hash": get_password_hash("test123"),
        "full_name": f"Instructor {n}",
        "role": "instructor",
        "is_active": True,
    }
    defaults.update(kwargs)
    user = User(**defaults)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_event_type(db, **kwargs):
    n = _next_id()
    defaults = {"name": f"Event Type {n}", "color": "#3498db", "counts_for_belt": True}
    defaults.update(kwargs)
    et = EventType(**defaults)
    db.add(et)
    db.commit()
    db.refresh(et)
    return et


@pytest.fixture(scope="function")
def instructor_user(db_session):
    return _make_instructor(db_session)


@pytest.fixture(scope="function")
def client(db_session, instructor_user):
    """TestClient with DB override and auth dependency override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: instructor_user
    app.dependency_overrides[get_current_admin] = lambda: instructor_user
    app.dependency_overrides[get_current_instructor_or_admin] = lambda: instructor_user
    tc = TestClient(app)
    yield tc
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def unauthenticated_client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    tc = TestClient(app)
    yield tc
    app.dependency_overrides.clear()


class TestEventSeriesAuth:
    """Auth is required on every route, mirroring events.py's existing tests."""

    def test_list_requires_auth(self, unauthenticated_client):
        response = unauthenticated_client.get("/api/v1/event-series")
        assert response.status_code == 401

    def test_create_requires_auth(self, unauthenticated_client):
        response = unauthenticated_client.post("/api/v1/event-series", json={})
        assert response.status_code == 401


class TestEventSeriesCRUDRoutes:
    """CRUD round-trip through the actual FastAPI routes, not just the service layer."""

    def test_create_and_list(self, client, db_session):
        et = _make_event_type(db_session, name="Aula Regular")

        response = client.post(
            "/api/v1/event-series",
            json={
                "title": "Aikido Geral",
                "event_type_id": et.id,
                "days_of_week": [0, 2, 5],
                "start_time": "07:00:00",
            },
        )
        assert response.status_code == 201
        created = response.json()
        assert created["days_of_week"] == [0, 2, 5]
        assert created["title"] == "Aikido Geral"
        assert "check_in_token" in created

        list_response = client.get("/api/v1/event-series")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

    def test_get_series(self, client, db_session):
        et = _make_event_type(db_session)
        created = client.post(
            "/api/v1/event-series",
            json={
                "title": "Judo Infantil",
                "event_type_id": et.id,
                "days_of_week": [1],
                "start_time": "18:00:00",
            },
        ).json()

        response = client.get(f"/api/v1/event-series/{created['id']}")
        assert response.status_code == 200
        assert response.json()["title"] == "Judo Infantil"

    def test_update_series(self, client, db_session):
        et = _make_event_type(db_session)
        created = client.post(
            "/api/v1/event-series",
            json={
                "title": "Old Title",
                "event_type_id": et.id,
                "days_of_week": [3],
                "start_time": "19:00:00",
            },
        ).json()

        response = client.put(f"/api/v1/event-series/{created['id']}", json={"title": "New Title"})
        assert response.status_code == 200
        assert response.json()["title"] == "New Title"

    def test_generate_occurrences(self, client, db_session):
        et = _make_event_type(db_session)
        today = local_today()
        created = client.post(
            "/api/v1/event-series",
            json={
                "title": "Daily Class",
                "event_type_id": et.id,
                "days_of_week": [0, 1, 2, 3, 4, 5, 6],
                "start_time": "07:00:00",
                "series_start_date": today.isoformat(),
            },
        ).json()

        response = client.post(f"/api/v1/event-series/{created['id']}/generate")
        assert response.status_code == 200
        data = response.json()
        assert data["created_count"] == 365
        assert data["skipped_count"] == 0

    def test_qr_code(self, client, db_session):
        et = _make_event_type(db_session)
        created = client.post(
            "/api/v1/event-series",
            json={
                "title": "QR Series",
                "event_type_id": et.id,
                "days_of_week": [0],
                "start_time": "07:00:00",
            },
        ).json()

        response = client.get(f"/api/v1/event-series/{created['id']}/qr-code")
        assert response.status_code == 200
        data = response.json()
        assert data["check_in_token"] == created["check_in_token"]
        assert data["url"] == f"/checkin?token={created['check_in_token']}"

    def test_deactivate_series(self, client, db_session):
        et = _make_event_type(db_session)
        created = client.post(
            "/api/v1/event-series",
            json={
                "title": "To End",
                "event_type_id": et.id,
                "days_of_week": [0],
                "start_time": "07:00:00",
            },
        ).json()

        response = client.delete(f"/api/v1/event-series/{created['id']}")
        assert response.status_code == 204

        get_response = client.get(f"/api/v1/event-series/{created['id']}")
        assert get_response.json()["is_active"] is False
