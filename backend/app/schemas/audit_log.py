import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    user_label: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    resource_label: Optional[str]
    result: str
    ip_address: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedAuditLogs(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    page_size: int
