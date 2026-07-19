"""Schemas for the pre-check-in flow."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PreCheckInRequest(BaseModel):
    """Public credentials used to confirm or cancel a pre-check-in."""

    event_id: str
    registration_number: str
    pin: str


class PreCheckInPublicResponse(BaseModel):
    """Privacy-preserving response for public pre-check-in actions."""

    status: str
    message: str


class PreCheckInResponse(BaseModel):
    """Instructor-facing pre-check-in record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    student_id: str
    status: str
    confirmed_at: datetime
    cancelled_at: datetime | None = None
    converted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PreCheckInRosterItem(PreCheckInResponse):
    """A confirmation record with the student's name for authorized rosters."""

    student_name: str
    registration_number: str


class PreCheckInCount(BaseModel):
    """Confirmed pre-check-in count for an event."""

    event_id: str
    confirmed_count: int


class PublicPreCheckInEvent(BaseModel):
    """Non-sensitive event fields available before public credential validation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    start_datetime: datetime
    end_datetime: datetime | None = None
    location: str | None = None
