"""Integration tests for the flat dojos listing endpoint."""

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
from app.models import Base, Dojo, Organization, User

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


def _make_organization(db, **kwargs):
    n = _next_id()
    defaults = {"name": f"Org {n}"}
    defaults.update(kwargs)
    org = Organization(**defaults)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _make_dojo(db, organization_id, **kwargs):
    n = _next_id()
    defaults = {"organization_id": organization_id, "code": n, "name": f"Dojo {n}"}
    defaults.update(kwargs)
    dojo = Dojo(**defaults)
    db.add(dojo)
    db.commit()
    db.refresh(dojo)
    return dojo


@pytest.fixture(scope="function")
def instructor_user(db_session):
    return _make_instructor(db_session)


@pytest.fixture(scope="function")
def client(db_session, instructor_user):
    """TestClient with DB override, authenticated as a non-admin instructor."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: instructor_user
    app.dependency_overrides[get_current_instructor_or_admin] = lambda: instructor_user
    app.dependency_overrides[get_current_admin] = lambda: instructor_user
    tc = TestClient(app)
    yield tc
    app.dependency_overrides.clear()


class TestListAllDojos:
    """Tests for GET /api/v1/dojos."""

    def test_lists_dojos_across_organizations(self, client, db_session):
        """An instructor (not just an admin) can list dojos from every organization."""
        org_a = _make_organization(db_session, name="Org A")
        org_b = _make_organization(db_session, name="Org B")
        _make_dojo(db_session, org_a.id, name="Kitahira Dojo")
        _make_dojo(db_session, org_b.id, name="Second Dojo")

        response = client.get("/api/v1/dojos")

        assert response.status_code == 200
        names = {dojo["name"] for dojo in response.json()}
        assert names == {"Kitahira Dojo", "Second Dojo"}
