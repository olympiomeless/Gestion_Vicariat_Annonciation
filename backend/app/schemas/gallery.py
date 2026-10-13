import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.document import DocumentStatus


class GalleryPhotoUpdate(BaseModel):
    caption: Optional[str] = Field(default=None, max_length=500)


class GalleryPhotoRejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class GalleryPhotoOut(BaseModel):
    id: uuid.UUID
    caption: Optional[str]
    original_filename: str
    section_id: Optional[uuid.UUID]
    section_name: Optional[str] = None
    programme_id: Optional[uuid.UUID]
    author_id: uuid.UUID
    author_name: Optional[str] = None
    status: DocumentStatus
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedGalleryPhotos(BaseModel):
    items: list[GalleryPhotoOut]
    total: int
    page: int
    page_size: int
