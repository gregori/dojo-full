from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExamBase(BaseModel):
    event_id: str
    belt_id: str
    exam_date: datetime
    notes: str | None = None


class ExamCreate(ExamBase):
    pass


class ExamUpdate(BaseModel):
    exam_date: datetime | None = None
    status: str | None = None
    notes: str | None = None


class ExamResponse(ExamBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class ExamParticipantBase(BaseModel):
    exam_id: str
    student_id: str
    role: str  # 'candidate', 'uke'


class ExamParticipantCreate(BaseModel):
    exam_id: str | None = None
    student_id: str
    role: str
    override_eligibility: bool = False
    override_reason: str | None = None


class ExamParticipantUpdate(BaseModel):
    status: str | None = None  # 'pending', 'approved', 'rejected'
    is_eligible: bool | None = None
    override_eligibility: bool | None = None
    override_reason: str | None = None
    notes: str | None = None


class ExamParticipantResponse(ExamParticipantBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    is_eligible: bool
    override_eligibility: bool
    override_reason: str | None = None
    overridden_by: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ExamBoardMemberBase(BaseModel):
    exam_id: str
    user_id: str
    role_in_board: str = "member"  # 'president', 'member'


class ExamBoardMemberCreate(BaseModel):
    user_id: str
    role_in_board: str = "member"  # 'president', 'member'
    exam_id: str | None = None  # Set from path parameter


class ExamBoardMemberResponse(ExamBoardMemberBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


class ExamWithDetails(ExamResponse):
    participants: list[ExamParticipantResponse] = []
    board_members: list[ExamBoardMemberResponse] = []
    event_title: str | None = None
    belt_name: str | None = None
