from datetime import UTC

from behave import given, then, when

from app.core.security import get_password_hash
from app.models import Belt, Event, EventType, Student, User

# Background steps


@given("the database is empty")
def step_database_is_empty(context):
    """Ensure database is clean. Handled by fixture."""
    pass


@given('belt "{belt_name}" exists for category "{category}" with sort order {sort_order:d}')
def step_belt_exists(context, belt_name, category, sort_order):
    db = context.db
    belt = Belt(name=belt_name, category=category, sort_order=sort_order)
    db.add(belt)
    db.commit()
    context.current_belt = belt


@given('event type "{event_type_name}" exists with color "{color}"')
def step_event_type_exists(context, event_type_name, color):
    db = context.db
    event_type = EventType(name=event_type_name, color=color, counts_for_belt=True)
    db.add(event_type)
    db.commit()
    context.current_event_type = event_type


@given('a student "{student_name}" exists with:')
def step_student_exists_with_colon(context, student_name):
    """Create a student with table data - colon variant for data tables."""
    step_student_exists_with_no_colon(context, student_name)


@given('a student "{student_name}" exists with')
def step_student_exists_with_no_colon(context, student_name):
    """Create a student with table data - no colon variant."""
    db = context.db
    data = {row["field"]: row["value"] for row in context.table}

    belt = context.current_belt if hasattr(context, "current_belt") else None
    if belt is None:
        belt = db.query(Belt).first()

    # Handle belt_name field
    if "belt_name" in data:
        belt_name = data.pop("belt_name")
        belt = context.belts.get(belt_name) if hasattr(context, "belts") else None
        if belt is None:
            belt = db.query(Belt).filter_by(name=belt_name).first()

    student = Student(
        full_name=student_name,
        registration_number=data.get("registration_number", ""),
        pin=get_password_hash(data.get("pin", "1234")),
        category=data.get("category", "adult"),
        current_belt_id=belt.id if belt else None,
    )
    db.add(student)
    db.commit()
    context.current_student = student


@given('an event "{event_title}" exists with type "{event_type_name}"')
def step_event_exists(context, event_title, event_type_name):
    db = context.db
    event_type = db.query(EventType).filter_by(name=event_type_name).first()
    if not event_type:
        raise Exception(f"Event type '{event_type_name}' not found. Create it first.")

    # Create a mock user if needed
    user = db.query(User).first()
    if not user:
        user = User(
            email="test@dojo.com",
            password_hash=get_password_hash("test123"),
            full_name="Test User",
            role="admin",
        )
        db.add(user)
        db.commit()

    from datetime import datetime

    event = Event(
        title=event_title,
        event_type_id=event_type.id,
        start_datetime=datetime.now(UTC),
        created_by=user.id,
    )
    db.add(event)
    db.commit()
    context.current_event = event
    context.event_id = event.id


@given('a user exists with email "{email}" and password "{password}" and role "{role}"')
def step_user_exists(context, email, password, role):
    db = context.db
    user = User(
        email=email,
        password_hash=get_password_hash(password),
        full_name="Test User",
        role=role,
    )
    db.add(user)
    db.commit()
    context.current_user = user


@given("the event has a valid check-in token")
def step_event_has_token(context):
    if not hasattr(context, "current_event"):
        raise Exception("No current event. Create an event first.")
    context.current_event_token = context.current_event.check_in_token


@given("the student has already checked in to the event")
def step_student_already_checked_in(context):
    db = context.db
    if not hasattr(context, "current_student") or not hasattr(context, "current_event"):
        raise Exception("Need student and event first.")

    from datetime import datetime

    from app.models import Attendance

    attendance = Attendance(
        event_id=context.current_event.id,
        student_id=context.current_student.id,
        check_in_method="tablet",
        check_in_at=datetime.now(UTC),
    )
    db.add(attendance)
    db.commit()


# When steps (English)


@when('I send a POST request to "{endpoint}" with:')
def step_send_post_request_with_table(context, endpoint):
    """Send a POST request with table data - colon variant for data tables."""
    data = {row["field"]: row["value"] for row in context.table}
    headers = {}
    if hasattr(context, "user_token") and context.user_token:
        headers["Authorization"] = f"Bearer {context.user_token}"
    context.response = context.client.post(endpoint, json=data, headers=headers)


@when('I send a POST request to "{endpoint}" with')
def step_send_post_request(context, endpoint):
    """Send a POST request with table data - no colon variant."""
    data = {row["field"]: row["value"] for row in context.table}
    headers = {}
    if hasattr(context, "user_token") and context.user_token:
        headers["Authorization"] = f"Bearer {context.user_token}"
    context.response = context.client.post(endpoint, json=data, headers=headers)


@when("the student checks in with:")
def step_student_checks_in_with_colon(context):
    """Student check-in - colon variant for data tables."""
    data = {row["field"]: row["value"] for row in context.table}
    event_id = context.event_id if hasattr(context, "event_id") else context.current_event.id
    context.response = context.client.post(f"/api/v1/checkin/tablet/{event_id}", json=data)


