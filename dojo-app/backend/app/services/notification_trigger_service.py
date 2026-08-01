"""Daily/hourly threshold-crossing detection for the three notification types.

All three statuses this feature keys off of are computed on read, not stored
(requirements.md Constraints) -- each routine below performs its own
date-arithmetic against the exact calendar day a threshold is crossed, using
the same app-wide America/Sao_Paulo timezone module recurring-event-series
already introduced (app.core.timezone), not a bare datetime.now(UTC).

Each routine narrows its own SQL query to the single relevant calendar day
(mirroring MedicalExamService.get_dashboard/BalanceService.get_overdue_dashboard's
existing "narrow SQL filter, then a Python loop for anything conditional" style),
then applies NH-06's idempotent create-or-skip via NotificationService.create_if_new,
sending a push only for the row that actually just fired (see plan.md Autocritica).
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.core.timezone import APP_TIMEZONE, local_today
from app.models import Event, MedicalExam, Mensalidade, PreCheckIn, Student
from app.services.balance_service import BalanceService
from app.services.notification_service import NotificationService
from app.services.push_service import PushService

PRE_CHECKIN_LEAD = timedelta(days=1)
MEDICAL_EXAM_LEAD = timedelta(days=30)
MENSALIDADE_LEAD = timedelta(days=7)


def _day_bounds_utc(local_date: date) -> tuple[datetime, datetime]:
    """UTC instant range spanning one full America/Sao_Paulo calendar day."""
    start = datetime.combine(local_date, time.min, tzinfo=APP_TIMEZONE)
    end = datetime.combine(local_date, time.max, tzinfo=APP_TIMEZONE)
    return start, end


class NotificationTriggerService:
    @staticmethod
    def check_pre_checkin_reminders(db: Session) -> int:
        """NH-03: events starting exactly PRE_CHECKIN_LEAD from today, no exclusions by event_type_id."""
        target_date = local_today() + PRE_CHECKIN_LEAD
        start, end = _day_bounds_utc(target_date)
        events = db.query(Event).filter(Event.status != "cancelled", Event.start_datetime.between(start, end)).all()
        active_students = db.query(Student).filter(Student.is_active.is_(True)).all()
        fired = 0
        for event in events:
            checked_in_ids = {
                pc.student_id
                for pc in db.query(PreCheckIn).filter(
                    PreCheckIn.event_id == event.id, PreCheckIn.status.in_(("confirmed", "converted"))
                )
            }
            for student in active_students:
                if student.id in checked_in_ids:
                    continue
                if event.minimum_belt_id and (
                    not student.current_belt or student.current_belt.sort_order < event.minimum_belt.sort_order
                ):
                    continue
                message = (
                    f'Falta pouco! Faça seu pré-check-in para "{event.title}" '
                    f"em {event.start_datetime.astimezone(APP_TIMEZONE):%d/%m/%Y %H:%M}."
                )
                notification = NotificationService.create_if_new(
                    db, student.id, "pre_checkin_reminder", event.id, message
                )
                if notification:
                    PushService.send_to_student(db, student, "Pré-check-in pendente", message)
                    fired += 1
        return fired

    @staticmethod
    def check_medical_exam_reminders(db: Session) -> int:
        """NH-04: active exams expiring exactly MEDICAL_EXAM_LEAD from today."""
        target_date = local_today() + MEDICAL_EXAM_LEAD
        start, end = _day_bounds_utc(target_date)
        exams = (
            db.query(MedicalExam)
            .filter(MedicalExam.status == "active", MedicalExam.expires_at.between(start, end))
            .all()
        )
        fired = 0
        for exam in exams:
            message = (
                f"Seu exame médico vence em {exam.expires_at.astimezone(APP_TIMEZONE):%d/%m/%Y}. "
                "Providencie a renovação."
            )
            notification = NotificationService.create_if_new(
                db, exam.student_id, "medical_exam_expiring", exam.id, message
            )
            if notification:
                PushService.send_to_student(db, exam.student, "Exame médico vencendo", message)
                fired += 1
        return fired

    @staticmethod
    def check_mensalidade_reminders(db: Session) -> int:
        """NH-05: mensalidades due exactly MENSALIDADE_LEAD from today, unless already fully paid.

        Reuses BalanceService.get_student_charges_with_status (the one
        authoritative paid/overdue/partial/open computation) rather than
        reimplementing "is this paid" -- directly addresses the Constraints
        section's warning against a second, subtly different computation.
        """
        target_date = local_today() + MENSALIDADE_LEAD
        start, end = _day_bounds_utc(target_date)
        mensalidades = db.query(Mensalidade).filter(Mensalidade.due_date.between(start, end)).all()
        fired = 0
        for mensalidade in mensalidades:
            charges = BalanceService.get_student_charges_with_status(db, mensalidade.student_id)
            charge = next((c for c in charges if c["id"] == mensalidade.id), None)
            if not charge or charge["status"] == "paid":
                continue
            message = (
                f"Sua mensalidade de {mensalidade.reference_month.astimezone(APP_TIMEZONE):%m/%Y} "
                f"vence em {mensalidade.due_date.astimezone(APP_TIMEZONE):%d/%m/%Y}."
            )
            notification = NotificationService.create_if_new(
                db, mensalidade.student_id, "mensalidade_due", mensalidade.id, message
            )
            if notification:
                PushService.send_to_student(db, mensalidade.student, "Mensalidade a vencer", message)
                fired += 1
        return fired
