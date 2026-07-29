"""Schemas for the versioned legal contract template."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ContractTemplateVersionCreate(BaseModel):
    """Fields required to author a new contract template version."""

    body: str
    effective_from: datetime


class ContractTemplateVersionResponse(BaseModel):
    """A single contract template version."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    body: str
    status: str
    effective_from: datetime
    created_by: str
    created_at: datetime
