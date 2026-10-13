"""
Journal d'audit (point 13 du cahier des charges). Lecture réservée à
l'administrateur. Le journal lui-même est append-only : aucun endpoint
d'écriture/suppression n'est exposé ici, l'écriture se fait uniquement via
app.services.audit_service.log_action() depuis les autres routes.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query

from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, require_admin
from app.core.database import get_db
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogOut, PaginatedAuditLogs

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=PaginatedAuditLogs)
def list_audit_logs(
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    result: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if result:
        query = query.filter(AuditLog.result == result)
    if date_from:
        query = query.filter(AuditLog.created_at >= date_from)
    if date_to:
        query = query.filter(AuditLog.created_at <= date_to)

    total = query.count()
    items = (
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedAuditLogs(
        items=[AuditLogOut.model_validate(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
    )
