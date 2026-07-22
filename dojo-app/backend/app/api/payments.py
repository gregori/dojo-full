"""Instructor/admin-only endpoints for recording and voiding student payments."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_instructor_or_admin
from app.schemas import PaymentCreate, PaymentResponse
from app.services import PaymentService

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def record_payment(
    data: PaymentCreate, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """Record a payment against a student; overpayment becomes credit applied via FIFO (D7)."""
    return PaymentService.record_payment(
        db, data.student_id, data.amount, data.payment_date, data.method, recorded_by=current_user.id
    )


@router.post("/{payment_id}/void", response_model=PaymentResponse)
def void_payment(payment_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)):
    """Soft-void a mis-entered payment, keeping an audit trail."""
    return PaymentService.void_payment(db, payment_id, voided_by=current_user.id)
