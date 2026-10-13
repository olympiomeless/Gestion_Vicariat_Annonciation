"""
Actualités (étape 10). Workflow : BROUILLON -> SOUMIS -> PUBLIE | REFUSE.

Règles serveur (jamais seulement côté interface) :
- Une section ne peut créer/modifier/soumettre/supprimer que SES PROPRES
  actualités (section_id dérivé du compte connecté, jamais du client).
- Seul un administrateur peut publier, refuser, ou créer une actualité
  "Vicariat" (section_id NULL).
- Une actualité BROUILLON ou SOUMIS n'est jamais visible publiquement ni
  par les autres sections ; seule PUBLIE l'est.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import CurrentUser, get_client_ip, get_current_user, require_admin
from app.core.database import get_db
from app.models.actualite import Actualite, ActualiteStatus
from app.models.notification import NotificationType
from app.models.user import Role, User
from app.schemas.actualite import (
    ActualiteCreate,
    ActualiteOut,
    ActualiteRejectRequest,
    ActualiteUpdate,
    PaginatedActualites,
)
from app.services.audit_service import log_action
from app.services.notification_service import notify, notify_all_admins

router = APIRouter(prefix="/actualites", tags=["actualites"])


def _actor_label(db: Session, current: CurrentUser) -> str:
    user = db.get(User, current.id)
    return user.username if user else str(current.id)


def _base_query(db: Session):
    return db.query(Actualite).options(joinedload(Actualite.section), joinedload(Actualite.author))  # type: ignore[attr-defined]


def _out(a: Actualite) -> ActualiteOut:
    return ActualiteOut(
        id=a.id,
        title=a.title,
        body=a.body,
        section_id=a.section_id,
        section_name=getattr(a.section, "name", None) if getattr(a, "section", None) else None,
        author_id=a.author_id,
        author_name=getattr(a.author, "full_name", None) if getattr(a, "author", None) else None,
        status=a.status,
        rejection_reason=a.rejection_reason,
        published_at=a.published_at,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


def _can_view(current: CurrentUser, a: Actualite) -> bool:
    if current.is_admin:
        return True
    if a.status == ActualiteStatus.PUBLIE:
        return True
    return a.section_id is not None and a.section_id == current.section_id


def _can_manage(current: CurrentUser, a: Actualite) -> bool:
    if current.is_admin:
        return True
    return a.section_id is not None and a.section_id == current.section_id and a.author_id == current.id


@router.get("", response_model=PaginatedActualites)
def list_actualites(
    status_filter: ActualiteStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    query = _base_query(db)
    if not current.is_admin:
        # Une section voit ses propres actualités (tous statuts) + celles
        # publiées de tout le monde. Jamais les brouillons/soumissions des
        # autres sections.
        query = query.filter(
            (Actualite.status == ActualiteStatus.PUBLIE) | (Actualite.section_id == current.section_id)
        )
    if status_filter is not None:
        query = query.filter(Actualite.status == status_filter)

    total = query.count()
    items = query.order_by(Actualite.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedActualites(items=[_out(a) for a in items], total=total, page=page, page_size=page_size)


@router.get("/{actualite_id}", response_model=ActualiteOut)
def get_actualite(actualite_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    a = _base_query(db).filter(Actualite.id == actualite_id).first()
    if a is None or not _can_view(current, a):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actualité introuvable.")
    return _out(a)


@router.post("", response_model=ActualiteOut, status_code=status.HTTP_201_CREATED)
def create_actualite(
    payload: ActualiteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    if current.is_admin:
        section_id = payload.section_id  # NULL autorisé : actualité du Vicariat entier
    else:
        # Jamais confiance dans le section_id envoyé par le client.
        section_id = current.section_id
        if section_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ce compte n'est rattaché à aucune section.")

    a = Actualite(
        title=payload.title,
        body=payload.body,
        section_id=section_id,
        author_id=current.id,
        status=ActualiteStatus.BROUILLON,
    )
    db.add(a)
    db.commit()
    db.refresh(a)

    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="ACTUALITE_CREATED",
        resource_type="actualite", resource_id=str(a.id), resource_label=a.title, ip_address=get_client_ip(request),
    )
    a = _base_query(db).filter(Actualite.id == a.id).first()
    return _out(a)


@router.put("/{actualite_id}", response_model=ActualiteOut)
def update_actualite(
    actualite_id: uuid.UUID,
    payload: ActualiteUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    a = db.get(Actualite, actualite_id)
    if a is None or not _can_manage(current, a):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actualité introuvable.")
    if not current.is_admin and a.status not in (ActualiteStatus.BROUILLON, ActualiteStatus.REFUSE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette actualité ne peut plus être modifiée (déjà soumise ou publiée).",
        )

    if payload.title is not None:
        a.title = payload.title
    if payload.body is not None:
        a.body = payload.body

    # Une correction après refus repasse en brouillon : la section doit
    # explicitement la resoumettre.
    if not current.is_admin and a.status == ActualiteStatus.REFUSE:
        a.status = ActualiteStatus.BROUILLON
        a.rejection_reason = None

    db.commit()
    db.refresh(a)
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="ACTUALITE_UPDATED",
        resource_type="actualite", resource_id=str(a.id), resource_label=a.title, ip_address=get_client_ip(request),
    )
    a = _base_query(db).filter(Actualite.id == a.id).first()
    return _out(a)


@router.delete("/{actualite_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_actualite(
    actualite_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    a = db.get(Actualite, actualite_id)
    if a is None or not _can_manage(current, a):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actualité introuvable.")
    if not current.is_admin and a.status == ActualiteStatus.PUBLIE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Une actualité publiée ne peut être supprimée que par un administrateur.")

    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="ACTUALITE_DELETED",
        resource_type="actualite", resource_id=str(a.id), resource_label=a.title, ip_address=get_client_ip(request),
    )
    db.delete(a)
    db.commit()


@router.post("/{actualite_id}/submit", response_model=ActualiteOut)
def submit_actualite(
    actualite_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    a = db.get(Actualite, actualite_id)
    if a is None or not _can_manage(current, a):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actualité introuvable.")
    if a.status != ActualiteStatus.BROUILLON:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Seul un brouillon peut être soumis à validation.")

    a.status = ActualiteStatus.SOUMIS
    db.commit()
    db.refresh(a)

    notify_all_admins(
        db, type=NotificationType.ACTUALITE_SUBMITTED,
        message=f"Nouvelle actualité soumise : « {a.title} ».", resource_type="actualite", resource_id=a.id,
    )
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="ACTUALITE_SUBMITTED",
        resource_type="actualite", resource_id=str(a.id), resource_label=a.title, ip_address=get_client_ip(request),
    )
    a = _base_query(db).filter(Actualite.id == a.id).first()
    return _out(a)


@router.post("/{actualite_id}/approve", response_model=ActualiteOut)
def approve_actualite(
    actualite_id: uuid.UUID, request: Request, db: Session = Depends(get_db), current: CurrentUser = Depends(require_admin)
):
    from datetime import datetime, timezone

    a = db.get(Actualite, actualite_id)
    if a is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actualité introuvable.")
    if a.status != ActualiteStatus.SOUMIS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Seule une actualité soumise peut être publiée.")

    a.status = ActualiteStatus.PUBLIE
    a.published_at = datetime.now(timezone.utc)
    a.rejection_reason = None
    db.commit()
    db.refresh(a)

    notify(
        db, user_id=a.author_id, type=NotificationType.ACTUALITE_PUBLISHED,
        message=f"Votre actualité « {a.title} » a été publiée.", resource_type="actualite", resource_id=a.id,
    )
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="ACTUALITE_APPROVED",
        resource_type="actualite", resource_id=str(a.id), resource_label=a.title, ip_address=get_client_ip(request),
    )
    a = _base_query(db).filter(Actualite.id == a.id).first()
    return _out(a)


@router.post("/{actualite_id}/reject", response_model=ActualiteOut)
def reject_actualite(
    actualite_id: uuid.UUID,
    payload: ActualiteRejectRequest,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    a = db.get(Actualite, actualite_id)
    if a is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actualité introuvable.")
    if a.status != ActualiteStatus.SOUMIS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Seule une actualité soumise peut être refusée.")

    a.status = ActualiteStatus.REFUSE
    a.rejection_reason = payload.reason
    db.commit()
    db.refresh(a)

    notify(
        db, user_id=a.author_id, type=NotificationType.ACTUALITE_REJECTED,
        message=f"Votre actualité « {a.title} » a été refusée : {payload.reason}",
        resource_type="actualite", resource_id=a.id,
    )
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="ACTUALITE_REJECTED",
        resource_type="actualite", resource_id=str(a.id), resource_label=a.title, result="SUCCESS",
        ip_address=get_client_ip(request),
    )
    a = _base_query(db).filter(Actualite.id == a.id).first()
    return _out(a)
