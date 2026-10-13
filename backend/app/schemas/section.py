import uuid
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.user import USERNAME_PATTERN


class SectionBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    badge_label: Optional[str] = None
    quartier: Optional[str] = None
    responsable_name: Optional[str] = None
    description: Optional[str] = None
    effectif_total: int = 0
    photo_url: Optional[str] = None
    display_order: int = 0


class SectionCreate(SectionBase):
    slug: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9_-]+$")
    # Optionnel : si renseigné, le compte de connexion de la section (rôle
    # SECTION) est créé dans la même opération, avec un mot de passe par
    # défaut généré côté serveur (voir create_section) — évite de devoir
    # créer la section puis son compte en deux étapes séparées.
    username: Optional[str] = Field(default=None, pattern=USERNAME_PATTERN, min_length=3, max_length=50)


class SectionUpdate(BaseModel):
    name: Optional[str] = None
    badge_label: Optional[str] = None
    quartier: Optional[str] = None
    responsable_name: Optional[str] = None
    description: Optional[str] = None
    effectif_total: Optional[int] = None
    photo_url: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class SectionOut(SectionBase):
    id: uuid.UUID
    slug: str
    is_active: bool
    has_photo: bool

    model_config = {"from_attributes": True}


class SectionCreateOut(SectionOut):
    """
    Réponse à la création d'une section. Si un compte a été créé en même
    temps (voir SectionCreate.username), le mot de passe par défaut généré
    est inclus ICI UNE SEULE FOIS — il n'est jamais récupérable ensuite (ni
    stocké en clair), comme pour toute création/réinitialisation de mot de
    passe ailleurs dans ce backend.
    """

    generated_username: Optional[str] = None
    generated_password: Optional[str] = None
