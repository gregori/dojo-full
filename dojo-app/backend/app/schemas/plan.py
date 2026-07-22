"""Schemas for the plan tier catalog and student plan assignments."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PlanTierCreate(BaseModel):
    """Fields required to define a new weekly-frequency plan tier."""

    weekly_frequency: int = Field(ge=1)
    name: str
    price: Decimal = Field(gt=0)


class PlanVersionResponse(BaseModel):
    """A priced, versioned snapshot of a plan tier."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    plan_tier_id: str
    price: Decimal
    status: str
    effective_from: datetime
    created_at: datetime


class PlanTierResponse(BaseModel):
    """A plan tier with its current active price."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    weekly_frequency: int
    name: str
    is_active: bool
    current_price: Decimal | None = None


class PlanPriceUpdate(BaseModel):
    """New price for a plan tier; creates and activates a new version."""

    price: Decimal = Field(gt=0)


class StudentPlanResponse(BaseModel):
    """A student's plan assignment, with the locked plan version."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    plan_version_id: str
    status: str
    started_at: datetime
    ended_at: datetime | None = None
    plan_version: PlanVersionResponse
