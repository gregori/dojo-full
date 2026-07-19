from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str
    is_active: bool = True
    organization_id: str | None = None
    dojo_id: str | None = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime


class UserLogin(BaseModel):
    username: str  # email
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None  # user id
    role: str | None = None
