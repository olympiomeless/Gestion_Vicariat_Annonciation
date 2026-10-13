import uuid
from typing import Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_pk


class Section(Base, TimestampMixin):
    __tablename__ = "sections"

    id: Mapped[uuid.UUID] = uuid_pk()
    # slug technique stable (nda, stmarc, ...) utilisé par le site public et
    # conservé depuis l'ancien système pour ne pas casser les liens existants.
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    badge_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # ex: "1ère section — la plus ancienne"
    quartier: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    responsable_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    effectif_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # URL externe manuelle (ancien mécanisme, conservé pour compatibilité) ;
    # remplacée en pratique par photo_filename dès qu'une vraie photo est
    # déposée depuis l'administration — voir has_photo et l'endpoint .../photo.
    photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    photo_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="section")  # noqa: F821

    @property
    def has_photo(self) -> bool:
        return self.photo_filename is not None
