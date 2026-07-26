"""Shared fixtures for unit tests.

Uses SQLite in-memory database for fast, isolated test execution.
Each test gets a fresh database with all tables created and dropped.
"""

import itertools
import os

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Force test database URL before any app imports
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from datetime import UTC
from decimal import Decimal

from app.core.security import get_password_hash
from app.models import (
    Attendance,
    Base,
    Belt,
    BeltPromotion,
    BeltRequirement,
    Contract,
    ContractTemplateVersion,
    Dojo,
    Event,
    EventType,
    Exam,
    ExamParticipant,
    Mensalidade,
    Organization,
    Payment,
    PlanTier,
    PlanVersion,
    Student,
    StudentPlan,
    User,
)

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
    from datetime import datetime

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
        "start_datetime": datetime.now(UTC),
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
    from datetime import datetime

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
        "check_in_at": datetime.now(UTC),
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
    from datetime import datetime

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
        "exam_date": datetime.now(UTC),
        "status": "scheduled",
        "created_by": created_by,
    }
    defaults.update(kwargs)
    exam = Exam(**defaults)
    db.add(exam)
    db.flush()
    return exam


def make_exam_participant(db, exam_id=None, student_id=None, **kwargs):
    if exam_id is None:
        exam = make_exam(db)
        exam_id = exam.id
    if student_id is None:
        student = make_student(db)
        student_id = student.id
    defaults = {
        "exam_id": exam_id,
        "student_id": student_id,
        "role": "candidate",
        "status": "pending",
        "is_eligible": True,
    }
    defaults.update(kwargs)
    participant = ExamParticipant(**defaults)
    db.add(participant)
    db.flush()
    return participant


def make_belt_promotion(db, student_id=None, belt_id=None, **kwargs):
    from datetime import datetime

    if student_id is None:
        student = make_student(db)
        student_id = student.id
    if belt_id is None:
        belt = make_belt(db)
        belt_id = belt.id
    defaults = {
        "student_id": student_id,
        "belt_id": belt_id,
        "promoted_at": datetime.now(UTC),
        "notes": "Initial belt assignment",
    }
    defaults.update(kwargs)
    promotion = BeltPromotion(**defaults)
    db.add(promotion)
    db.flush()
    return promotion


def make_plan_tier(db, **kwargs):
    n = _next_id()
    defaults = {"weekly_frequency": n, "name": f"{n}x por semana", "is_active": True}
    defaults.update(kwargs)
    tier = PlanTier(**defaults)
    db.add(tier)
    db.flush()
    return tier


def make_plan_version(db, plan_tier_id=None, created_by=None, **kwargs):
    from datetime import datetime

    if plan_tier_id is None:
        tier = make_plan_tier(db)
        plan_tier_id = tier.id
    if created_by is None:
        user = make_user(db)
        created_by = user.id
    defaults = {
        "plan_tier_id": plan_tier_id,
        "price": Decimal("100.00"),
        "status": "active",
        "effective_from": datetime.now(UTC),
        "created_by": created_by,
    }
    defaults.update(kwargs)
    version = PlanVersion(**defaults)
    db.add(version)
    db.flush()
    return version


def make_student_plan(db, student_id=None, plan_version_id=None, **kwargs):
    from datetime import datetime

    if student_id is None:
        student = make_student(db)
        student_id = student.id
    if plan_version_id is None:
        version = make_plan_version(db)
        plan_version_id = version.id
    defaults = {
        "student_id": student_id,
        "plan_version_id": plan_version_id,
        "status": "active",
        "started_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    student_plan = StudentPlan(**defaults)
    db.add(student_plan)
    db.flush()
    return student_plan


def make_mensalidade(db, student_id=None, plan_version_id=None, **kwargs):
    from datetime import datetime

    if student_id is None:
        student = make_student(db)
        student_id = student.id
    if plan_version_id is None:
        version = make_plan_version(db)
        plan_version_id = version.id
    defaults = {
        "student_id": student_id,
        "plan_version_id": plan_version_id,
        "reference_month": datetime(2026, 1, 1, tzinfo=UTC),
        "due_date": datetime(2026, 1, 5, tzinfo=UTC),
        "amount": Decimal("100.00"),
    }
    defaults.update(kwargs)
    mensalidade = Mensalidade(**defaults)
    db.add(mensalidade)
    db.flush()
    return mensalidade


def make_student_with_contract_data(db, **kwargs):
    """Create a student with every CON-02/D3 required legal-data field populated."""
    from datetime import datetime

    defaults = {
        "contract_name": "Responsavel Legal",
        "contract_cpf": "123.456.789-00",
        "address_street": "Rua Teste, 100",
        "address_neighborhood": "Centro",
        "address_city": "Sao Paulo",
        "address_zip": "01000-000",
        "birth_date": datetime(2000, 1, 1, tzinfo=UTC),
        "phone": "(11) 99999-9999",
    }
    defaults.update(kwargs)
    return make_student(db, **defaults)


def make_contract_template_version(db, created_by=None, **kwargs):
    from datetime import datetime

    if created_by is None:
        user = make_user(db)
        created_by = user.id
    defaults = {
        "body": "Contrato de {{ student.contract_name }}, plano {{ plan_tier.name }}, valor {{ plan_version.price }}.",
        "status": "active",
        "effective_from": datetime.now(UTC),
        "created_by": created_by,
    }
    defaults.update(kwargs)
    version = ContractTemplateVersion(**defaults)
    db.add(version)
    db.flush()
    return version


def make_contract(
    db, student_id=None, contract_template_version_id=None, plan_version_id=None, created_by=None, **kwargs
):
    if student_id is None:
        student = make_student_with_contract_data(db)
        student_id = student.id
    if contract_template_version_id is None:
        template_version = make_contract_template_version(db)
        contract_template_version_id = template_version.id
    if plan_version_id is None:
        plan_version = make_plan_version(db)
        plan_version_id = plan_version.id
    if created_by is None:
        user = make_user(db)
        created_by = user.id
    defaults = {
        "student_id": student_id,
        "contract_template_version_id": contract_template_version_id,
        "plan_version_id": plan_version_id,
        "status": "draft",
        "created_by": created_by,
    }
    defaults.update(kwargs)
    contract = Contract(**defaults)
    db.add(contract)
    db.flush()
    return contract


def make_payment(db, student_id=None, recorded_by=None, **kwargs):
    from datetime import datetime

    if student_id is None:
        student = make_student(db)
        student_id = student.id
    if recorded_by is None:
        user = make_user(db)
        recorded_by = user.id
    defaults = {
        "student_id": student_id,
        "amount": Decimal("50.00"),
        "payment_date": datetime.now(UTC),
        "method": "pix",
        "recorded_by": recorded_by,
        "status": "active",
    }
    defaults.update(kwargs)
    payment = Payment(**defaults)
    db.add(payment)
    db.flush()
    return payment
