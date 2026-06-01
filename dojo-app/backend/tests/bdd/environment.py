from behave import use_fixture
from behave.fixture import fixture

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base

TEST_DATABASE_URL = "sqlite:///:memory:"


@fixture
def test_database(context):
    """Create a fresh in-memory database for each test."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    context.db = db
    context.engine = engine

    yield db

    db.close()
    Base.metadata.drop_all(bind=engine)


def before_all(context):
    """Setup before all tests."""
    context.test_mode = True
    context.base_url = "http://localhost:8000"


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