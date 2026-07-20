"""Schemas for medical exam records and the public self-service flow."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.document import DocumentResponse


class MedicalExamResponse(BaseModel):
    """A single medical exam history record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    exam_date: datetime
    expires_at: datetime
    status: str
    document: DocumentResponse | None = None
    created_at: datetime


class MedicalExamStatus(BaseModel):
    """Computed medical-exam status for a student."""

    student_id: str
    status: str
    exam_date: datetime | None = None
    expires_at: datetime | None = None


class MedicalExamDashboardItem(MedicalExamStatus):
    """A status entry enriched with identity fields for instructor dashboards."""

    student_name: str
    registration_number: str


class MedicalExamPublicResponse(BaseModel):
    """Privacy-preserving response for public medical-exam submissions."""

    status: str
    message: str
