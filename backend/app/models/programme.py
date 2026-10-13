import uuid
from datetime import date, time
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum, ForeignKey, String, Text, Time
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_pk
from app.models.document import DocumentStatus

if TYPE_CHECKING:
    from app.models.section import Section
    from app.models.user import User


class ProgrammeActivite(Base, TimestampMixin):
    __tablename__ = "programmes"

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    activity_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    target_audience: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # NULL = activité du Vicariat entier
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sections.id"), nullable=True, index=True
    )
    section: Mapped[Optional["Section"]] = relationship(foreign_keys=[section_id])
    author_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    author: Mapped["User"] = relationship(foreign_keys=[author_id])

    # Réutilise l'enum document_status (EN_ATTENTE/PUBLIE/REFUSE) déjà en
    # base : même workflow de validation que les documents et la galerie.
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.EN_ATTENTE, nullable=False, index=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
