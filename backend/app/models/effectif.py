"""
Effectifs globaux du Vicariat par catégorie (Benjamins, Cadets, ...) —
équivalent à l'ancienne feuille Google Sheets « Effectifs globaux ». Distinct
de `Section.effectif_total`, qui est le total par section.
"""
import uuid

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_pk


class EffectifCategorie(Base, TimestampMixin):
    __tablename__ = "effectif_categories"

    id: Mapped[uuid.UUID] = uuid_pk()
    categorie: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    effectif: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
