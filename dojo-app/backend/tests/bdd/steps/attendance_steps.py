"""Step definitions for attendance management scenarios (Portuguese Gherkin)."""
from datetime import datetime, timezone

from behave import given, when, then

from app.models import Attendance


@given('o aluno "{name}" fez check-in no evento')
def step_student_checked_in_event(context, name):
    """Pre-seed an attendance record for a student at the current event."""
    db = context.db
    student = context.students.get(name) if hasattr(context, 'students') else None
    if student is None:
        student = context.current_student
    assert student is not None, f"Student '{name}' not found in context"

    event = context.current_event if hasattr(context, 'current_event') else None
    assert event is not None, "No current event in context"

    attendance = Attendance(
        event_id=event.id,
        student_id=student.id,
        check_in_method="tablet",
        check_in_at=datetime.now(timezone.utc),
    )
    db.add(attendance)
    db.commit()


@given('o aluno "{name}" fez check-in no evento via "{method}"')
def step_student_checked_in_event_via(context, name, method):
    """Pre-seed an attendance record with a specific check-in method."""
    db = context.db
    student = context.students.get(name) if hasattr(context, 'students') else None
    if student is None:
        student = context.current_student
    assert student is not None, f"Student '{name}' not found in context"

    event = context.current_event if hasattr(context, 'current_event') else None
    assert event is not None, "No current event in context"

    attendance = Attendance(
        event_id=event.id,
        student_id=student.id,
        check_in_method=method,
        check_in_at=datetime.now(timezone.utc),
    )
    db.add(attendance)
    db.commit()


@when('o aluno "{name}" faz check-in com')
def step_student_checks_in_by_name(context, name):
    """Student check-in by name (Portuguese)."""
    import requests
    data = {row['field']: row['value'] for row in context.table}

    event_id = context.event_id if hasattr(context, 'event_id') else context.current_event.id
    url = context.base_url + f"/api/v1/checkin/tablet/{event_id}"
    context.response = requests.post(url, json=data)


@then('a resposta deve conter uma lista vazia de presenças')
def step_response_empty_attendance_list(context):
    """Verify the response is an empty attendance list."""
    data = context.response.json()
    assert isinstance(data, list), f"Expected a list, got {type(data)}"
    assert len(data) == 0, f"Expected empty list, got {len(data)} items"


@then('a lista de presenças deve conter "{name}"')
def step_attendance_list_contains(context, name):
    """Verify a student name appears in the attendance list."""
    data = context.response.json()
    if isinstance(data, list):
        names = [item.get('student_name', item.get('full_name', '')) for item in data]
        assert name in names, f"Expected '{name}' in attendance list: {names}"
    else:
        assert False, f"Expected a list, got {type(data)}"


@then('a lista de presenças não deve conter "{name}"')
def step_attendance_list_not_contains(context, name):
    """Verify a student name does NOT appear in the attendance list."""
    data = context.response.json()
    if isinstance(data, list):
        names = [item.get('student_name', item.get('full_name', '')) for item in data]
        assert name not in names, f"Expected '{name}' NOT in attendance list: {names}"
    else:
        assert False, f"Expected a list, got {type(data)}"


@then('a presença de "{name}" deve ter método "{method}"')
def step_attendance_method_for_student(context, name, method):
    """Verify the check-in method for a specific student in the attendance list."""
    data = context.response.json()
    if isinstance(data, list):
        for item in data:
            student_name = item.get('student_name', item.get('full_name', ''))
            if student_name == name:
                assert item.get('check_in_method') == method, \
                    f"Expected method '{method}' for '{name}', got '{item.get('check_in_method')}'"
                return
        assert False, f"Student '{name}' not found in attendance list"
    else:
        assert False, f"Expected a list, got {type(data)}"


@then('a lista de presenças deve conter {count:d} alunos')
def step_attendance_list_count(context, count):
    """Verify the attendance list has a specific number of entries."""
    data = context.response.json()
    assert isinstance(data, list), f"Expected a list, got {type(data)}"
    assert len(data) == count, f"Expected {count} attendance records, got {len(data)}"


@then('o método de check-in deve ser "{method}"')
def step_checkin_method_pt(context, method):
    """Verify the check-in method in the response or database."""
    data = context.response.json()
    if isinstance(data, dict) and "check_in_method" in data:
        assert data["check_in_method"] == method, \
            f"Expected check_in_method '{method}', got '{data['check_in_method']}'"
    else:
        db = context.db
        student = context.current_student
        event = context.current_event
        attendance = db.query(Attendance).filter_by(
            student_id=student.id,
            event_id=event.id,
        ).first()
        assert attendance is not None, "Attendance not found"
        assert attendance.check_in_method == method, \
            f"Expected check_in_method '{method}', got '{attendance.check_in_method}'"