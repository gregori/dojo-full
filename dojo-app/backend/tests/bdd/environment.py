import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from behave import use_fixture
from behave.fixture import fixture

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fastapi.testclient import TestClient

import app.core.config as _config

class _TestConfig(_config.Settings):
    database_url: str = "sqlite:///:memory:"
    debug: bool = True
    environment: str = "test"

_config.get_settings = lambda: _TestConfig()

from app.models import (
    Base,
    User, Student, Belt, BeltRequirement, BeltPromotion,
    EventType, Event, Attendance,
    Exam, ExamParticipant, ExamBoardMember,
    Organization, Dojo,
)
from app.core.database import get_db, engine
from app.main import app


TEST_DATABASE_URL = "sqlite:///:memory:"


@fixture
def test_database(context):
    """Create a fresh in-memory database for each test and override the app's DB dependency."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign key support in SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    context.db = db
    context.engine = engine

    # Override the get_db dependency to use our test database
    def override_get_db():
        try:
            yield db
        finally:
            pass  # Don't close here; we manage the session lifecycle

    app.dependency_overrides[get_db] = override_get_db

    # Create TestClient with the overridden dependency
    context.client = TestClient(app)

    yield db

    # Cleanup
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(bind=engine)


def before_all(context):
    """Setup before all tests."""
    context.test_mode = True


def before_scenario(context, scenario):
    """Setup before each scenario."""
    use_fixture(test_database, context)

    # Reset state
    context.response = None
    context.last_error = None
    context.user_token = None

    # Entity storage dictionaries for multi-entity scenarios
    context.belts = {}
    context.event_types = {}
    context.events = {}
    context.students = {}
    context.users = {}

    # Current entity references
    context.current_belt = None
    context.current_event_type = None
    context.current_event = None
    context.current_student = None
    context.current_user = None
    context.current_exam = None
    context.current_participant = None
    context.current_requirement = None

    # ID references for placeholder resolution
    context.belt_id = None
    context.event_type_id = None
    context.event_id = None
    context.student_id = None
    context.exam_id = None
    context.participant_id = None
    context.requirement_id = None


def after_scenario(context, scenario):
    """Cleanup after each scenario."""
    if hasattr(context, 'db'):
        context.db.close()