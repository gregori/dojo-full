"""Auth request/response schemas for API validation and serialization."""

from pydantic import BaseModel, EmailStr, Field

from app.schemas.user import UserResponse


class RegisterRequest(BaseModel):
    """Request body for user registration."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=255)
    name: str = Field(min_length=2, max_length=255)


class LoginRequest(BaseModel):
    """Request body for user login."""

    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Response body for login/register/refresh endpoints."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class GoogleCallbackResponse(BaseModel):
    """Response for Google OAuth callback (used internally, not directly returned)."""

    success: bool
    error: str | None = None
