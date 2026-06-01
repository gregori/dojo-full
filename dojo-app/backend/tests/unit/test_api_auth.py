"""Integration tests for auth API endpoints."""

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
from app.main import app
from app.models import Base, User

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine():
    """Create a fresh SQLite in-memory engine for each test."""
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
    """Create a fresh database session for each test."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a TestClient with the test database session."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    tc = TestClient(app)
    yield tc
    app.dependency_overrides.clear()


def _make_admin_user(db, **kwargs):
    """Create an admin user directly in the database."""
    from itertools import count

    n = next(count(1))
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


class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login."""

    def test_login_success(self, client, db_session):
        """Successful login returns access token."""
        user = _make_admin_user(db_session)
        response = client.post(
            "/api/v1/auth/login",
            data={"username": user.email, "password": "test123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, db_session):
        """Login with wrong password returns 401."""
        user = _make_admin_user(db_session)
        response = client.post(
            "/api/v1/auth/login",
            data={"username": user.email, "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client, db_session):
        """Login with non-existent email returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "nobody@dojo.com", "password": "test123"},
        )
        assert response.status_code == 401

    def test_login_inactive_user(self, client, db_session):
        """Login with inactive user returns 401."""
        user = _make_admin_user(db_session, is_active=False)
        response = client.post(
            "/api/v1/auth/login",
            data={"username": user.email, "password": "test123"},
        )
        assert response.status_code == 401


class TestRegisterEndpoint:
    """Tests for POST /api/v1/auth/register."""

    def test_register_success(self, client, db_session):
        """Register a new user returns 201 with user data."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@dojo.com",
                "full_name": "New User",
                "role": "instructor",
                "is_active": True,
                "password": "test123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@dojo.com"
        assert data["full_name"] == "New User"
        assert "id" in data
        assert "password" not in data

    def test_register_duplicate_email(self, client, db_session):
        """Register with duplicate email returns 409."""
        _make_admin_user(db_session, email="taken@dojo.com")
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "taken@dojo.com",
                "full_name": "Duplicate User",
                "role": "instructor",
                "is_active": True,
                "password": "test123",
            },
        )
        assert response.status_code == 409
