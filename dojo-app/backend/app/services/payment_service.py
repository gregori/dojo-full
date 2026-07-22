"""Business rules for recording and soft-voiding student payments."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Payment
from app.services.student_service import StudentService


class PaymentService:
    """Record payments against a student; voiding is a soft, audit-trailed correction."""

    @staticmethod
    def record_payment(
        db: Session, student_id: str, amount: Decimal, payment_date: datetime, method: str | None, recorded_by: str
    ) -> Payment:
        student = StudentService.get_student(db, student_id)
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        payment = Payment(
            student_id=student_id,
            amount=amount,
            payment_date=payment_date,
            method=method,
            recorded_by=recorded_by,
            status="active",
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def void_payment(db: Session, payment_id: str, voided_by: str) -> Payment:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        if payment.status == "voided":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment is already voided")

        payment.status = "voided"
        payment.voided_at = datetime.now(UTC)
        payment.voided_by = voided_by
        db.commit()
        db.refresh(payment)
        return payment