@when("the student checks in with")
def step_student_checks_in(context):
    """Student check-in - no colon variant."""
    data = {row["field"]: row["value"] for row in context.table}
    event_id = context.event_id if hasattr(context, "event_id") else context.current_event.id
    context.response = context.client.post(f"/api/v1/checkin/tablet/{event_id}", json=data)


@when("the student checks in via QR code with:")
def step_student_checks_in_qr_with_colon(context):
    """Student QR check-in - colon variant for data tables."""
    data = {row["field"]: row["value"] for row in context.table}
    if data.get("check_in_token") == "<token>":
        data["check_in_token"] = context.current_event_token
    context.response = context.client.post("/api/v1/checkin/qr", json=data)


@when("the student checks in via QR code with")
def step_student_checks_in_qr(context):
    """Student QR check-in - no colon variant."""
    data = {row["field"]: row["value"] for row in context.table}
    if data.get("check_in_token") == "<token>":
        data["check_in_token"] = context.current_event_token
    context.response = context.client.post("/api/v1/checkin/qr", json=data)


# Then steps (English)


@then("the response status should be {status_code:d}")
def step_response_status(context, status_code):
    assert context.response.status_code == status_code, (
        f"Expected {status_code}, got {context.response.status_code}: {context.response.text}"
    )


@then("the response should contain a valid access token")
def step_response_contains_token(context):
    data = context.response.json()
    assert "access_token" in data, f"Response does not contain access_token: {data}"
    assert len(data["access_token"]) > 0
    context.user_token = data["access_token"]
    context.client.headers["Authorization"] = f"Bearer {context.user_token}"


@then('the response should contain "{field}" with value "{expected_value}"')
def step_response_contains_field(context, field, expected_value):
    data = context.response.json()
    actual = data.get(field, f"<field '{field}' not found>")
    assert str(actual) == expected_value, f"Expected '{field}' to be '{expected_value}', got '{actual}'"


@then('the user role in the token should be "{expected_role}"')
def step_token_contains_role(context, expected_role):
    from jose import jwt

    from app.core.config import get_settings

    token = context.user_token
    settings = get_settings()
    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])

    assert payload.get("role") == expected_role, f"Expected role '{expected_role}', got '{payload.get('role')}'"


@then("the student attendance should be recorded for the event")
def step_attendance_recorded(context):
    from app.models import Attendance

    db = context.db

    attendance = (
        db.query(Attendance)
        .filter_by(
            student_id=context.current_student.id,
            event_id=context.current_event.id,
        )
        .first()
    )

    assert attendance is not None, "Attendance was not recorded"


@then("the response should contain the student progress information")
def step_response_contains_progress(context):
    data = context.response.json()
    assert "progress" in data, f"Response does not contain progress: {data}"
    progress = data["progress"]
    assert "current_belt" in progress, f"Progress does not contain current_belt: {progress}"


@then("no attendance should be recorded")
def step_no_attendance_recorded(context):
    from app.models import Attendance

    db = context.db

    count = (
        db.query(Attendance)
        .filter_by(
            student_id=context.current_student.id,
            event_id=context.current_event.id,
        )
        .count()
    )

    assert count == 0, f"Expected 0 attendances, found {count}"


@then('the check-in method should be "{method}"')
def step_checkin_method(context, method):
    from app.models import Attendance

    db = context.db

    attendance = (
        db.query(Attendance)
        .filter_by(
            student_id=context.current_student.id,
            event_id=context.current_event.id,
        )
        .first()
    )

    assert attendance is not None, "Attendance not found"
    assert attendance.check_in_method == method, (
        f"Expected check_in_method '{method}', got '{attendance.check_in_method}'"
    )


# ============================================================
# Portuguese Gherkin step definitions (shared across features)
# ============================================================


@given("o banco de dados está vazio")
def step_database_is_empty_pt(context):
    """Ensure database is clean (Portuguese). Handled by fixture."""
    pass


@given('existe uma faixa "{belt_name}" para categoria "{category}" com ordem {sort_order:d}')
def step_belt_exists_pt(context, belt_name, category, sort_order):
    """Create a belt (Portuguese)."""
    db = context.db
    belt = Belt(name=belt_name, category=category, sort_order=sort_order)
    db.add(belt)
    db.commit()
    # Store by name for multi-belt scenarios
    if not hasattr(context, "belts"):
        context.belts = {}
    context.belts[belt_name] = belt
    context.current_belt = belt
    context.belt_id = belt.id


@given('existe um tipo de evento "{event_type_name}" com cor "{color}"')
def step_event_type_exists_pt(context, event_type_name, color):
    """Create an event type (Portuguese)."""
    db = context.db
    event_type = EventType(name=event_type_name, color=color, counts_for_belt=True)
    db.add(event_type)
    db.commit()
    if not hasattr(context, "event_types"):
        context.event_types = {}
    context.event_types[event_type_name] = event_type
    context.current_event_type = event_type
    context.event_type_id = event_type.id


