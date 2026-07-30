from datetime import date, datetime, time
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EventSeriesBase(BaseModel):
    title: str
    event_type_id: str
    description: str | None = None
    dojo_id: str | None = None
    minimum_belt_id: str | None = None
    organization_id: str | None = None
    days_of_week: list[int]
    start_time: time
    duration_minutes: Annotated[int, Field(gt=0)] | None = None
    series_start_date: date | None = None
    series_end_date: date | None = None
    is_active: bool = True

    @field_validator("days_of_week")
    @classmethod
    def validate_days_of_week(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("days_of_week must have at least one day")
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("days_of_week values must be 0 (Monday) through 6 (Sunday)")
        return sorted(set(v))


class EventSeriesCreate(EventSeriesBase):
    @model_validator(mode="after")
    def validate_dates(self):
        effective_start_date = self.series_start_date or date.today()
        if self.series_end_date and self.series_end_date < effective_start_date:
            raise ValueError("series_end_date must be after series_start_date")
        return self


class EventSeriesUpdate(BaseModel):
    title: str | None = None
    event_type_id: str | None = None
    description: str | None = None
    dojo_id: str | None = None
    minimum_belt_id: str | None = None
    days_of_week: list[int] | None = None
    start_time: time | None = None
    duration_minutes: Annotated[int, Field(gt=0)] | None = None
    series_end_date: date | None = None
    is_active: bool | None = None

    @field_validator("days_of_week")
    @classmethod
    def validate_days_of_week(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return v
        if not v:
            raise ValueError("days_of_week must have at least one day")
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("days_of_week values must be 0 (Monday) through 6 (Sunday)")
        return sorted(set(v))


class EventSeriesResponse(EventSeriesBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    check_in_token: str
    created_by: str
    series_start_date: date
    created_at: datetime
    updated_at: datetime

    @field_validator("days_of_week", mode="before")
    @classmethod
    def _split_days(cls, v):
        if isinstance(v, str):
            return [int(x) for x in v.split(",") if x != ""]
        return v


class GenerateOccurrencesResponse(BaseModel):
    series_id: str
    window_start: date
    window_end: date
    created_count: int
    skipped_count: int
