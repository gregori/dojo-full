"""Read-only report aggregation across belt exams, attendance, and finance (REP-01-REP-04).

Each function returns plain ``dict``/``list[dict]`` data (not ORM objects), so
the same shape can feed both the JSON preview response and the
``report_export_service`` renderers without a second query. No writes happen
here, mirroring ``BalanceService``'s "computed on read" discipline.
"""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Attendance, BeltPromotion, Event, EventType, Exam, ExamParticipant, Payment, Student
from app.services.balance_service import BalanceService
from app.services.student_plan_service import StudentPlanService


def _ensure_utc(value: datetime) -> datetime:
    """Attach UTC to a naive datetime so range comparisons never raise."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _resolve_date_range(start_date: datetime | None, end_date: datetime | None) -> tuple[datetime, datetime]:
    """Default an omitted range to the current calendar month; 400 on ``start_date > end_date``."""
    now = datetime.now(UTC)
    if start_date is None:
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_date = _ensure_utc(start_date)
    if end_date is None:
        end_date = now
    else:
        end_date = _ensure_utc(end_date)

    if start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date must not be after end_date")
    return start_date, end_date


class ReportService:
    """Query/aggregation functions backing the instructor/admin reports (REP-01-REP-04)."""

    @staticmethod
    def get_belt_exam_report(db: Session, student_id: str) -> dict:
        """Per-student exam participations (most recent first) plus any resulting promotion (REP-01)."""
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        participants = (
            db.query(ExamParticipant)
            .join(Exam, ExamParticipant.exam_id == Exam.id)
            .filter(ExamParticipant.student_id == student_id)
            .order_by(Exam.exam_date.desc())
            .all()
        )

        participations = []
        for participant in participants:
            exam = participant.exam
            promotion = None
            if participant.status == "approved":
                promotion = (
                    db.query(BeltPromotion)
                    .filter(BeltPromotion.student_id == student_id, BeltPromotion.exam_id == exam.id)
                    .first()
                )
            participations.append(
                {
                    "exam_id": exam.id,
                    "exam_date": exam.exam_date,
                    "target_belt_name": exam.belt.name,
                    "role": participant.role,
                    "status": participant.status,
                    "override_eligibility": participant.override_eligibility,
                    "override_reason": participant.override_reason,
                    "promoted_at": promotion.promoted_at if promotion else None,
                    "promoted_belt_name": promotion.belt.name if promotion else None,
                }
            )

        return {
            "student_id": student.id,
            "student_name": student.full_name,
            "participations": participations,
        }

    @staticmethod
    def get_student_attendance_report(
        db: Session, student_id: str, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> dict:
        """A single student's attendance in a date range, plus a total count (REP-02)."""
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        start_date, end_date = _resolve_date_range(start_date, end_date)

        attendances = (
            db.query(Attendance)
            .filter(
                Attendance.student_id == student_id,
                Attendance.check_in_at >= start_date,
                Attendance.check_in_at <= end_date,
            )
            .order_by(Attendance.check_in_at.asc())
            .all()
        )

        items = [
            {
                "event_title": attendance.event.title,
                "event_type_name": attendance.event.event_type.name,
                "check_in_at": attendance.check_in_at,
                "check_in_method": attendance.check_in_method,
            }
            for attendance in attendances
        ]

        return {
            "student_id": student.id,
            "student_name": student.full_name,
            "total_attendances": len(items),
            "attendances": items,
        }

    @staticmethod
    def get_class_attendance_report(
        db: Session, event_type_id: str, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> dict:
        """Per-event attendance counts and a per-student roster for one ``EventType`` (REP-03).

        The roster includes only students with at least one attendance in
        range -- there is no "enrolled in this EventType" concept in the
        schema to define a zero-attendance roster against.
        """
        event_type = db.query(EventType).filter(EventType.id == event_type_id).first()
        if not event_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event type not found")

        start_date, end_date = _resolve_date_range(start_date, end_date)

        events = (
            db.query(Event)
            .filter(
                Event.event_type_id == event_type_id,
                Event.start_datetime >= start_date,
                Event.start_datetime <= end_date,
            )
            .order_by(Event.start_datetime.asc())
            .all()
        )

        event_items = []
        roster_by_student: dict[str, dict] = {}
        for event in events:
            attendances = db.query(Attendance).filter(Attendance.event_id == event.id).all()
            event_items.append(
                {
                    "event_id": event.id,
                    "event_title": event.title,
                    "start_datetime": event.start_datetime,
                    "attendance_count": len(attendances),
                }
            )
            for attendance in attendances:
                entry = roster_by_student.setdefault(
                    attendance.student_id,
                    {
                        "student_id": attendance.student_id,
                        "student_name": attendance.student.full_name,
                        "total_attendances": 0,
                    },
                )
                entry["total_attendances"] += 1

        roster = sorted(roster_by_student.values(), key=lambda item: item["student_name"])

        return {
            "event_type_id": event_type.id,
            "event_type_name": event_type.name,
            "events": event_items,
            "roster": roster,
        }

    @staticmethod
    def get_financial_report(
        db: Session,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        months_ahead: int = 3,
    ) -> dict:
        """Payments in range, the current delinquency dashboard, and a revenue projection (REP-04).

        The projection is the already-resolved simple model: the sum of every
        active student's current locked plan price, times ``months_ahead``,
        with no adjustment for historical delinquency/cancellation.
        """
        if months_ahead < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="months_ahead must be at least 1")

        start_date, end_date = _resolve_date_range(start_date, end_date)

        payments = (
            db.query(Payment)
            .filter(
                Payment.status == "active",
                Payment.payment_date >= start_date,
                Payment.payment_date <= end_date,
            )
            .order_by(Payment.payment_date.asc())
            .all()
        )
        payment_items = [
            {
                "id": payment.id,
                "student_id": payment.student_id,
                "student_name": payment.student.full_name,
                "amount": payment.amount,
                "payment_date": payment.payment_date,
                "method": payment.method,
            }
            for payment in payments
        ]

        delinquency = BalanceService.get_overdue_dashboard(db)

        active_students = db.query(Student).filter(Student.is_active.is_(True)).all()
        monthly_total = Decimal("0")
        for student in active_students:
            price = StudentPlanService.get_current_price(db, student.id)
            if price is not None:
                monthly_total += price

        return {
            "payments": payment_items,
            "delinquency": delinquency,
            "projection": {
                "monthly_total": monthly_total,
                "months_ahead": months_ahead,
                "projected_total": monthly_total * months_ahead,
            },
        }
