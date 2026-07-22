"""Schemas for recording and voiding student payments."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PaymentCreate(BaseModel):
    """Fields required to record a payment against a student."""

    student_id: str
    amount: Decimal = Field(gt=0)
    payment_date: datetime
    method: str | None = None


class PaymentResponse(BaseModel):
    """A recorded payment, including its soft-void audit fields, if voided."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    amount: Decimal
    payment_date: datetime
    method: str | None = None
    recorded_by: str
    status: str
    voided_at: datetime | None = None
    voided_by: str | None = None
    created_at: datetime
