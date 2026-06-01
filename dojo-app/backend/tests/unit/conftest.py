"""Shared fixtures for unit tests.

Uses SQLite in-memory database for fast, isolated test execution.
Each test gets a fresh database with all tables created and dropped.
"""
import os
import itertools
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Force test database URL before any app imports
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.models import (
    Base,
    Organization, Dojo, User, Belt, BeltRequirement,
    EventType, Event, Student, Attendance,
    Exam, ExamParticipant, ExamBoardMember, BeltPromotion,
)
from app.core.security import get_password_hash


TEST_DATABASE_URL = "sqlite:///:memory:"

# Global counter for generating unique values across all tests
_counter = itertools.count(1)


def _next_id():
    """Return a monotonically increasing integer for unique test data."""
    return next(_counter)


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


# --- Entity Factories ---

def make_organization(db, **kwargs):
    n = _next_id()
    defaults = {"name": f"Test Org {n}", "description": "Test organization"}
    defaults.update(kwargs)
    org = Organization(**defaults)
    db.add(org)
    db.flush()
    return org


def make_dojo(db, organization_id=None, **kwargs):
    if organization_id is None:
        org = make_organization(db)
        organization_id = org.id
    n = _next_id()
    defaults = {"organization_id": organization_id, "code": n, "name": f"Test Dojo {n}", "address": "123 Main St"}
    defaults.update(kwargs)
    dojo = Dojo(**defaults)
    db.add(dojo)
    db.flush()
    return dojo


def make_user(db, **kwargs):
    n = _next_id()
    defaults = {
        "email": f"user{n}@dojo.com",
        "password_hash": get_password_hash("test123"),
        "full_name": f"Test User {n}",
        "role": "admin",
        "is_active": True,
    }
    defaults.update(kwargs)
    user = User(**defaults)
    db.add(user)
    db.flush()
    return user


def make_belt(db, **kwargs):
    n = _next_id()
    defaults = {"name": f"Belt {n}", "category": "adult", "sort_order": n}
    defaults.update(kwargs)
    belt = Belt(**defaults)
    db.add(belt)
    db.flush()
    return belt


def make_event_type(db, **kwargs):
    n = _next_id()
    defaults = {"name": f"Event Type {n}", "color": "#3498db", "counts_for_belt": True}
    defaults.update(kwargs)
    et = EventType(**defaults)
    db.add(et)
    db.flush()
    return et


def make_event(db, event_type_id=None, created_by=None, **kwargs):
    from datetime import datetime, timezone
    if event_type_id is None:
        et = make_event_type(db)
        event_type_id = et.id
    if created_by is None:
        user = make_user(db)
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
    event = Event(**defaults)
    db.add(event)
    db.flush()
    return event


def make_student(db, current_belt_id=None, **kwargs):
    if current_belt_id is None:
        belt = make_belt(db)
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
    db.flush()
    return student


def make_attendance(db, event_id=None, student_id=None, **kwargs):
    from datetime import datetime, timezone
    if event_id is None:
        event = make_event(db)
        event_id = event.id
    if student_id is None:
        student = make_student(db)
        student_id = student.id
    defaults = {
        "event_id": event_id,
        "student_id": student_id,
        "check_in_method": "tablet",
        "check_in_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    attendance = Attendance(**defaults)
    db.add(attendance)
    db.flush()
    return attendance


def make_belt_requirement(db, belt_id=None, event_type_id=None, **kwargs):
    if belt_id is None:
        belt = make_belt(db)
        belt_id = belt.id
    if event_type_id is None:
        et = make_event_type(db)
        event_type_id = et.id
    defaults = {
        "belt_id": belt_id,
        "event_type_id": event_type_id,
        "required_count": 10,
        "description": "Regular classes",
    }
    defaults.update(kwargs)
    req = BeltRequirement(**defaults)
    db.add(req)
    db.flush()
    return req


def make_exam(db, event_id=None, belt_id=None, created_by=None, **kwargs):
    from datetime import datetime, timezone
    if event_id is None:
        event = make_event(db)
        event_id = event.id
    if belt_id is None:
        belt = make_belt(db)
        belt_id = belt.id
    if created_by is None:
        user = make_user(db)
        created_by = user.id
    defaults = {
        "event_id": event_id,
        "belt_id": belt_id,
        "exam_date": datetime.now(timezone.utc),
        "status": "scheduled",
        "created_by": created_by,
    }
    defaults.update(kwargs)
    exam = Exam(**defaults)
    db.add(exam)
    db.flush()
    return exam


def make_belt_promotion(db, student_id=None, belt_id=None, **kwargs):
    from datetime import datetime, timezone
    if student_id is None:
        student = make_student(db)
        student_id = student.id
    if belt_id is None:
        belt = make_belt(db)
        belt_id = belt.id
    defaults = {
        "student_id": student_id,
        "belt_id": belt_id,
        "promoted_at": datetime.now(timezone.utc),
        "notes": "Initial belt assignment",
    }
    defaults.update(kwargs)
    promotion = BeltPromotion(**defaults)
    db.add(promotion)
    db.flush()
    return promotion