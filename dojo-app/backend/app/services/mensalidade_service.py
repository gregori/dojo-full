"""Business rules for generating monthly charges (mensalidades): proration and idempotent generation."""

import calendar
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Mensalidade, Student
from app.services.balance_service import BalanceService
from app.services.student_plan_service import StudentPlanService

DUE_DAY = 5


def _month_start(reference: datetime) -> datetime:
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    return datetime(reference.year, reference.month, 1, tzinfo=UTC)


def _due_date_for(month_start: datetime) -> datetime:
    return month_start + timedelta(days=DUE_DAY - 1)


def _prorate(price: Decimal, effective_date: datetime, month_start: datetime) -> Decimal:
    """Daily pro-rata (D6): price * days_remaining_including_effective_day / total_days_in_month."""
    total_days = calendar.monthrange(month_start.year, month_start.month)[1]
    days_remaining = total_days - effective_date.day + 1
    prorated = price * Decimal(days_remaining) / Decimal(total_days)
    return prorated.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class MensalidadeService:
    """Generate monthly charges idempotently, and expose a student's charge history."""

    @staticmethod
    def get_student_charges(db: Session, student_id: str) -> list[dict]:
        """A student's mensalidades with computed status per row (D4)."""
        return BalanceService.get_student_charges_with_status(db, student_id)

    @staticmethod
    def generate_monthly_charges(db: Session, reference_month: datetime | None = None) -> dict:
        """Idempotently create one mensalidade per active, plan-assigned student for the reference month.

        Safe to invoke repeatedly: the unique ``(student_id, reference_month)``
        constraint skips students who already have a row for that month. Plan
        assignment is its own explicit action (at enrollment/plan-change, tied
        to contract signing) -- an active student with no ``StudentPlan`` yet
        is skipped here, the same way an inactive student is, rather than
        being auto-assigned one.
        """
        month_start = _month_start(reference_month or datetime.now(UTC))
        due_date = _due_date_for(month_start)

        created_count = 0
        skipped_count = 0
        students = db.query(Student).filter(Student.is_active.is_(True)).all()
        for student in students:
            existing = (
                db.query(Mensalidade)
                .filter(Mensalidade.student_id == student.id, Mensalidade.reference_month == month_start)
                .first()
            )
            if existing:
                skipped_count += 1
                continue

            student_plan = StudentPlanService.get_active(db, student.id)
            if not student_plan:
                skipped_count += 1
                continue

            started_at = student_plan.started_at
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=UTC)
            price = student_plan.plan_version.price
            if started_at.year == month_start.year and started_at.month == month_start.month:
                amount = _prorate(price, started_at, month_start)
            else:
                amount = price

            mensalidade = Mensalidade(
                student_id=student.id,
                plan_version_id=student_plan.plan_version_id,
                reference_month=month_start,
                due_date=due_date,
                amount=amount,
            )
            db.add(mensalidade)
            try:
                db.commit()
                created_count += 1
            except IntegrityError:
                # A concurrent generation run may have created the same row first.
                db.rollback()
                skipped_count += 1

        return {"reference_month": month_start, "created_count": created_count, "skipped_count": skipped_count}
