import uuid
from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, Field

from app.models.document import DocumentStatus


class ProgrammeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    activity_date: date
    activity_time: Optional[time] = None
    location: Optional[str] = Field(default=None, max_length=255)
    target_audience: Optional[str] = Field(default=None, max_length=255)
    section_id: Optional[uuid.UUID] = None  # ignoré côté serveur pour un compte SECTION


class ProgrammeUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    activity_date: Optional[date] = None
    activity_time: Optional[time] = None
    location: Optional[str] = Field(default=None, max_length=255)
    target_audience: Optional[str] = Field(default=None, max_length=255)


class ProgrammeRejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)


class ProgrammeOut(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    activity_date: date
    activity_time: Optional[time]
    location: Optional[str]
    target_audience: Optional[str]
    section_id: Optional[uuid.UUID]
    section_name: Optional[str] = None
    author_id: uuid.UUID
    author_name: Optional[str] = None
    status: DocumentStatus
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedProgramme(BaseModel):
    items: list[ProgrammeOut]
    total: int
    page: int
    page_size: int
