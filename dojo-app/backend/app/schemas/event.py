from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator


class EventTypeBase(BaseModel):
    name: str
    color: str | None = None
    counts_for_belt: bool = True


class EventTypeCreate(EventTypeBase):
    pass


class EventTypeUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    counts_for_belt: bool | None = None


class EventTypeResponse(EventTypeBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


class EventBase(BaseModel):
    title: str
    event_type_id: str
    description: str | None = None
    start_datetime: datetime
    end_datetime: datetime | None = None
    location: str | None = None
    organization_id: str | None = None
    minimum_belt_id: str | None = None


class EventCreate(EventBase):
    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_datetime and self.start_datetime and self.end_datetime < self.start_datetime:
            raise ValueError("end_datetime must be after start_datetime")
        return self


class EventUpdate(BaseModel):
    title: str | None = None
    event_type_id: str | None = None
    description: str | None = None
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    location: str | None = None
    status: str | None = None
    minimum_belt_id: str | None = None


class EventResponse(EventBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_by: str
    check_in_token: str
    status: str
    created_at: datetime
    updated_at: datetime


class EventWithDetails(EventResponse):
    event_type: EventTypeResponse | None = None
    attendance_count: int = 0
