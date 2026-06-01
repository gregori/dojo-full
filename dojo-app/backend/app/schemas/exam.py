from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class ExamBase(BaseModel):
    event_id: str
    belt_id: str
    exam_date: datetime
    notes: Optional[str] = None


class ExamCreate(ExamBase):
    pass


class ExamUpdate(BaseModel):
    exam_date: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None


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
    exam_id: Optional[str] = None
    student_id: str
    role: str
    override_eligibility: bool = False
    override_reason: Optional[str] = None


class ExamParticipantUpdate(BaseModel):
    status: Optional[str] = None  # 'pending', 'approved', 'rejected'
    is_eligible: Optional[bool] = None
    override_eligibility: Optional[bool] = None
    override_reason: Optional[str] = None
    notes: Optional[str] = None


class ExamParticipantResponse(ExamParticipantBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    is_eligible: bool
    override_eligibility: bool
    override_reason: Optional[str] = None
    overridden_by: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ExamBoardMemberBase(BaseModel):
    exam_id: str
    user_id: str
    role_in_board: str = "member"  # 'president', 'member'


class ExamBoardMemberCreate(BaseModel):
    user_id: str
    role_in_board: str = "member"  # 'president', 'member'
    exam_id: Optional[str] = None  # Set from path parameter


class ExamBoardMemberResponse(ExamBoardMemberBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime


class ExamWithDetails(ExamResponse):
    participants: List[ExamParticipantResponse] = []
    board_members: List[ExamBoardMemberResponse] = []
    event_title: Optional[str] = None
    belt_name: Optional[str] = None
