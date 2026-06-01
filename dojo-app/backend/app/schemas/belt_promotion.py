from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BeltPromotionBase(BaseModel):
    student_id: str
    belt_id: str
    promoted_at: datetime | None = None
    notes: str | None = None


class BeltPromotionCreate(BaseModel):
    student_id: str
    belt_id: str
    promoted_at: datetime | None = None
    exam_id: str | None = None
    notes: str | None = None


class BeltPromotionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    student_id: str
    belt_id: str
    promoted_at: datetime
    promoted_by: str | None = None
    exam_id: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
