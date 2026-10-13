import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.document import DocumentStatus


class DocumentCategoryOut(BaseModel):
    id: uuid.UUID
    name: str
    is_system: bool

    model_config = {"from_attributes": True}


class DocumentCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class DocumentOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    original_filename: str
    mime_type: str
    size_bytes: int
    category_id: uuid.UUID
    category_name: Optional[str] = None
    section_id: Optional[uuid.UUID]
    section_name: Optional[str] = None
    author_id: uuid.UUID
    author_name: Optional[str] = None
    status: DocumentStatus
    rejection_reason: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    category_id: Optional[uuid.UUID] = None


class DocumentRejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class PaginatedDocuments(BaseModel):
    items: list[DocumentOut]
    total: int
    page: int
    page_size: int
