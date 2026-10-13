"""
Création des notifications internes.

Conçu pour qu'un envoi e-mail puisse être branché plus tard (point 15 :
"prévoir l'architecture permettant d'ajouter plus tard les notifications par
e-mail") : il suffirait d'ajouter un appel à un EmailService ici, sans changer
les appelants.
"""
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType


def notify(
    db: Session,
    *,
    user_id: uuid.UUID,
    type: NotificationType,
    message: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[uuid.UUID] = None,
    commit: bool = True,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        type=type,
        message=message,
        resource_type=resource_type,
        resource_id=resource_id,
    )
    db.add(notif)
    if commit:
        db.commit()
    # Point d'extension futur : envoi e-mail / push ici, ex.
    # email_service.send_notification_email(user_id, message)
    return notif


def notify_all_admins(
    db: Session,
    *,
    type: NotificationType,
    message: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[uuid.UUID] = None,
) -> None:
    from app.models.user import Role, User  # import local pour éviter un cycle

    admins = db.query(User).join(Role).filter(Role.name == Role.ADMIN, User.is_active.is_(True)).all()
    for admin in admins:
        notify(
            db,
            user_id=admin.id,
            type=type,
            message=message,
            resource_type=resource_type,
            resource_id=resource_id,
            commit=False,
        )
    db.commit()
