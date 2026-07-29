"""Integration tests for belt and belt requirement API endpoints."""

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
from app.dependencies.auth import (
    get_current_admin,
    get_current_instructor_or_admin,
    get_current_user,
)
from app.main import app
from app.models import Base, Belt, EventType, User

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


def _make_admin(db, **kwargs):
    n = _next_id()
    defaults = {
        "email": f"admin{n}@dojo.com",
        "password_hash": get_password_hash("test123"),
        "full_name": f"Admin User {n}",
        "role": "admin",
        "is_active": True,
    }
    defaults.update(kwargs)
    user = User(**defaults)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_belt(db, **kwargs):
    n = _next_id()
    defaults = {"name": f"Belt {n}", "category": "adult", "sort_order": n}
    defaults.update(kwargs)
    belt = Belt(**defaults)
    db.add(belt)
    db.commit()
    db.refresh(belt)
    return belt


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
def admin_user(db_session):
    return _make_admin(db_session)


@pytest.fixture(scope="function")
def client(db_session, admin_user):
    """TestClient with DB override and auth dependency override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_current_admin] = lambda: admin_user
    app.dependency_overrides[get_current_instructor_or_admin] = lambda: admin_user
    tc = TestClient(app)
    yield tc
    app.dependency_overrides.clear()


class TestCreateRequirement:
    """Tests for POST /api/v1/belts/{belt_id}/requirements."""

    def test_create_requirement_includes_event_type(self, client, db_session):
        """The created requirement should include the event type name, not just its ID."""
        belt = _make_belt(db_session)
        event_type = _make_event_type(db_session, name="Aula Regular")

        response = client.post(
            f"/api/v1/belts/{belt.id}/requirements",
            json={"event_type_id": event_type.id, "required_count": 30, "description": "Treinos"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["event_type"] is not None
        assert data["event_type"]["name"] == "Aula Regular"


class TestListRequirements:
    """Tests for GET /api/v1/belts/{belt_id}/requirements."""

    def test_list_requirements_includes_event_type(self, client, db_session):
        """Listed requirements should include the nested event type name."""
        belt = _make_belt(db_session)
        event_type = _make_event_type(db_session, name="Aula Regular")
        client.post(
            f"/api/v1/belts/{belt.id}/requirements",
            json={"event_type_id": event_type.id, "required_count": 30, "description": "Treinos"},
        )

        response = client.get(f"/api/v1/belts/{belt.id}/requirements")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["event_type"]["name"] == "Aula Regular"


class TestGetBeltWithRequirements:
    """Tests for GET /api/v1/belts/{belt_id}."""

    def test_get_belt_requirements_include_event_type(self, client, db_session):
        """Requirements nested under a belt should include the event type name."""
        belt = _make_belt(db_session)
        event_type = _make_event_type(db_session, name="Aula Regular")
        client.post(
            f"/api/v1/belts/{belt.id}/requirements",
            json={"event_type_id": event_type.id, "required_count": 30, "description": "Treinos"},
        )

        response = client.get(f"/api/v1/belts/{belt.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["requirements"][0]["event_type"]["name"] == "Aula Regular"
