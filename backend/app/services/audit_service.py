"""Écriture du journal d'audit (append-only, jamais modifié)."""
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_action(
    db: Session,
    *,
    user_id: Optional[uuid.UUID],
    user_label: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    resource_label: Optional[str] = None,
    result: str = "SUCCESS",
    ip_address: Optional[str] = None,
    commit: bool = True,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        user_label=user_label,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        resource_label=resource_label,
        result=result,
        ip_address=ip_address,
    )
    db.add(entry)
    if commit:
        db.commit()
    return entry
