from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrganizationBase(BaseModel):
    name: str
    description: str | None = None


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class OrganizationResponse(OrganizationBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


class DojoBase(BaseModel):
    organization_id: str
    code: int
    name: str
    address: str | None = None


class DojoCreate(DojoBase):
    pass


class DojoUpdate(BaseModel):
    code: int | None = None
    name: str | None = None
    address: str | None = None


class DojoResponse(DojoBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


class DojoWithOrganization(DojoResponse):
    organization: OrganizationResponse | None = None
