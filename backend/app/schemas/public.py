"""
Formes de sortie dédiées à l'API PUBLIQUE (étape 14) : jamais d'ID interne
d'auteur, jamais de statut de validation ou de motif de refus, jamais un
champ qui n'a pas de raison d'être visible sans connexion. Un contenu qui
n'est pas encore publié n'apparaît tout simplement jamais ici — le filtrage
se fait dans app/api/v1/public.py, jamais seulement dans ces schémas.
"""
import uuid
from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel


class PublicSectionOut(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    badge_label: Optional[str]
    quartier: Optional[str]
    responsable_name: Optional[str]
    description: Optional[str]
    effectif_total: int
    photo_url: Optional[str]
    has_photo: bool

    model_config = {"from_attributes": True}


class PublicBureauMemberOut(BaseModel):
    id: uuid.UUID
    full_name: str
    role_title: str
    paroisse: Optional[str]
    rang: Optional[str]
    photo_key: Optional[str]
    has_photo: bool
    display_order: int

    model_config = {"from_attributes": True}


class PublicEffectifOut(BaseModel):
    categorie: str
    effectif: int
    display_order: int

    model_config = {"from_attributes": True}


class PublicProgrammeOut(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    activity_date: date
    activity_time: Optional[time]
    location: Optional[str]
    target_audience: Optional[str]
    section_slug: Optional[str] = None
    section_name: Optional[str] = None

    model_config = {"from_attributes": True}


class PublicActualiteOut(BaseModel):
    id: uuid.UUID
    title: str
    body: str
    section_slug: Optional[str] = None
    section_name: Optional[str] = None
    published_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class PublicGalleryPhotoOut(BaseModel):
    id: uuid.UUID
    caption: Optional[str]
    section_slug: Optional[str] = None
    section_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PublicDocumentOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    category_name: Optional[str] = None
    section_name: Optional[str] = None
    original_filename: str
    mime_type: str
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PublicMouvementOut(BaseModel):
    intro_title: str
    intro_paragraph_1: str
    intro_paragraph_2: str
    intro_paragraph_3: str
    theme_annee_label: str
    theme_annee_quote: str
    limite_nord: str
    limite_sud: str
    limite_ouest: str
    tutelle: str
    aumonier_name: str
    aumonier_role: str
    vicaire_text: str
    rang_diocese: str

    model_config = {"from_attributes": True}


class PaginatedPublicProgramme(BaseModel):
    items: list[PublicProgrammeOut]
    total: int
    page: int
    page_size: int


class PaginatedPublicActualites(BaseModel):
    items: list[PublicActualiteOut]
    total: int
    page: int
    page_size: int


class PaginatedPublicGallery(BaseModel):
    items: list[PublicGalleryPhotoOut]
    total: int
    page: int
    page_size: int


class PaginatedPublicDocuments(BaseModel):
    items: list[PublicDocumentOut]
    total: int
    page: int
    page_size: int
