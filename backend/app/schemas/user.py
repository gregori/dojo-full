"""User request/response schemas for API validation and serialization."""

from datetime import datetime

from pydantic import BaseModel, Field


class RoleAssignmentRequest(BaseModel):
    """Request body for assigning a role to a user."""

    role: str = Field(pattern=r"^(student|instructor|super-admin)$")


class UserListResponse(BaseModel):
    """Paginated list of users."""

    users: list["UserResponse"]
    total: int
    offset: int
    limit: int


class UserResponse(BaseModel):
    """User data returned in API responses."""

    id: str
    org_id: str
    email: str
    name: str
    roles: list[str]
    auth_provider: str
    google_sub: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
