import uuid

from pydantic import BaseModel, Field


class EffectifCategorieCreate(BaseModel):
    categorie: str = Field(min_length=1, max_length=100)
    effectif: int = Field(ge=0)
    display_order: int = 0


class EffectifCategorieUpdate(BaseModel):
    effectif: int | None = Field(default=None, ge=0)
    display_order: int | None = None


class EffectifCategorieOut(BaseModel):
    id: uuid.UUID
    categorie: str
    effectif: int
    display_order: int

    model_config = {"from_attributes": True}
