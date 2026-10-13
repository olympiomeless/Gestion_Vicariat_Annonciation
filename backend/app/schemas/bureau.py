import uuid
from typing import Optional

from pydantic import BaseModel, Field


class BureauMemberCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    role_title: str = Field(min_length=1, max_length=255)
    paroisse: Optional[str] = Field(default=None, max_length=255)
    rang: Optional[str] = Field(default=None, max_length=20)
    display_order: int = 0
    is_active: bool = True


class BureauMemberUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=255)
    role_title: Optional[str] = Field(default=None, max_length=255)
    paroisse: Optional[str] = Field(default=None, max_length=255)
    rang: Optional[str] = Field(default=None, max_length=20)
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class BureauMemberOut(BaseModel):
    id: uuid.UUID
    full_name: str
    role_title: str
    paroisse: Optional[str]
    rang: Optional[str]
    photo_key: Optional[str]
    has_photo: bool
    display_order: int
    is_active: bool

    model_config = {"from_attributes": True}
