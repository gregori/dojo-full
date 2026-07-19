"""Step definitions for belt progress and requirements scenarios (Portuguese Gherkin)."""

from datetime import UTC, datetime

from behave import given, then

from app.models import Attendance, Belt, BeltRequirement, Event, EventType


@given('o requisito de "{event_type_name}" para faixa "{belt_name}" é {count:d}')
def step_belt_requirement_set(context, event_type_name, belt_name, count):
    """Create a belt requirement (Portuguese)."""
    db = context.db
    belt = context.belts.get(belt_name) if hasattr(context, "belts") else None
    if belt is None:
        belt = db.query(Belt).filter_by(name=belt_name).first()
    assert belt is not None, f"Belt '{belt_name}' not found"

    event_type = context.event_types.get(event_type_name) if hasattr(context, "event_types") else None
    if event_type is None:
        event_type = db.query(EventType).filter_by(name=event_type_name).first()
    assert event_type is not None, f"Event type '{event_type_name}' not found"

    requirement = BeltRequirement(
        belt_id=belt.id,
        event_type_id=event_type.id,
        required_count=count,
        description=f"{count} {event_type_name}",
    )
    db.add(requirement)
    db.commit()
    context.current_requirement = requirement
    context.requirement_id = requirement.id


@given('existe um requisito de "{event_type_name}" para faixa "{belt_name}" com {count:d}')
def step_belt_requirement_exists(context, event_type_name, belt_name, count):
    """Pre-seed a belt requirement (Portuguese)."""
    step_belt_requirement_set(context, event_type_name, belt_name, count)


@given('o aluno "{name}" tem {count:d} presenças em "{event_type_name}"')
def step_student_has_attendances(context, name, count, event_type_name):
    """Pre-seed multiple attendance records for a student."""
    db = context.db
    student = context.students.get(name) if hasattr(context, "students") else None
    if student is None:
        student = context.current_student
    assert student is not None, f"Student '{name}' not found in context"

    event_type = context.event_types.get(event_type_name) if hasattr(context, "event_types") else None
    if event_type is None:
        event_type = db.query(EventType).filter_by(name=event_type_name).first()
    assert event_type is not None, f"Event type '{event_type_name}' not found"

    from app.models import User

    user = db.query(User).first()

    for i in range(count):
        event = Event(
            title=f"{event_type_name} #{i + 1}",
            event_type_id=event_type.id,
            start_datetime=datetime.now(UTC),
            created_by=user.id if user else "system",
        )
        db.add(event)
        db.flush()

        attendance = Attendance(
            event_id=event.id,
            student_id=student.id,
            check_in_method="tablet",
            check_in_at=datetime.now(UTC),
        )
        db.add(attendance)

    db.commit()


@given('o aluno "{name}" fez check-in no evento "{event_title}"')
def step_student_checked_in_named_event(context, name, event_title):
    """Pre-seed an attendance record for a student at a named event."""
    db = context.db
    student = context.students.get(name) if hasattr(context, "students") else None
    if student is None:
        student = context.current_student
    assert student is not None, f"Student '{name}' not found in context"

    event = context.events.get(event_title) if hasattr(context, "events") else None
    if event is None:
        event = db.query(Event).filter_by(title=event_title).first()
    assert event is not None, f"Event '{event_title}' not found in context"

    attendance = Attendance(
        event_id=event.id,
        student_id=student.id,
        check_in_method="tablet",
        check_in_at=datetime.now(UTC),
    )
    db.add(attendance)
    db.commit()


@then("a resposta deve conter os requisitos de presença")
def step_response_contains_requirements(context):
    """Verify the response contains belt requirements."""
    data = context.response.json()
    has_requirements = False
    if isinstance(data, dict):
        if "requirements" in data:
            has_requirements = True
        elif "progress" in data:
            progress = data["progress"]
            if isinstance(progress, dict) and "requirements" in progress:
                has_requirements = True
    assert has_requirements, f"Response does not contain requirements: {data}"


@then("a resposta deve conter o progresso do aluno")
def step_response_contains_student_progress(context):
    """Verify the response contains student progress information."""
    data = context.response.json()
    has_progress = False
    if isinstance(data, dict):
        if "progress" in data or "current_belt" in data:
            has_progress = True
    assert has_progress, f"Response does not contain progress: {data}"


@then("todas as contagens de presença devem ser 0")
def step_all_attendance_counts_zero(context):
    """Verify all attendance counts in progress are 0."""
    data = context.response.json()
    progress = data.get("progress", data)
    if isinstance(progress, dict) and "requirements" in progress:
        for req in progress["requirements"]:
            completed = req.get("completed", req.get("attended", -1))
            assert completed == 0, f"Expected 0 completed, got {completed}"


@then('a presença em "{event_type_name}" não deve contar para o progresso de "{other_type}"')
def step_attendance_not_count_for_progress(context, event_type_name, other_type):
    """Verify that attendance in a non-counting event type doesn't count for progress."""
    data = context.response.json()
    progress = data.get("progress", data)
    if isinstance(progress, dict) and "requirements" in progress:
        for req in progress["requirements"]:
            if req.get("event_type", {}).get("name") == other_type:
                completed = req.get("completed", req.get("attended", 0))
                assert completed == 0, f"Expected 0 completed for '{other_type}', got {completed}"


@then('a faixa do aluno "{name}" deve ser atualizada para "{belt_name}"')
def step_student_belt_updated(context, name, belt_name):
    """Verify the student's belt was updated in the database."""
    db = context.db
    student = context.students.get(name) if hasattr(context, "students") else None
    if student is None:
        student = context.current_student
    assert student is not None, f"Student '{name}' not found in context"

    db.refresh(student)
    belt = db.query(Belt).filter_by(name=belt_name).first()
    assert belt is not None, f"Belt '{belt_name}' not found"
    assert student.current_belt_id == belt.id, (
        f"Expected belt '{belt_name}' (id={belt.id}), got belt_id={student.current_belt_id}"
    )


@then('a faixa do aluno "{name}" deve permanecer "{belt_name}"')
def step_student_belt_unchanged(context, name, belt_name):
    """Verify the student's belt was NOT changed."""
    step_student_belt_updated(context, name, belt_name)
