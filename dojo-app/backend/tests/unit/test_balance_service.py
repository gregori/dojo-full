"""Unit tests for computed-on-read balance, FIFO payment allocation, and status priority."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.services import BalanceService
from tests.unit.conftest import make_mensalidade, make_payment, make_student


class TestComputeStatus:
    def test_fully_paid_is_paid(self):
        due_date = datetime.now(UTC) - timedelta(days=5)
        assert BalanceService.compute_status(Decimal("100.00"), Decimal("100.00"), due_date) == "paid"

    def test_paid_takes_priority_over_overdue(self):
        """Even if the due date has passed, a fully paid mensalidade is 'paid', not 'overdue'."""
        due_date = datetime.now(UTC) - timedelta(days=30)
        assert BalanceService.compute_status(Decimal("100.00"), Decimal("100.00"), due_date) == "paid"

    def test_unpaid_past_due_date_is_overdue(self):
        due_date = datetime.now(UTC) - timedelta(days=1)
        assert BalanceService.compute_status(Decimal("100.00"), Decimal("0.00"), due_date) == "overdue"

    def test_partial_payment_before_due_date_is_partial(self):
        due_date = datetime.now(UTC) + timedelta(days=5)
        assert BalanceService.compute_status(Decimal("100.00"), Decimal("40.00"), due_date) == "partial"

    def test_no_payment_before_due_date_is_open(self):
        due_date = datetime.now(UTC) + timedelta(days=5)
        assert BalanceService.compute_status(Decimal("100.00"), Decimal("0.00"), due_date) == "open"


class TestFIFOAllocation:
    def test_payment_covers_oldest_mensalidade_first(self, db_session):
        student = make_student(db_session)
        # Future due dates so status reflects the payment split, not the overdue rule.
        older = make_mensalidade(
            db_session,
            student_id=student.id,
            reference_month=datetime.now(UTC) + timedelta(days=30),
            due_date=datetime.now(UTC) + timedelta(days=30),
            amount=Decimal("100.00"),
        )
        newer = make_mensalidade(
            db_session,
            student_id=student.id,
            reference_month=datetime.now(UTC) + timedelta(days=60),
            due_date=datetime.now(UTC) + timedelta(days=60),
            amount=Decimal("100.00"),
        )
        make_payment(db_session, student_id=student.id, amount=Decimal("150.00"))

        charges = {c["id"]: c for c in BalanceService.get_student_charges_with_status(db_session, student.id)}

        assert charges[older.id]["paid_amount"] == Decimal("100.00")
        assert charges[older.id]["status"] == "paid"
        assert charges[newer.id]["paid_amount"] == Decimal("50.00")
        assert charges[newer.id]["status"] == "partial"

    def test_overpayment_becomes_credit_applied_to_next_mensalidade(self, db_session):
        student = make_student(db_session)
        first = make_mensalidade(
            db_session,
            student_id=student.id,
            reference_month=datetime.now(UTC) + timedelta(days=30),
            due_date=datetime.now(UTC) + timedelta(days=30),
            amount=Decimal("100.00"),
        )
        make_payment(db_session, student_id=student.id, amount=Decimal("150.00"))

        balance_before = BalanceService.get_balance(db_session, student.id)
        assert balance_before["balance"] == Decimal("-50.00")

        second = make_mensalidade(
            db_session,
            student_id=student.id,
            reference_month=datetime.now(UTC) + timedelta(days=60),
            due_date=datetime.now(UTC) + timedelta(days=60),
            amount=Decimal("100.00"),
        )

        charges = {c["id"]: c for c in BalanceService.get_student_charges_with_status(db_session, student.id)}
        assert charges[first.id]["paid_amount"] == Decimal("100.00")
        assert charges[second.id]["paid_amount"] == Decimal("50.00")
        assert charges[second.id]["status"] == "partial"

    def test_voided_payment_is_excluded_from_allocation(self, db_session):
        student = make_student(db_session)
        # A future due date isolates "unpaid because voided" from the separate overdue rule.
        mensalidade = make_mensalidade(
            db_session,
            student_id=student.id,
            amount=Decimal("100.00"),
            due_date=datetime.now(UTC) + timedelta(days=30),
        )
        make_payment(db_session, student_id=student.id, amount=Decimal("100.00"), status="voided")

        charges = BalanceService.get_student_charges_with_status(db_session, student.id)

        assert charges[0]["id"] == mensalidade.id
        assert charges[0]["paid_amount"] == Decimal("0.00")
        assert charges[0]["status"] == "open"


class TestOverdueDashboard:
    def test_includes_only_students_with_overdue_mensalidades(self, db_session):
        overdue_student = make_student(db_session)
        make_mensalidade(
            db_session,
            student_id=overdue_student.id,
            due_date=datetime.now(UTC) - timedelta(days=10),
            amount=Decimal("100.00"),
        )

        paid_student = make_student(db_session)
        paid_mensalidade = make_mensalidade(
            db_session,
            student_id=paid_student.id,
            due_date=datetime.now(UTC) - timedelta(days=10),
            amount=Decimal("100.00"),
        )
        make_payment(db_session, student_id=paid_student.id, amount=paid_mensalidade.amount)

        open_student = make_student(db_session)
        make_mensalidade(
            db_session,
            student_id=open_student.id,
            due_date=datetime.now(UTC) + timedelta(days=10),
            amount=Decimal("100.00"),
        )

        dashboard = BalanceService.get_overdue_dashboard(db_session)
        student_ids = {row["student_id"] for row in dashboard}

        assert overdue_student.id in student_ids
        assert paid_student.id not in student_ids
        assert open_student.id not in student_ids
        overdue_row = next(row for row in dashboard if row["student_id"] == overdue_student.id)
        assert overdue_row["amount_owed"] == Decimal("100.00")
        assert overdue_row["overdue_count"] == 1
        assert "medical_exam_status" in overdue_row
