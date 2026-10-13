"""Effectifs globaux du Vicariat par catégorie — lecture connectée, écriture admin."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_client_ip, get_current_user, require_admin
from app.core.database import get_db
from app.models.effectif import EffectifCategorie
from app.models.user import User
from app.schemas.effectif import EffectifCategorieCreate, EffectifCategorieOut, EffectifCategorieUpdate
from app.services.audit_service import log_action

router = APIRouter(prefix="/effectifs", tags=["effectifs"])


def _actor_label(db: Session, current: CurrentUser) -> str:
    user = db.get(User, current.id)
    return user.username if user else str(current.id)


@router.get("", response_model=list[EffectifCategorieOut])
def list_effectifs(db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    return db.query(EffectifCategorie).order_by(EffectifCategorie.display_order.asc()).all()


@router.post("", response_model=EffectifCategorieOut, status_code=status.HTTP_201_CREATED)
def create_effectif(
    payload: EffectifCategorieCreate, request: Request, db: Session = Depends(get_db), current: CurrentUser = Depends(require_admin)
):
    existing = db.query(EffectifCategorie).filter(EffectifCategorie.categorie == payload.categorie).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cette catégorie existe déjà.")

    categorie = EffectifCategorie(**payload.model_dump())
    db.add(categorie)
    db.commit()
    db.refresh(categorie)
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="EFFECTIF_CREATED",
        resource_type="effectif_categorie", resource_id=str(categorie.id), resource_label=categorie.categorie,
        ip_address=get_client_ip(request),
    )
    return categorie


@router.put("/{categorie_id}", response_model=EffectifCategorieOut)
def update_effectif(
    categorie_id: uuid.UUID,
    payload: EffectifCategorieUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    categorie = db.get(EffectifCategorie, categorie_id)
    if categorie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(categorie, field, value)

    db.commit()
    db.refresh(categorie)
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="EFFECTIF_UPDATED",
        resource_type="effectif_categorie", resource_id=str(categorie.id), resource_label=categorie.categorie,
        ip_address=get_client_ip(request),
    )
    return categorie


@router.delete("/{categorie_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_effectif(
    categorie_id: uuid.UUID, request: Request, db: Session = Depends(get_db), current: CurrentUser = Depends(require_admin)
):
    categorie = db.get(EffectifCategorie, categorie_id)
    if categorie is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable.")

    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="EFFECTIF_DELETED",
        resource_type="effectif_categorie", resource_id=str(categorie.id), resource_label=categorie.categorie,
        ip_address=get_client_ip(request),
    )
    db.delete(categorie)
    db.commit()
