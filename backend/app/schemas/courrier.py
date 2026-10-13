import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.courrier import CourrierKind, CourrierStatus


class CourrierRespondRequest(BaseModel):
    response_note: Optional[str] = Field(default=None, max_length=2000)


class CourrierOut(BaseModel):
    id: uuid.UUID
    section_id: uuid.UUID
    section_name: Optional[str] = None
    kind: CourrierKind
    subject: str
    body: str
    has_attachment: bool
    attachment_original_filename: Optional[str] = None
    status: CourrierStatus
    response_note: Optional[str] = None
    has_response_file: bool
    response_original_filename: Optional[str] = None
    handled_at: Optional[datetime] = None
    handled_by_id: Optional[uuid.UUID] = None
    handled_by_name: Optional[str] = None
    author_id: uuid.UUID
    author_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
