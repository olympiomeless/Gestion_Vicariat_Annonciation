"""
Notifications internes (point 12 du cahier des charges). Un utilisateur ne
peut voir et marquer comme lues que SES PROPRES notifications — vérifié
côté serveur sur chaque endpoint, jamais seulement filtré côté client.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user
from app.core.database import get_db
from app.models.notification import Notification
from app.schemas.notification import NotificationOut, PaginatedNotifications

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=PaginatedNotifications)
def list_notifications(
    unread_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    query = db.query(Notification).filter(Notification.user_id == current.id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))

    total = query.count()
    unread_count = (
        db.query(func.count(Notification.id))
        .filter(Notification.user_id == current.id, Notification.is_read.is_(False))
        .scalar()
        or 0
    )
    items = (
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaginatedNotifications(
        items=[NotificationOut.model_validate(n) for n in items],
        total=total,
        unread_count=unread_count,
        page=page,
        page_size=page_size,
    )


@router.put("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    notification = db.get(Notification, notification_id)
    # 404, jamais 403 : on ne révèle pas l'existence de la notification d'un
    # autre utilisateur.
    if notification is None or notification.user_id != current.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification introuvable.")

    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return NotificationOut.model_validate(notification)


@router.put("/read-all", response_model=dict)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    updated = (
        db.query(Notification)
        .filter(Notification.user_id == current.id, Notification.is_read.is_(False))
        .update({Notification.is_read: True})
    )
    db.commit()
    return {"updated": updated}
