import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_pk
from app.models.document import DocumentStatus

if TYPE_CHECKING:
    from app.models.programme import ProgrammeActivite
    from app.models.section import Section
    from app.models.user import User


class GalleryPhoto(Base, TimestampMixin):
    __tablename__ = "gallery_photos"

    id: Mapped[uuid.UUID] = uuid_pk()
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False, default="photo.jpg")
    caption: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sections.id"), nullable=True, index=True
    )
    section: Mapped[Optional["Section"]] = relationship(foreign_keys=[section_id])
    programme_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("programmes.id"), nullable=True
    )
    programme: Mapped[Optional["ProgrammeActivite"]] = relationship(foreign_keys=[programme_id])
    author_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    author: Mapped["User"] = relationship(foreign_keys=[author_id])

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.EN_ATTENTE, nullable=False, index=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
