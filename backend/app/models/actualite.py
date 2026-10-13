import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.section import Section
    from app.models.user import User


class ActualiteStatus(str, enum.Enum):
    BROUILLON = "BROUILLON"
    SOUMIS = "SOUMIS"          # en attente de validation admin
    PUBLIE = "PUBLIE"
    REFUSE = "REFUSE"


class Actualite(Base, TimestampMixin):
    __tablename__ = "actualites"

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # NULL = actualité générale du Vicariat
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sections.id"), nullable=True, index=True
    )
    section: Mapped[Optional["Section"]] = relationship(foreign_keys=[section_id])
    author_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    author: Mapped["User"] = relationship(foreign_keys=[author_id])

    image_stored_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    attachment_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )

    status: Mapped[ActualiteStatus] = mapped_column(
        Enum(ActualiteStatus, name="actualite_status"), default=ActualiteStatus.BROUILLON, nullable=False, index=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
