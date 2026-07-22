"""Computed-on-read balance, mensalidade status, and the overdue dashboard.

No ledger/allocation table is stored (D4, D7): a student's balance and each
mensalidade's status are derived by walking active mensalidades (ascending
due date) and active payments (ascending payment date), applying payments
oldest-mensalidade-first (FIFO).
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Mensalidade, Payment, Student
from app.services.medical_exam_service import MedicalExamService


class BalanceService:
    """FIFO balance and status computation across a student's mensalidades and payments."""

    @staticmethod
    def _active_mensalidades(db: Session, student_id: str) -> list[Mensalidade]:
        return (
            db.query(Mensalidade)
            .filter(Mensalidade.student_id == student_id)
            .order_by(Mensalidade.due_date.asc())
            .all()
        )

    @staticmethod
    def _active_payments(db: Session, student_id: str) -> list[Payment]:
        return (
            db.query(Payment)
            .filter(Payment.student_id == student_id, Payment.status == "active")
            .order_by(Payment.payment_date.asc())
            .all()
        )

    @staticmethod
    def allocate(mensalidades: list[Mensalidade], payments: list[Payment]) -> dict[str, Decimal]:
        """Greedily apply payments oldest-mensalidade-first; return paid amount per mensalidade id."""
        remaining = sum((p.amount for p in payments), Decimal("0"))
        paid_by_id: dict[str, Decimal] = {}
        for mensalidade in mensalidades:
            allocated = min(remaining, mensalidade.amount)
            paid_by_id[mensalidade.id] = allocated
            remaining -= allocated
        return paid_by_id

    @staticmethod
    def compute_status(amount: Decimal, paid_amount: Decimal, due_date: datetime) -> str:
        """Paid / overdue (no grace, D8) / partial / open, in that priority order."""
        if paid_amount >= amount:
            return "paid"
        if due_date.tzinfo is None:
            due_date = due_date.replace(tzinfo=UTC)
        if datetime.now(UTC) > due_date:
            return "overdue"
        if paid_amount > 0:
            return "partial"
        return "open"

    @staticmethod
    def get_student_charges_with_status(db: Session, student_id: str) -> list[dict]:
        """Return a student's mensalidades enriched with computed paid amount and status."""
        mensalidades = BalanceService._active_mensalidades(db, student_id)
        payments = BalanceService._active_payments(db, student_id)
        paid_by_id = BalanceService.allocate(mensalidades, payments)
        return [
            {
                "id": m.id,
                "student_id": m.student_id,
                "plan_version_id": m.plan_version_id,
                "reference_month": m.reference_month,
                "due_date": m.due_date,
                "amount": m.amount,
                "paid_amount": paid_by_id[m.id],
                "status": BalanceService.compute_status(m.amount, paid_by_id[m.id], m.due_date),
                "created_at": m.created_at,
            }
            for m in mensalidades
        ]

    @staticmethod
    def get_balance(db: Session, student_id: str) -> dict:
        """Return a student's net owed (positive) or credit (negative) balance.

        Uses the raw payment total rather than the per-mensalidade allocation
        (``allocate`` caps each mensalidade's paid amount at its own amount, so
        any payment surplus -- the credit -- would otherwise be dropped here).
        """
        charges = BalanceService.get_student_charges_with_status(db, student_id)
        total_amount = sum((c["amount"] for c in charges), Decimal("0"))
        total_paid = sum((p.amount for p in BalanceService._active_payments(db, student_id)), Decimal("0"))
        return {
            "student_id": student_id,
            "balance": total_amount - total_paid,
            "open_count": sum(1 for c in charges if c["status"] in ("open", "partial")),
            "overdue_count": sum(1 for c in charges if c["status"] == "overdue"),
        }

    @staticmethod
    def get_overdue_dashboard(db: Session) -> list[dict]:
        """List active students with at least one overdue mensalidade (FIN-05).

        Each row includes the student's medical-exam status as a display-only
        flag (D3): it never gates anything in this phase.
        """
        results = []
        students = db.query(Student).filter(Student.is_active.is_(True)).all()
        for student in students:
            charges = BalanceService.get_student_charges_with_status(db, student.id)
            overdue = [c for c in charges if c["status"] == "overdue"]
            if not overdue:
                continue
            unpaid_total = sum((c["amount"] - c["paid_amount"] for c in charges if c["status"] != "paid"), Decimal("0"))
            results.append(
                {
                    "student_id": student.id,
                    "student_name": student.full_name,
                    "registration_number": student.registration_number,
                    "amount_owed": unpaid_total,
                    "open_count": sum(1 for c in charges if c["status"] in ("open", "partial")),
                    "overdue_count": len(overdue),
                    "oldest_overdue_due_date": min(c["due_date"] for c in overdue),
                    "medical_exam_status": MedicalExamService.get_status(db, student.id)["status"],
                }
            )
        return results
