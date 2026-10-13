import enum
import uuid
from typing import Optional

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_pk


class NotificationType(str, enum.Enum):
    DOCUMENT_SUBMITTED = "DOCUMENT_SUBMITTED"
    DOCUMENT_APPROVED = "DOCUMENT_APPROVED"
    DOCUMENT_REJECTED = "DOCUMENT_REJECTED"
    ACTUALITE_SUBMITTED = "ACTUALITE_SUBMITTED"
    ACTUALITE_PUBLISHED = "ACTUALITE_PUBLISHED"
    ACTUALITE_REJECTED = "ACTUALITE_REJECTED"
    PHOTO_SUBMITTED = "PHOTO_SUBMITTED"
    PHOTO_APPROVED = "PHOTO_APPROVED"
    PHOTO_REJECTED = "PHOTO_REJECTED"
    PROGRAMME_SUBMITTED = "PROGRAMME_SUBMITTED"
    PROGRAMME_PUBLISHED = "PROGRAMME_PUBLISHED"
    PROGRAMME_REJECTED = "PROGRAMME_REJECTED"
    SECTION_BUREAU_SUBMITTED = "SECTION_BUREAU_SUBMITTED"
    SECTION_BUREAU_PUBLISHED = "SECTION_BUREAU_PUBLISHED"
    SECTION_BUREAU_REJECTED = "SECTION_BUREAU_REJECTED"
    NEW_ACCOUNT = "NEW_ACCOUNT"
    COURRIER_SUBMITTED = "COURRIER_SUBMITTED"
    COURRIER_TRAITE = "COURRIER_TRAITE"


class Notification(Base, TimestampMixin):
    """
    Notification interne à la plateforme. La structure (type, message,
    resource_type/resource_id) est conçue pour pouvoir brancher un envoi par
    e-mail plus tard (un service NotificationService.notify(...) appelé ici
    pourrait aussi déclencher un envoi SMTP) sans changer ce modèle.
    """

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType, name="notification_type"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
