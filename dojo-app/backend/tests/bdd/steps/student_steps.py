"""Step definitions for student management scenarios (Portuguese Gherkin)."""

from behave import given, then


@given('o aluno "{name}" foi inativado')
def step_student_deactivated(context, name):
    """Deactivate a student in the database."""
    db = context.db
    student = context.students.get(name) if hasattr(context, "students") else None
    if student is None:
        student = context.current_student
    assert student is not None, f"Student '{name}' not found in context"
    student.is_active = False
    db.commit()
    # Update context so <student_id> resolves to this student
    context.student_id = student.id
    context.current_student = student


@then("a resposta deve conter uma lista de alunos")
def step_response_contains_student_list(context):
    """Verify the response is a list of students."""
    data = context.response.json()
    assert isinstance(data, list), f"Expected a list, got {type(data)}"


@then('a lista deve conter "{name}"')
def step_list_contains_name(context, name):
    """Verify a name appears in the response list."""
    data = context.response.json()
    if isinstance(data, list):
        names = [item.get("full_name", item.get("title", "")) for item in data]
        assert name in names, f"Expected '{name}' in {names}"
    else:
        assert False, f"Expected a list, got {type(data)}"


@then('a lista não deve conter "{name}"')
def step_list_not_contains_name(context, name):
    """Verify a name does NOT appear in the response list."""
    data = context.response.json()
    if isinstance(data, list):
        names = [item.get("full_name", item.get("title", "")) for item in data]
        assert name not in names, f"Expected '{name}' NOT in {names}"
    else:
        assert False, f"Expected a list, got {type(data)}"


@then("o aluno deve estar inativo no banco de dados")
def step_student_inactive_in_db(context):
    """Verify the student is inactive in the database."""
    db = context.db
    student = context.current_student
    db.refresh(student)
    assert student.is_active is False, f"Student should be inactive but is_active={student.is_active}"


@then("a resposta deve conter a nova faixa")
def step_response_contains_new_belt(context):
    """Verify the response contains the updated belt information."""
    data = context.response.json()
    assert "current_belt_id" in data or "current_belt" in data, f"Response does not contain belt info: {data}"


@then("o PIN deve ter 4 dígitos")
def step_pin_has_4_digits(context):
    """Verify the student PIN is 4 digits."""
    data = context.response.json()
    pin = data.get("pin", "")
    assert len(str(pin)) == 4, f"Expected PIN to be 4 digits, got '{pin}'"


@then("a matrícula deve ser diferente do primeiro aluno")
def step_registration_is_unique(context):
    """Verify the registration number is different from the first student's."""
    data = context.response.json()
    if hasattr(context, "first_student_reg"):
        assert data.get("registration_number") != context.first_student_reg, "Registration number should be unique"
    context.first_student_reg = data.get("registration_number")
