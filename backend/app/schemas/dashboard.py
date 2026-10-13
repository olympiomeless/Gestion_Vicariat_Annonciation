import uuid
from typing import Optional

from pydantic import BaseModel

from app.schemas.document import DocumentOut


class SectionStat(BaseModel):
    section_id: uuid.UUID
    section_name: str
    users_count: int
    documents_count: int
    documents_pending_count: int


class AdminDashboardStats(BaseModel):
    sections_count: int
    users_count: int
    users_active_count: int
    documents_count: int
    documents_pending_count: int
    documents_published_count: int
    documents_refused_count: int
    actualites_count: int
    actualites_pending_count: int
    programmes_count: int
    gallery_photos_count: int
    gallery_photos_pending_count: int
    recent_documents: list[DocumentOut]
    pending_documents: list[DocumentOut]
    sections_breakdown: list[SectionStat]


class SectionDashboardStats(BaseModel):
    section_id: uuid.UUID
    section_name: str
    documents_count: int
    documents_pending_count: int
    documents_published_count: int
    documents_refused_count: int
    actualites_count: int
    programmes_count: int
    gallery_photos_count: int
    recent_documents: list[DocumentOut]


class SectionDashboardQuery(BaseModel):
    section_id: Optional[uuid.UUID] = None
