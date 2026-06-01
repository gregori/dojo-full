from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class OrganizationBase(BaseModel):
    name: str
    description: Optional[str] = None


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class OrganizationResponse(OrganizationBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


class DojoBase(BaseModel):
    organization_id: str
    code: int
    name: str
    address: Optional[str] = None


class DojoCreate(DojoBase):
    pass


class DojoUpdate(BaseModel):
    code: Optional[int] = None
    name: Optional[str] = None
    address: Optional[str] = None


class DojoResponse(DojoBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


class DojoWithOrganization(DojoResponse):
    organization: Optional[OrganizationResponse] = None