@given('existe um tipo de evento "{event_type_name}" com cor "{color}" e não conta para faixa')
def step_event_type_exists_no_belt_pt(context, event_type_name, color):
    """Create an event type that does NOT count for belt progress (Portuguese)."""
    db = context.db
    event_type = EventType(name=event_type_name, color=color, counts_for_belt=False)
    db.add(event_type)
    db.commit()
    if not hasattr(context, "event_types"):
        context.event_types = {}
    context.event_types[event_type_name] = event_type
    context.current_event_type = event_type
    context.event_type_id = event_type.id


@given('existe um usuário com email "{email}" e senha "{password}" e papel "{role}"')
def step_user_exists_pt(context, email, password, role):
    """Create a user (Portuguese)."""
    db = context.db
    user = User(
        email=email,
        password_hash=get_password_hash(password),
        full_name=f"Test {role.title()}",
        role=role,
    )
    db.add(user)
    db.commit()
    if not hasattr(context, "users"):
        context.users = {}
    context.users[email] = user
    context.current_user = user
    # Store user_id for placeholder resolution (e.g., <sensei_user_id>)
    user_id_key = email.split("@")[0].replace(".", "_").replace("+", "_") + "_user_id"
    setattr(context, user_id_key, user.id)


@given('existe um aluno "{name}" com matrícula "{reg}" e PIN "{pin}" e categoria "{category}"')
def step_student_exists_pt(context, name, reg, pin, category):
    """Create a student (Portuguese)."""
    db = context.db
    belt = context.current_belt if hasattr(context, "current_belt") else None
    if belt is None:
        belt = db.query(Belt).filter_by(category=category).first()
    if belt is None:
        belt = db.query(Belt).first()
    if belt is None:
        belt = Belt(name="Branca", category=category, sort_order=1)
        db.add(belt)
        db.commit()
        if not hasattr(context, "belts"):
            context.belts = {}
        context.belts[belt.name] = belt
        context.current_belt = belt
        context.belt_id = belt.id

    student = Student(
        full_name=name,
        registration_number=reg,
        pin=get_password_hash(pin),
        category=category,
        current_belt_id=belt.id if belt else None,
    )
    db.add(student)
    db.commit()
    if not hasattr(context, "students"):
        context.students = {}
    context.students[name] = student
    context.current_student = student
    context.student_id = student.id


@given('existe um evento "{title}" com tipo "{type_name}"')
def step_event_exists_pt(context, title, type_name):
    """Create an event (Portuguese)."""
    db = context.db
    event_type = db.query(EventType).filter_by(name=type_name).first()
    if not event_type:
        raise Exception(f"Event type '{type_name}' not found. Create it first.")

    # Ensure a user exists for created_by
    user = db.query(User).first()
    if not user:
        user = User(
            email="test@dojo.com",
            password_hash=get_password_hash("test123"),
            full_name="Test User",
            role="admin",
        )
        db.add(user)
        db.commit()

    from datetime import datetime

    event = Event(
        title=title,
        event_type_id=event_type.id,
        start_datetime=datetime.now(UTC),
        created_by=user.id,
    )
    db.add(event)
    db.commit()
    if not hasattr(context, "events"):
        context.events = {}
    context.events[title] = event
    context.current_event = event
    context.event_id = event.id
    context.event_type_id = event_type.id


@when("o aluno faz check-in com:")
def step_student_checks_in_pt_colon(context):
    """Student check-in (Portuguese) - colon variant for data tables."""
    data = {row["field"]: row["value"] for row in context.table}
    data = _resolve_placeholders(context, data)
    event_id = context.event_id if hasattr(context, "event_id") else context.current_event.id
    context.response = context.client.post(f"/api/v1/checkin/tablet/{event_id}", json=data)


@when("o aluno faz check-in com")
def step_student_checks_in_pt(context):
    """Student check-in (Portuguese) - no colon variant."""
    data = {row["field"]: row["value"] for row in context.table}
    data = _resolve_placeholders(context, data)
    event_id = context.event_id if hasattr(context, "event_id") else context.current_event.id
    context.response = context.client.post(f"/api/v1/checkin/tablet/{event_id}", json=data)


def _resolve_placeholders(context, data, endpoint=""):
    """Resolve <placeholder> values in request data from context attributes."""
    resolved = {}
    for key, value in data.items():
        if isinstance(value, str) and value.startswith("<") and value.endswith(">"):
            placeholder = value.strip("<>")
            resolved_value = getattr(context, placeholder, value)
            resolved[key] = str(resolved_value) if resolved_value != value else value
        else:
            resolved[key] = value
    if "belt_id" in resolved and "current_belt_id" not in resolved and "/students" in endpoint:
        resolved["current_belt_id"] = resolved.pop("belt_id")
    return resolved
