"""Step definitions for exam management scenarios (Portuguese Gherkin)."""
from datetime import datetime, timezone

from behave import given, when, then

from app.models import Exam, ExamParticipant, ExamBoardMember, Belt


@given('existe um exame para o evento "{event_title}" com faixa "{belt_name}"')
def step_exam_exists(context, event_title, belt_name):
    """Create an exam for a given event and belt."""
    db = context.db
    event = context.events.get(event_title) if hasattr(context, 'events') else None
    if event is None:
        from app.models import Event
        event = db.query(Event).filter_by(title=event_title).first()
    assert event is not None, f"Event '{event_title}' not found in context"

    belt = context.belts.get(belt_name) if hasattr(context, 'belts') else None
    if belt is None:
        belt = db.query(Belt).filter_by(name=belt_name).first()
    assert belt is not None, f"Belt '{belt_name}' not found"

    user = context.current_user if hasattr(context, 'current_user') else None
    if user is None:
        from app.models import User
        user = db.query(User).first()

    exam = Exam(
        event_id=event.id,
        belt_id=belt.id,
        exam_date=datetime.now(timezone.utc),
        status="scheduled",
        notes="",
        created_by=user.id if user else "system",
    )
    db.add(exam)
    db.commit()
    context.current_exam = exam
    context.exam_id = exam.id


@given('existe um membro na banca do exame com usuário "{email}" como "{role}"')
def step_exam_board_member_exists(context, email, role):
    """Pre-seed a board member for the current exam."""
    db = context.db
    user = context.users.get(email) if hasattr(context, 'users') else None
    if user is None:
        from app.models import User
        user = db.query(User).filter_by(email=email).first()
    assert user is not None, f"User '{email}' not found in context"

    exam = context.current_exam if hasattr(context, 'current_exam') else None
    assert exam is not None, "No current exam in context"

    board_member = ExamBoardMember(
        exam_id=exam.id,
        user_id=user.id,
        role_in_board=role,
    )
    db.add(board_member)
    db.commit()


@given('existe um participante "{role}" no exame com aluno "{name}"')
def step_exam_participant_exists(context, role, name):
    """Pre-seed a participant (candidate or uke) for the current exam."""
    db = context.db
    student = context.students.get(name) if hasattr(context, 'students') else None
    if student is None:
        student = context.current_student
    assert student is not None, f"Student '{name}' not found in context"

    exam = context.current_exam if hasattr(context, 'current_exam') else None
    assert exam is not None, "No current exam in context"

    participant = ExamParticipant(
        exam_id=exam.id,
        student_id=student.id,
        role=role,
        status="pending",
        is_eligible=True,
    )
    db.add(participant)
    db.commit()
    context.current_participant = participant
    context.participant_id = participant.id


@then('o exame deve ter {count:d} membros na banca')
def step_exam_board_member_count(context, count):
    """Verify the number of board members in the current exam."""
    db = context.db
    exam = context.current_exam if hasattr(context, 'current_exam') else None
    assert exam is not None, "No current exam in context"

    member_count = db.query(ExamBoardMember).filter_by(exam_id=exam.id).count()
    assert member_count == count, \
        f"Expected {count} board members, got {member_count}"


@then('o resultado deve ser "{status}"')
def step_exam_result_status(context, status):
    """Verify the exam result status."""
    data = context.response.json()
    assert data.get("status") == status, \
        f"Expected status '{status}', got '{data.get('status')}'"