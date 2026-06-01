from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class BeltPromotionBase(BaseModel):
    student_id: str
    belt_id: str
    promoted_at: Optional[datetime] = None
    notes: Optional[str] = None


class BeltPromotionCreate(BaseModel):
    student_id: str
    belt_id: str
    promoted_at: Optional[datetime] = None
    exam_id: Optional[str] = None
    notes: Optional[str] = None


class BeltPromotionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    student_id: str
    belt_id: str
    promoted_at: datetime
    promoted_by: Optional[str] = None
    exam_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
