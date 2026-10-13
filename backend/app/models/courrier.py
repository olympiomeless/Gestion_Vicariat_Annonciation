"""
Courriers échangés entre une section et le Bureau du Vicariat (point 4 de la
dernière refonte demandée) : soit un message libre (sujet + corps + pièce
jointe optionnelle), soit une demande de fichier (ex. attestation de camp),
traitée par l'administrateur sous forme de file d'attente.

Contrairement aux Documents/Programme/Bureau de section, un courrier n'est pas
un contenu "publié" : il n'y a pas de notion de validation éditoriale, juste
un statut NOUVEAU -> TRAITE une fois que l'administrateur a répondu (avec une
note et/ou un fichier déposé en réponse, notamment pour une demande de
fichier). D'où un enum dédié (CourrierStatus), distinct de DocumentStatus.
"""
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


class CourrierKind(str, enum.Enum):
    MESSAGE = "MESSAGE"
    DEMANDE_FICHIER = "DEMANDE_FICHIER"


class CourrierStatus(str, enum.Enum):
    NOUVEAU = "NOUVEAU"
    TRAITE = "TRAITE"


class Courrier(Base, TimestampMixin):
    __tablename__ = "courriers"

    id: Mapped[uuid.UUID] = uuid_pk()

    # Toujours renseigné : un courrier part toujours d'une section précise,
    # vers le Bureau du Vicariat (seul destinataire modélisé, cf. décision
    # produit — pas de bureau diocésain distinct).
    section_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sections.id"), nullable=False, index=True
    )
    section: Mapped["Section"] = relationship(foreign_keys=[section_id])

    author_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    author: Mapped["User"] = relationship(foreign_keys=[author_id])

    kind: Mapped[CourrierKind] = mapped_column(Enum(CourrierKind, name="courrier_kind"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    # Pièce jointe optionnelle envoyée par la section (ex. un justificatif).
    # Nom de fichier stocké jamais exposé tel quel — voir has_attachment et la
    # route .../attachment (même pattern que Document.stored_filename).
    attachment_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    attachment_original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    status: Mapped[CourrierStatus] = mapped_column(
        Enum(CourrierStatus, name="courrier_status"), default=CourrierStatus.NOUVEAU, nullable=False, index=True
    )

    # Réponse de l'administrateur : une note libre et/ou un fichier déposé
    # (c'est typiquement ainsi qu'une "demande de fichier" est close : en
    # déposant le document demandé ici).
    response_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    response_original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    handled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    handled_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    handled_by: Mapped[Optional["User"]] = relationship(foreign_keys=[handled_by_id])

    @property
    def has_attachment(self) -> bool:
        return self.attachment_filename is not None

    @property
    def has_response_file(self) -> bool:
        return self.response_filename is not None
