"""Schemas for monthly charges (mensalidades) and computed status."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class GenerateChargesRequest(BaseModel):
    """Optional reference month for monthly charge generation; defaults to the current month."""

    reference_month: datetime | None = None


class GenerateChargesResponse(BaseModel):
    """Summary of a generation run."""

    reference_month: datetime
    created_count: int
    skipped_count: int


class MensalidadeResponse(BaseModel):
    """A single mensalidade with its computed (not stored) status."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    plan_version_id: str
    reference_month: datetime
    due_date: datetime
    amount: Decimal
    paid_amount: Decimal
    status: str
    created_at: datetime


class BalanceResponse(BaseModel):
    """A student's current owed (positive) or credit (negative) balance."""

    student_id: str
    balance: Decimal
    open_count: int
    overdue_count: int


class OverdueDashboardItem(BaseModel):
    """A row in the FIN-05 inadimplentes dashboard, with the medical-exam flag (D3: display-only)."""

    student_id: str
    student_name: str
    registration_number: str
    amount_owed: Decimal
    open_count: int
    overdue_count: int
    oldest_overdue_due_date: datetime | None = None
    medical_exam_status: str
