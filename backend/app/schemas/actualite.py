import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.actualite import ActualiteStatus


class ActualiteCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    section_id: Optional[uuid.UUID] = None  # ignoré côté serveur pour un compte SECTION


class ActualiteUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    body: Optional[str] = None


class ActualiteRejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class ActualiteOut(BaseModel):
    id: uuid.UUID
    title: str
    body: str
    section_id: Optional[uuid.UUID]
    section_name: Optional[str] = None
    author_id: uuid.UUID
    author_name: Optional[str] = None
    status: ActualiteStatus
    rejection_reason: Optional[str] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedActualites(BaseModel):
    items: list[ActualiteOut]
    total: int
    page: int
    page_size: int
