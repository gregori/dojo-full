from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class BeltBase(BaseModel):
    name: str
    category: str
    sort_order: int
    organization_id: Optional[str] = None


class BeltCreate(BeltBase):
    pass


class BeltUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    sort_order: Optional[int] = None


class BeltResponse(BeltBase):
    model_config = ConfigDict(from_attributes=True)
    id: str


class BeltRequirementBase(BaseModel):
    belt_id: str
    event_type_id: str
    required_count: int
    description: Optional[str] = None


class BeltRequirementCreate(BaseModel):
    event_type_id: str
    required_count: int
    description: Optional[str] = None
    belt_id: Optional[str] = None


class BeltRequirementUpdate(BaseModel):
    required_count: Optional[int] = None
    description: Optional[str] = None
    event_type_id: Optional[str] = None


class BeltRequirementResponse(BeltRequirementBase):
    model_config = ConfigDict(from_attributes=True)
    id: str


class BeltWithRequirements(BeltResponse):
    requirements: List[BeltRequirementResponse] = []
