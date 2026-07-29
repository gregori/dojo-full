"""Business rules for locking a student to a plan tier's current priced version."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import PlanTier, Student, StudentPlan
from app.services.plan_service import PlanService


class StudentPlanService:
    """Assign students to plan versions, locking the price at assignment time (D11)."""

    @staticmethod
    def get_active(db: Session, student_id: str) -> StudentPlan | None:
        """Return a student's current active plan assignment, if any."""
        return (
            db.query(StudentPlan).filter(StudentPlan.student_id == student_id, StudentPlan.status == "active").first()
        )

    @staticmethod
    def get_history(db: Session, student_id: str) -> list[StudentPlan]:
        """Return a student's full plan assignment history, most recent first."""
        return (
            db.query(StudentPlan)
            .filter(StudentPlan.student_id == student_id)
            .order_by(StudentPlan.started_at.desc())
            .all()
        )

    @staticmethod
    def get_current_price(db: Session, student_id: str) -> Decimal | None:
        """Return the student's current locked price, independent of mensalidade existence."""
        active = StudentPlanService.get_active(db, student_id)
        return active.plan_version.price if active else None

    @staticmethod
    def assign(db: Session, student: Student) -> StudentPlan:
        """Assign (or reassign) a student to the plan tier matching their declared weekly frequency (D1).

        Fails loudly if no active plan tier matches ``student.classes_per_week``,
        rather than silently defaulting to a price (the "plan-tier lookup gap"
        edge case) -- the catalog must be kept complete for every frequency in use.
        """
        tier = (
            db.query(PlanTier)
            .filter(PlanTier.weekly_frequency == student.classes_per_week, PlanTier.is_active.is_(True))
            .first()
        )
        if not tier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No active plan tier is defined for {student.classes_per_week} classes/week",
            )
        version = PlanService.get_active_version(db, tier.id)
        if not version:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Plan tier '{tier.name}' has no active price",
            )

        previous = StudentPlanService.get_active(db, student.id)
        now = datetime.now(UTC)
        if previous:
            previous.status = "superseded"
            previous.ended_at = now

        assignment = StudentPlan(
            student_id=student.id,
            plan_version_id=version.id,
            status="active",
            started_at=now,
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        return assignment
