"""
Contenu éditorial de la section « Le mouvement » du site public (identité du
vicariat, thème de l'année pastorale, limites territoriales, accompagnement
spirituel). Instance UNIQUE (singleton) : pas de notion de section, modifiable
uniquement par l'administrateur — voir get_or_create_mouvement_content() dans
app/api/v1/mouvement.py, qui garantit qu'il existe toujours exactement une
ligne (créée avec le contenu d'origine du site si la table est encore vide).
"""
import uuid

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_pk


class MouvementContent(Base, TimestampMixin):
    __tablename__ = "mouvement_content"

    id: Mapped[uuid.UUID] = uuid_pk()

    intro_title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    intro_paragraph_1: Mapped[str] = mapped_column(Text, nullable=False, default="")
    intro_paragraph_2: Mapped[str] = mapped_column(Text, nullable=False, default="")
    intro_paragraph_3: Mapped[str] = mapped_column(Text, nullable=False, default="")

    theme_annee_label: Mapped[str] = mapped_column(Text, nullable=False, default="")
    theme_annee_quote: Mapped[str] = mapped_column(Text, nullable=False, default="")

    limite_nord: Mapped[str] = mapped_column(Text, nullable=False, default="")
    limite_sud: Mapped[str] = mapped_column(Text, nullable=False, default="")
    limite_ouest: Mapped[str] = mapped_column(Text, nullable=False, default="")
    tutelle: Mapped[str] = mapped_column(Text, nullable=False, default="")

    aumonier_name: Mapped[str] = mapped_column(Text, nullable=False, default="")
    aumonier_role: Mapped[str] = mapped_column(Text, nullable=False, default="")
    vicaire_text: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Rang du vicariat parmi l'ensemble des vicariats du diocèse (ex. "1/13"),
    # affiché dans le bandeau d'accueil du site public.
    rang_diocese: Mapped[str] = mapped_column(Text, nullable=False, default="")
