"""Unit tests for locking a student to a plan tier's active version, and the lookup-gap edge case."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models import StudentPlan
from app.services import MensalidadeService, PlanService, StudentPlanService
from tests.unit.conftest import make_student, make_user


class TestAssign:
    def test_assigns_matching_tier_by_classes_per_week(self, db_session):
        user = make_user(db_session)
        PlanService.create_tier(db_session, 2, "2x por semana", Decimal("150.00"), created_by=user.id)
        student = make_student(db_session, classes_per_week=2)

        assignment = StudentPlanService.assign(db_session, student)

        assert assignment.status == "active"
        assert assignment.plan_version.price == Decimal("150.00")

    def test_reassignment_supersedes_prior_active_plan(self, db_session):
        user = make_user(db_session)
        PlanService.create_tier(db_session, 2, "2x por semana", Decimal("150.00"), created_by=user.id)
        student = make_student(db_session, classes_per_week=2)
        first = StudentPlanService.assign(db_session, student)

        second = StudentPlanService.assign(db_session, student)

        db_session.refresh(first)
        assert first.status == "superseded"
        assert first.ended_at is not None
        active_plans = (
            db_session.query(StudentPlan)
            .filter(StudentPlan.student_id == student.id, StudentPlan.status == "active")
            .all()
        )
        assert len(active_plans) == 1
        assert active_plans[0].id == second.id

    def test_no_matching_tier_fails_loudly(self, db_session):
        """The plan-tier lookup gap: classes_per_week with no matching PlanTier must raise, not default silently."""
        student = make_student(db_session, classes_per_week=6)

        with pytest.raises(HTTPException) as exc_info:
            StudentPlanService.assign(db_session, student)

        assert exc_info.value.status_code == 400
        assert "6" in exc_info.value.detail

    def test_inactive_tier_is_not_matched(self, db_session):
        from app.models import PlanTier

        user = make_user(db_session)
        PlanService.create_tier(db_session, 4, "4x por semana", Decimal("200.00"), created_by=user.id)
        db_session.query(PlanTier).filter(PlanTier.weekly_frequency == 4).update({"is_active": False})
        db_session.commit()
        student = make_student(db_session, classes_per_week=4)

        with pytest.raises(HTTPException) as exc_info:
            StudentPlanService.assign(db_session, student)

        assert exc_info.value.status_code == 400

    def test_get_current_price_is_independent_of_mensalidade_existence(self, db_session):
        user = make_user(db_session)
        PlanService.create_tier(db_session, 5, "5x por semana", Decimal("250.00"), created_by=user.id)
        student = make_student(db_session, classes_per_week=5)
        StudentPlanService.assign(db_session, student)

        assert StudentPlanService.get_current_price(db_session, student.id) == Decimal("250.00")

    def test_get_current_price_returns_none_when_unassigned(self, db_session):
        student = make_student(db_session, classes_per_week=2)

        assert StudentPlanService.get_current_price(db_session, student.id) is None


class TestPriceLocking:
    """AC2: editing a tier's price never reprices an already-assigned student (D11)."""

    def test_set_price_after_assignment_does_not_reprice_the_student(self, db_session):
        user = make_user(db_session)
        tier = PlanService.create_tier(db_session, 2, "2x por semana", Decimal("150.00"), created_by=user.id)
        student = make_student(db_session, classes_per_week=2)
        assignment = StudentPlanService.assign(db_session, student)
        original_plan_version_id = assignment.plan_version_id

        PlanService.set_price(db_session, tier.id, Decimal("999.00"), created_by=user.id)

        db_session.refresh(assignment)
        assert assignment.plan_version_id == original_plan_version_id
        assert assignment.plan_version.price == Decimal("150.00")
        assert StudentPlanService.get_current_price(db_session, student.id) == Decimal("150.00")

    def test_mensalidade_generated_after_price_change_still_uses_locked_version(self, db_session):
        user = make_user(db_session)
        tier = PlanService.create_tier(db_session, 3, "3x por semana", Decimal("200.00"), created_by=user.id)
        student = make_student(db_session, classes_per_week=3)
        assignment = StudentPlanService.assign(db_session, student)
        # Backdate so the mensalidade generated below isn't the (prorated) enrollment-month charge.
        assignment.started_at = datetime.now(UTC) - timedelta(days=60)
        db_session.commit()

        PlanService.set_price(db_session, tier.id, Decimal("999.00"), created_by=user.id)

        result = MensalidadeService.generate_monthly_charges(db_session, datetime.now(UTC))
        assert result["created_count"] == 1
        charges = MensalidadeService.get_student_charges(db_session, student.id)
        assert charges[0]["amount"] == Decimal("200.00")
        assert charges[0]["plan_version_id"] == assignment.plan_version_id
