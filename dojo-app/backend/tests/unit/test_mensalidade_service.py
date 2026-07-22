"""Unit tests for monthly charge generation: proration and idempotent, plan-assignment-aware generation."""

from datetime import UTC, datetime
from decimal import Decimal

from app.models import Mensalidade, StudentPlan
from app.services import MensalidadeService
from tests.unit.conftest import make_plan_tier, make_plan_version, make_student, make_student_plan


class TestProration:
    def test_mid_month_assignment_is_prorated(self, db_session):
        tier = make_plan_tier(db_session, weekly_frequency=2)
        version = make_plan_version(db_session, plan_tier_id=tier.id, price=Decimal("300.00"))
        student = make_student(db_session, classes_per_week=2)
        make_student_plan(
            db_session,
            student_id=student.id,
            plan_version_id=version.id,
            started_at=datetime(2026, 1, 16, tzinfo=UTC),
        )

        result = MensalidadeService.generate_monthly_charges(db_session, datetime(2026, 1, 1, tzinfo=UTC))

        assert result["created_count"] == 1
        mensalidade = db_session.query(Mensalidade).filter(Mensalidade.student_id == student.id).one()
        # 31-day January, effective day 16: 16 remaining days / 31 total * 300.00 = 154.84 (rounded)
        assert mensalidade.amount == Decimal("154.84")

    def test_full_month_after_enrollment_month_is_not_prorated(self, db_session):
        tier = make_plan_tier(db_session, weekly_frequency=2)
        version = make_plan_version(db_session, plan_tier_id=tier.id, price=Decimal("300.00"))
        student = make_student(db_session, classes_per_week=2)
        make_student_plan(
            db_session,
            student_id=student.id,
            plan_version_id=version.id,
            started_at=datetime(2025, 12, 10, tzinfo=UTC),
        )

        result = MensalidadeService.generate_monthly_charges(db_session, datetime(2026, 1, 1, tzinfo=UTC))

        assert result["created_count"] == 1
        mensalidade = db_session.query(Mensalidade).filter(Mensalidade.student_id == student.id).one()
        assert mensalidade.amount == Decimal("300.00")


class TestGenerateMonthlyCharges:
    def test_running_twice_does_not_duplicate(self, db_session):
        tier = make_plan_tier(db_session, weekly_frequency=2)
        version = make_plan_version(db_session, plan_tier_id=tier.id, price=Decimal("100.00"))
        student = make_student(db_session, classes_per_week=2)
        make_student_plan(
            db_session,
            student_id=student.id,
            plan_version_id=version.id,
            started_at=datetime(2025, 6, 1, tzinfo=UTC),
        )
        reference_month = datetime(2026, 2, 1, tzinfo=UTC)

        first_run = MensalidadeService.generate_monthly_charges(db_session, reference_month)
        second_run = MensalidadeService.generate_monthly_charges(db_session, reference_month)

        assert first_run["created_count"] == 1
        assert second_run["created_count"] == 0
        assert second_run["skipped_count"] == 1
        assert db_session.query(Mensalidade).filter(Mensalidade.student_id == student.id).count() == 1

    def test_inactive_student_is_skipped(self, db_session):
        tier = make_plan_tier(db_session, weekly_frequency=2)
        version = make_plan_version(db_session, plan_tier_id=tier.id, price=Decimal("100.00"))
        student = make_student(db_session, classes_per_week=2, is_active=False)
        make_student_plan(db_session, student_id=student.id, plan_version_id=version.id)

        result = MensalidadeService.generate_monthly_charges(db_session, datetime(2026, 3, 1, tzinfo=UTC))

        assert result["created_count"] == 0
        assert db_session.query(Mensalidade).filter(Mensalidade.student_id == student.id).count() == 0

    def test_active_student_without_plan_assignment_is_skipped_and_not_auto_assigned(self, db_session):
        """Plan assignment is its own explicit action (enrollment/plan-change); generation must not auto-assign."""
        student = make_student(db_session, classes_per_week=2)

        result = MensalidadeService.generate_monthly_charges(db_session, datetime(2026, 4, 1, tzinfo=UTC))

        assert result["created_count"] == 0
        assert result["skipped_count"] == 1
        assert db_session.query(Mensalidade).filter(Mensalidade.student_id == student.id).count() == 0
        assert db_session.query(StudentPlan).filter(StudentPlan.student_id == student.id).count() == 0
