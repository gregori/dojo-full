from pydantic import BaseModel, ConfigDict


class BeltBase(BaseModel):
    name: str
    category: str
    sort_order: int
    organization_id: str | None = None


class BeltCreate(BeltBase):
    pass


class BeltUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    sort_order: int | None = None


class BeltResponse(BeltBase):
    model_config = ConfigDict(from_attributes=True)
    id: str


class BeltRequirementBase(BaseModel):
    belt_id: str
    event_type_id: str
    required_count: int
    description: str | None = None


class BeltRequirementCreate(BaseModel):
    event_type_id: str
    required_count: int
    description: str | None = None
    belt_id: str | None = None


class BeltRequirementUpdate(BaseModel):
    required_count: int | None = None
    description: str | None = None
    event_type_id: str | None = None


class BeltRequirementResponse(BeltRequirementBase):
    model_config = ConfigDict(from_attributes=True)
    id: str


class BeltWithRequirements(BeltResponse):
    requirements: list[BeltRequirementResponse] = []
