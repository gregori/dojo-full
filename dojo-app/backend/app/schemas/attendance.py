from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttendanceBase(BaseModel):
    event_id: str
    student_id: str
    check_in_method: str  # 'tablet', 'qrcode', 'manual'


class AttendanceCreate(AttendanceBase):
    registered_by: str | None = None


class AttendanceResponse(AttendanceBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    student_name: str | None = None
    check_in_at: datetime
    registered_by: str | None = None
    created_at: datetime


class CheckInRequest(BaseModel):
    registration_number: str
    pin: str
    check_in_method: str = "tablet"


class CheckInQRRequest(BaseModel):
    registration_number: str
    pin: str
    check_in_token: str


class CheckInResponse(BaseModel):
    status: str
    message: str
    student_name: str
    event_title: str
    progress: dict | None = None
