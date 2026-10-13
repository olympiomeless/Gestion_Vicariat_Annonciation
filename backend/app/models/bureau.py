"""
Membres du Bureau du Vicariat (contenu géré par l'administrateur uniquement —
pas de workflow de soumission par une section : le bureau est une instance
unique commune à tout le Vicariat).
"""
import uuid
from typing import Optional

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_pk


class BureauMember(Base, TimestampMixin):
    __tablename__ = "bureau_members"

    id: Mapped[uuid.UUID] = uuid_pk()
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_title: Mapped[str] = mapped_column(String(255), nullable=False)
    paroisse: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rang: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # AA / AC / AP...
    # Clé technique de la photo (héritée de l'ancien système à base de Google
    # Sheets) ; conservée pour compatibilité mais remplacée en pratique par
    # photo_filename dès qu'une vraie photo est déposée depuis l'administration.
    photo_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Nom de fichier stocké (géré par le backend de stockage), jamais exposé
    # tel quel au client — voir has_photo et l'endpoint .../photo.
    photo_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def has_photo(self) -> bool:
        return self.photo_filename is not None
