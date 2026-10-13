import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.section import Section
    from app.models.user import User


class DocumentStatus(str, enum.Enum):
    EN_ATTENTE = "EN_ATTENTE"
    PUBLIE = "PUBLIE"
    REFUSE = "REFUSE"


class DocumentCategory(Base):
    __tablename__ = "document_categories"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    # Catégories livrées par défaut (Rapport, Compte rendu, ...) vs créées par
    # l'admin ensuite. Les catégories système ne peuvent pas être supprimées.
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    documents: Mapped[list["Document"]] = relationship(back_populates="category")


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Nom de fichier aléatoire sur le disque (jamais le nom fourni par
    # l'utilisateur) — voir app/services/storage_service.py pour la génération
    # et la validation. `original_filename` est conservé uniquement pour
    # l'affichage / le téléchargement, jamais utilisé comme chemin réel.
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(150), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    category_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("document_categories.id"), nullable=False, index=True
    )
    category: Mapped["DocumentCategory"] = relationship(back_populates="documents")

    # NULL = document du Vicariat (ajouté par un admin, pas rattaché à une section)
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sections.id"), nullable=True, index=True
    )
    section: Mapped[Optional["Section"]] = relationship(foreign_keys=[section_id])

    author_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    author: Mapped["User"] = relationship(foreign_keys=[author_id])

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.EN_ATTENTE, nullable=False, index=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
