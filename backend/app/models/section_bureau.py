"""
Bureau PROPRE à chaque section (distinct du Bureau du Vicariat, voir
app/models/bureau.py, qui reste exclusivement géré par l'administrateur).

Une section peut proposer/modifier les membres de son propre bureau, mais
toute publication passe par une validation de l'administrateur — même
workflow EN_ATTENTE -> PUBLIE | REFUSE que le programme et les documents
(voir app/api/v1/programme.py pour la logique serveur équivalente).
"""
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_pk
from app.models.document import DocumentStatus

if TYPE_CHECKING:
    from app.models.section import Section
    from app.models.user import User


class SectionBureauMember(Base, TimestampMixin):
    __tablename__ = "section_bureau_members"

    id: Mapped[uuid.UUID] = uuid_pk()

    # Toujours renseigné : contrairement au programme, un membre de bureau de
    # section n'a pas d'équivalent "Vicariat entier" (section_id NULL).
    section_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sections.id"), nullable=False, index=True
    )
    section: Mapped["Section"] = relationship(foreign_keys=[section_id])

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_title: Mapped[str] = mapped_column(String(255), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Nom de fichier stocké (backend de stockage), jamais exposé tel quel —
    # voir has_photo et les routes .../photo (même pattern que BureauMember).
    photo_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    author_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    author: Mapped["User"] = relationship(foreign_keys=[author_id])

    # Réutilise l'enum document_status (EN_ATTENTE/PUBLIE/REFUSE) déjà en
    # base : même workflow de validation que les documents et le programme.
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status"), default=DocumentStatus.EN_ATTENTE, nullable=False, index=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    @property
    def has_photo(self) -> bool:
        return self.photo_filename is not None
