"""Instructor/admin-only endpoints for monthly charge generation, history, balance, and the overdue dashboard."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_instructor_or_admin
from app.schemas import (
    BalanceResponse,
    GenerateChargesRequest,
    GenerateChargesResponse,
    MensalidadeResponse,
    OverdueDashboardItem,
)
from app.services import BalanceService, MensalidadeService

router = APIRouter(prefix="/api/v1", tags=["mensalidades"])


@router.post("/mensalidades/generate", response_model=GenerateChargesResponse)
def generate_monthly_charges(
    data: GenerateChargesRequest | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_instructor_or_admin),
):
    """Idempotently generate the reference month's charges for all active students."""
    return MensalidadeService.generate_monthly_charges(db, data.reference_month if data else None)


@router.get("/students/{student_id}/mensalidades", response_model=list[MensalidadeResponse])
def get_student_mensalidades(
    student_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """List a student's charge history with computed status per row (D4)."""
    return MensalidadeService.get_student_charges(db, student_id)


@router.get("/students/{student_id}/balance", response_model=BalanceResponse)
def get_student_balance(
    student_id: str, db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)
):
    """Return a student's current owed/credit balance."""
    return BalanceService.get_balance(db, student_id)


@router.get("/finance/overdue", response_model=list[OverdueDashboardItem])
def get_overdue_dashboard(db: Session = Depends(get_db), current_user=Depends(get_current_instructor_or_admin)):
    """List active students with overdue mensalidades (FIN-05), including the medical-exam flag (D3)."""
    return BalanceService.get_overdue_dashboard(db)
