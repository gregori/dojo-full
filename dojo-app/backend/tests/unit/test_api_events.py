"""Integration tests for event and event type API endpoints."""
import os
import itertools
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Force test database URL before any app imports
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.models import (
    Base, Organization, Dojo, User, Belt, EventType, Event,
)
from app.core.security import get_password_hash, create_access_token
from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_current_admin, get_current_instructor_or_admin
from app.main import app

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


def _make_event_type(db, **kwargs):
    n = _next_id()
    defaults = {"name": f"Event Type {n}", "color": "#3498db", "counts_for_belt": True}
    defaults.update(kwargs)
    et = EventType(**defaults)
    db.add(et)
    db.commit()
    db.refresh(et)
    return et


def _make_event(db, event_type_id=None, created_by=None, **kwargs):
    if event_type_id is None:
        et = _make_event_type(db)
        event_type_id = et.id
    if created_by is None:
        user = _make_admin(db)
        created_by = user.id
    n = _next_id()
    defaults = {
        "title": f"Test Event {n}",
        "event_type_id": event_type_id,
        "start_datetime": datetime.now(timezone.utc),
        "created_by": created_by,
        "status": "scheduled",
    }
    defaults.update(kwargs)
    ev = Event(**defaults)
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


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


# --- Event Type Tests ---

class TestListEventTypes:
    """Tests for GET /api/v1/events/types."""

    def test_list_event_types_empty(self, client, db_session):
        """List event types returns empty list when none exist."""
        response = client.get("/api/v1/events/types")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_event_types_returns_types(self, client, db_session):
        """List event types returns created types."""
        _make_event_type(db_session, name="Class")
        _make_event_type(db_session, name="Cleaning")
        response = client.get("/api/v1/events/types")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestCreateEventType:
    """Tests for POST /api/v1/events/types."""

    def test_create_event_type_success(self, client, db_session):
        """Create a new event type returns 201."""
        response = client.post(
            "/api/v1/events/types",
            json={"name": "Aikido Class", "color": "#2ecc71", "counts_for_belt": True},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Aikido Class"
        assert data["color"] == "#2ecc71"
        assert data["counts_for_belt"] is True


class TestUpdateEventType:
    """Tests for PUT /api/v1/events/types/{event_type_id}."""

    def test_update_event_type_name(self, client, db_session):
        """Update event type name returns updated type."""
        et = _make_event_type(db_session)
        response = client.put(
            f"/api/v1/events/types/{et.id}",
            json={"name": "Updated Type"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Type"


class TestDeleteEventType:
    """Tests for DELETE /api/v1/events/types/{event_type_id}."""

    def test_delete_event_type(self, client, db_session):
        """Delete event type returns 204."""
        et = _make_event_type(db_session)
        response = client.delete(f"/api/v1/events/types/{et.id}")
        assert response.status_code == 204


# --- Event Tests ---

class TestListEvents:
    """Tests for GET /api/v1/events."""

    def test_list_events_empty(self, client, db_session):
        """List events returns empty list when none exist."""
        response = client.get("/api/v1/events")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_events_returns_events(self, client, db_session):
        """List events returns created events."""
        admin = _make_admin(db_session)
        et = _make_event_type(db_session)
        _make_event(db_session, event_type_id=et.id, created_by=admin.id)
        _make_event(db_session, event_type_id=et.id, created_by=admin.id)
        response = client.get("/api/v1/events")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


class TestGetEvent:
    """Tests for GET /api/v1/events/{event_id}."""

    def test_get_event_by_id(self, client, db_session):
        """Get event by ID returns event details."""
        admin = _make_admin(db_session)
        et = _make_event_type(db_session)
        ev = _make_event(db_session, event_type_id=et.id, created_by=admin.id)
        response = client.get(f"/api/v1/events/{ev.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == ev.id
        assert data["title"] == ev.title

    


class TestCreateEvent:
    """Tests for POST /api/v1/events."""

    def test_create_event_success(self, client, db_session):
        """Create a new event returns 201."""
        et = _make_event_type(db_session)
        start = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        response = client.post(
            "/api/v1/events",
            json={
                "title": "New Event",
                "event_type_id": et.id,
                "start_datetime": start,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "New Event"
        assert data["status"] == "scheduled"


class TestUpdateEvent:
    """Tests for PUT /api/v1/events/{event_id}."""

    def test_update_event_title(self, client, db_session):
        """Update event title returns updated event."""
        admin = _make_admin(db_session)
        et = _make_event_type(db_session)
        ev = _make_event(db_session, event_type_id=et.id, created_by=admin.id)
        response = client.put(
            f"/api/v1/events/{ev.id}",
            json={"title": "Updated Event"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Event"


class TestCancelEvent:
    """Tests for DELETE /api/v1/events/{event_id}."""

    def test_cancel_event(self, client, db_session):
        """Cancel event returns 204."""
        admin = _make_admin(db_session)
        et = _make_event_type(db_session)
        ev = _make_event(db_session, event_type_id=et.id, created_by=admin.id)
        response = client.delete(f"/api/v1/events/{ev.id}")
        assert response.status_code == 204


class TestEventQRCode:
    """Tests for GET /api/v1/events/{event_id}/qr-code."""

    def test_get_event_qr_code(self, client, db_session):
        """Get QR code for event returns token."""
        admin = _make_admin(db_session)
        et = _make_event_type(db_session)
        ev = _make_event(db_session, event_type_id=et.id, created_by=admin.id)
        response = client.get(f"/api/v1/events/{ev.id}/qr-code")
        assert response.status_code == 200
        data = response.json()
        assert "check_in_token" in data
        assert "url" in data