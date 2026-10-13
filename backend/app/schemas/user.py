import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.auth import validate_password_strength


USERNAME_PATTERN = r"^[a-z0-9][a-z0-9._-]{2,49}$"


class UserCreate(BaseModel):
    username: str = Field(pattern=USERNAME_PATTERN, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: str = Field(min_length=1, max_length=255)
    password: str
    role: str = Field(pattern=r"^[A-Z_]+$")
    section_id: Optional[uuid.UUID] = None

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    section_id: Optional[uuid.UUID] = None


class AdminResetPasswordRequest(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserAdminOut(BaseModel):
    id: uuid.UUID
    username: str
    email: Optional[str] = None
    full_name: str
    role: str
    section_id: Optional[uuid.UUID] = None
    section_name: Optional[str] = None
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
