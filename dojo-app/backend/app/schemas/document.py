"""Schemas for generic document metadata."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentResponse(BaseModel):
    """Document metadata exposed to authorized clients. Never includes file bytes or the raw storage key."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    document_type: str
    mime_type: str
    size_bytes: int
    uploaded_by_user_id: str | None = None
    uploaded_by_student_self: bool
    status: str
    created_at: datetime
