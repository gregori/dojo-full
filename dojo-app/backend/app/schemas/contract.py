"""Schemas for a student's contract history and the on-screen signature request."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.document import DocumentResponse

# Base64 encoding of a ~500KB PNG (generous for a signature image, plus the
# `data:image/png;base64,` prefix) is comfortably under 700K characters;
# bounds the payload the same way the sibling upload path is bounded by
# `MAX_FILE_SIZE_BYTES` (D4), rather than accepting an unbounded string.
MAX_SIGNATURE_PNG_LENGTH = 700_000


class ContractResponse(BaseModel):
    """A single contract history record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    student_id: str
    contract_template_version_id: str
    plan_version_id: str
    signature_method: str | None = None
    status: str
    signed_at: datetime | None = None
    document: DocumentResponse | None = None
    created_at: datetime


class ContractSignOnScreenRequest(BaseModel):
    """Base64-encoded PNG signature captured by the in-app signature pad."""

    signature_png: str = Field(max_length=MAX_SIGNATURE_PNG_LENGTH)
