import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MouvementContentOut(BaseModel):
    id: uuid.UUID
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
    updated_at: datetime

    model_config = {"from_attributes": True}


class MouvementContentUpdate(BaseModel):
    intro_title: Optional[str] = Field(default=None, max_length=255)
    intro_paragraph_1: Optional[str] = None
    intro_paragraph_2: Optional[str] = None
    intro_paragraph_3: Optional[str] = None
    theme_annee_label: Optional[str] = Field(default=None, max_length=255)
    theme_annee_quote: Optional[str] = None
    limite_nord: Optional[str] = Field(default=None, max_length=255)
    limite_sud: Optional[str] = Field(default=None, max_length=255)
    limite_ouest: Optional[str] = Field(default=None, max_length=255)
    tutelle: Optional[str] = Field(default=None, max_length=255)
    aumonier_name: Optional[str] = Field(default=None, max_length=255)
    aumonier_role: Optional[str] = Field(default=None, max_length=255)
    vicaire_text: Optional[str] = None
    rang_diocese: Optional[str] = Field(default=None, max_length=32)
