"""Integration tests for student API endpoints."""

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
from app.core.security import create_access_token, get_password_hash
from app.dependencies.auth import (
    get_current_admin,
    get_current_instructor_or_admin,
    get_current_user,
)
from app.main import app
from app.models import (
    Base,
    Belt,
    Student,
    User,
)

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


def _make_instructor(db, **kwargs):
    n = _next_id()
    defaults = {
        "email": f"instructor{n}@dojo.com",
        "password_hash": get_password_hash("test123"),
        "full_name": f"Instructor User {n}",
        "role": "instructor",
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


def _make_student(db, current_belt_id=None, **kwargs):
    if current_belt_id is None:
        belt = _make_belt(db)
        current_belt_id = belt.id
    n = _next_id()
    defaults = {
        "registration_number": f"REG{n:06d}",
        "full_name": f"Test Student {n}",
        "category": "adult",
        "current_belt_id": current_belt_id,
        "pin": get_password_hash("1234"),
        "is_active": True,
    }
    defaults.update(kwargs)
    student = Student(**defaults)
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@pytest.fixture(scope="function")
def admin_user(db_session):
    return _make_admin(db_session)


@pytest.fixture(scope="function")
def instructor_user(db_session):
    return _make_instructor(db_session)


@pytest.fixture(scope="function")
def auth_headers(admin_user):
    """Return auth headers for an admin user."""
    token = create_access_token({"sub": admin_user.id, "role": admin_user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def instructor_auth_headers(instructor_user):
    """Return auth headers for an instructor user."""
    token = create_access_token({"sub": instructor_user.id, "role": instructor_user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def client(db_session, admin_user):
    """TestClient with DB override and auth dependency override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    # Override auth to return our admin user from DB
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_current_admin] = lambda: admin_user
    app.dependency_overrides[get_current_instructor_or_admin] = lambda: admin_user
    tc = TestClient(app)
    yield tc
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def instructor_client(db_session, instructor_user):
    """TestClient with instructor auth."""

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


class TestListStudents:
    """Tests for GET /api/v1/students."""

    def test_list_students_empty(self, client, db_session):
        """List students returns empty list when no students exist."""
        response = client.get("/api/v1/students")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_students_returns_students(self, client, db_session):
        """List students returns created students."""
        belt = _make_belt(db_session)
        _make_student(db_session, current_belt_id=belt.id, full_name="Student A")
        _make_student(db_session, current_belt_id=belt.id, full_name="Student B")
        response = client.get("/api/v1/students")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_students_filter_by_category(self, client, db_session):
        """List students can filter by category."""
        belt = _make_belt(db_session)
        _make_student(db_session, current_belt_id=belt.id, category="adult")
        _make_student(db_session, current_belt_id=belt.id, category="child")
        response = client.get("/api/v1/students?category=adult")
        assert response.status_code == 200
        data = response.json()
        assert all(s["category"] == "adult" for s in data)

    def test_list_students_includes_current_belt(self, client, db_session):
        """List students should include the nested current_belt object."""
        belt = _make_belt(db_session, name="Blue")
        _make_student(db_session, current_belt_id=belt.id, full_name="Student A")
        response = client.get("/api/v1/students")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["current_belt"] is not None
        assert data[0]["current_belt"]["name"] == "Blue"
        assert data[0]["current_belt"]["id"] == belt.id


class TestGetStudent:
    """Tests for GET /api/v1/students/{student_id}."""

    def test_get_student_by_id(self, client, db_session):
        """Get student by ID returns student details."""
        belt = _make_belt(db_session)
        student = _make_student(db_session, current_belt_id=belt.id)
        response = client.get(f"/api/v1/students/{student.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == student.id
        assert data["full_name"] == student.full_name


class TestCreateStudent:
    """Tests for POST /api/v1/students."""

    def test_create_student_success(self, client, db_session):
        """Create a new student returns 201."""
        belt = _make_belt(db_session)
        response = client.post(
            "/api/v1/students",
            json={
                "full_name": "New Student",
                "category": "adult",
                "current_belt_id": belt.id,
                "pin": "1234",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["full_name"] == "New Student"
        assert data["category"] == "adult"
        assert "id" in data
        assert "registration_number" in data


class TestUpdateStudent:
    """Tests for PUT /api/v1/students/{student_id}."""

    def test_update_student_name(self, client, db_session):
        """Update student name returns updated student."""
        belt = _make_belt(db_session)
        student = _make_student(db_session, current_belt_id=belt.id)
        response = client.put(
            f"/api/v1/students/{student.id}",
            json={"full_name": "Updated Name"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"

    def test_update_student_registration_number(self, client, db_session):
        """Update student registration number returns updated student."""
        belt = _make_belt(db_session)
        student = _make_student(db_session, current_belt_id=belt.id, registration_number="OLD001")
        response = client.put(
            f"/api/v1/students/{student.id}",
            json={"registration_number": "NEW001"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["registration_number"] == "NEW001"

    def test_update_student_duplicate_registration_number(self, client, db_session):
        """Update to a registration number already in use returns 409."""
        belt = _make_belt(db_session)
        _make_student(db_session, current_belt_id=belt.id, registration_number="TAKEN001")
        student = _make_student(db_session, current_belt_id=belt.id, registration_number="OWN001")
        response = client.put(
            f"/api/v1/students/{student.id}",
            json={"registration_number": "TAKEN001"},
        )
        assert response.status_code == 409


class TestDeactivateStudent:
    """Tests for DELETE /api/v1/students/{student_id}."""

    def test_deactivate_student(self, client, db_session):
        """Deactivate student returns 204."""
        belt = _make_belt(db_session)
        student = _make_student(db_session, current_belt_id=belt.id)
        response = client.delete(f"/api/v1/students/{student.id}")
        assert response.status_code == 204


class TestStudentProgress:
    """Tests for GET /api/v1/students/{student_id}/progress."""

    def test_get_student_progress(self, client, db_session):
        """Get student progress returns progress data."""
        belt = _make_belt(db_session)
        student = _make_student(db_session, current_belt_id=belt.id)
        response = client.get(f"/api/v1/students/{student.id}/progress")
        assert response.status_code == 200


class TestStudentExamHistory:
    """Tests for GET /api/v1/students/{student_id}/exam-history."""

    def test_get_student_exam_history(self, client, db_session):
        """Get student exam history returns list."""
        belt = _make_belt(db_session)
        student = _make_student(db_session, current_belt_id=belt.id)
        response = client.get(f"/api/v1/students/{student.id}/exam-history")
        assert response.status_code == 200
