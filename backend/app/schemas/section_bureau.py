import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.document import DocumentStatus


class SectionBureauMemberCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    role_title: str = Field(min_length=1, max_length=255)
    display_order: int = 0
    section_id: Optional[uuid.UUID] = None  # ignoré côté serveur pour un compte SECTION


class SectionBureauMemberUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=255)
    role_title: Optional[str] = Field(default=None, max_length=255)
    display_order: Optional[int] = None


class SectionBureauMemberRejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class SectionBureauMemberOut(BaseModel):
    id: uuid.UUID
    section_id: uuid.UUID
    section_name: Optional[str] = None
    full_name: str
    role_title: str
    display_order: int
    has_photo: bool
    author_id: uuid.UUID
    author_name: Optional[str] = None
    status: DocumentStatus
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
