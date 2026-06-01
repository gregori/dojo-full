from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, model_validator


class EventTypeBase(BaseModel):
    name: str
    color: Optional[str] = None
    counts_for_belt: bool = True


class EventTypeCreate(EventTypeBase):
    pass


class EventTypeUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    counts_for_belt: Optional[bool] = None


class EventTypeResponse(EventTypeBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


class EventBase(BaseModel):
    title: str
    event_type_id: str
    description: Optional[str] = None
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    location: Optional[str] = None
    organization_id: Optional[str] = None


class EventCreate(EventBase):
    @model_validator(mode='after')
    def validate_dates(self):
        if self.end_datetime and self.start_datetime and self.end_datetime < self.start_datetime:
            raise ValueError('end_datetime must be after start_datetime')
        return self


class EventUpdate(BaseModel):
    title: Optional[str] = None
    event_type_id: Optional[str] = None
    description: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    location: Optional[str] = None
    status: Optional[str] = None


class EventResponse(EventBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_by: str
    check_in_token: str
    status: str
    created_at: datetime
    updated_at: datetime


class EventWithDetails(EventResponse):
    event_type: Optional[EventTypeResponse] = None
    attendance_count: int = 0
