"""
Programme des activités (étape 11). Workflow : EN_ATTENTE -> PUBLIE | REFUSE
(même logique que les documents : une section propose, l'admin valide).

Règles serveur :
- Une section ne peut créer/modifier/supprimer que les activités de SA
  PROPRE section (section_id toujours dérivé du compte connecté pour un
  compte SECTION, jamais du client).
- Seul un administrateur peut publier/refuser, ou créer une activité
  "Vicariat" (section_id NULL).
- Une activité non publiée n'est visible que par sa section et l'admin.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import CurrentUser, get_client_ip, get_current_user, require_admin
from app.core.database import get_db
from app.models.document import DocumentStatus
from app.models.notification import NotificationType
from app.models.programme import ProgrammeActivite
from app.models.user import User
from app.schemas.programme import (
    PaginatedProgramme,
    ProgrammeCreate,
    ProgrammeOut,
    ProgrammeRejectRequest,
    ProgrammeUpdate,
)
from app.services.audit_service import log_action
from app.services.notification_service import notify, notify_all_admins

router = APIRouter(prefix="/programme", tags=["programme"])


def _actor_label(db: Session, current: CurrentUser) -> str:
    user = db.get(User, current.id)
    return user.username if user else str(current.id)


def _base_query(db: Session):
    return db.query(ProgrammeActivite).options(
        joinedload(ProgrammeActivite.section), joinedload(ProgrammeActivite.author)
    )


def _out(p: ProgrammeActivite) -> ProgrammeOut:
    return ProgrammeOut(
        id=p.id,
        title=p.title,
        description=p.description,
        activity_date=p.activity_date,
        activity_time=p.activity_time,
        location=p.location,
        target_audience=p.target_audience,
        section_id=p.section_id,
        section_name=getattr(p.section, "name", None) if getattr(p, "section", None) else None,
        author_id=p.author_id,
        author_name=getattr(p.author, "full_name", None) if getattr(p, "author", None) else None,
        status=p.status,
        rejection_reason=p.rejection_reason,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _can_view(current: CurrentUser, p: ProgrammeActivite) -> bool:
    if current.is_admin:
        return True
    if p.status == DocumentStatus.PUBLIE:
        return True
    return p.section_id is not None and p.section_id == current.section_id


def _can_manage(current: CurrentUser, p: ProgrammeActivite) -> bool:
    if current.is_admin:
        return True
    return p.section_id is not None and p.section_id == current.section_id and p.author_id == current.id


@router.get("", response_model=PaginatedProgramme)
def list_programme(
    status_filter: DocumentStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    query = _base_query(db)
    if not current.is_admin:
        query = query.filter(
            (ProgrammeActivite.status == DocumentStatus.PUBLIE) | (ProgrammeActivite.section_id == current.section_id)
        )
    if status_filter is not None:
        query = query.filter(ProgrammeActivite.status == status_filter)

    total = query.count()
    items = (
        query.order_by(ProgrammeActivite.activity_date.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedProgramme(items=[_out(p) for p in items], total=total, page=page, page_size=page_size)


@router.get("/{programme_id}", response_model=ProgrammeOut)
def get_programme(
    programme_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)
):
    p = _base_query(db).filter(ProgrammeActivite.id == programme_id).first()
    if p is None or not _can_view(current, p):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activité introuvable.")
    return _out(p)


@router.post("", response_model=ProgrammeOut, status_code=status.HTTP_201_CREATED)
def create_programme(
    payload: ProgrammeCreate,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    if current.is_admin:
        section_id = payload.section_id
    else:
        section_id = current.section_id
        if section_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Ce compte n'est rattaché à aucune section."
            )

    p = ProgrammeActivite(
        title=payload.title,
        description=payload.description,
        activity_date=payload.activity_date,
        activity_time=payload.activity_time,
        location=payload.location,
        target_audience=payload.target_audience,
        section_id=section_id,
        author_id=current.id,
        status=DocumentStatus.EN_ATTENTE,
    )
    db.add(p)
    db.commit()
    db.refresh(p)

    notify_all_admins(
        db, type=NotificationType.PROGRAMME_SUBMITTED,
        message=f"Nouvelle activité proposée au programme : « {p.title} ».",
        resource_type="programme", resource_id=p.id,
    )
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="PROGRAMME_CREATED",
        resource_type="programme", resource_id=str(p.id), resource_label=p.title, ip_address=get_client_ip(request),
    )
    p = _base_query(db).filter(ProgrammeActivite.id == p.id).first()
    return _out(p)


@router.put("/{programme_id}", response_model=ProgrammeOut)
def update_programme(
    programme_id: uuid.UUID,
    payload: ProgrammeUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    p = db.get(ProgrammeActivite, programme_id)
    if p is None or not _can_manage(current, p):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activité introuvable.")
    if not current.is_admin and p.status == DocumentStatus.PUBLIE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Une activité déjà publiée ne peut être modifiée que par un administrateur."
        )

    for field in ("title", "description", "activity_date", "activity_time", "location", "target_audience"):
        value = getattr(payload, field)
        if value is not None:
            setattr(p, field, value)

    # Une correction après refus repasse automatiquement en attente de validation.
    if not current.is_admin and p.status == DocumentStatus.REFUSE:
        p.status = DocumentStatus.EN_ATTENTE
        p.rejection_reason = None

    db.commit()
    db.refresh(p)
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="PROGRAMME_UPDATED",
        resource_type="programme", resource_id=str(p.id), resource_label=p.title, ip_address=get_client_ip(request),
    )
    p = _base_query(db).filter(ProgrammeActivite.id == p.id).first()
    return _out(p)


@router.delete("/{programme_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_programme(
    programme_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    p = db.get(ProgrammeActivite, programme_id)
    if p is None or not _can_manage(current, p):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activité introuvable.")
    if not current.is_admin and p.status == DocumentStatus.PUBLIE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une activité publiée ne peut être supprimée que par un administrateur.",
        )

    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="PROGRAMME_DELETED",
        resource_type="programme", resource_id=str(p.id), resource_label=p.title, ip_address=get_client_ip(request),
    )
    db.delete(p)
    db.commit()


@router.post("/{programme_id}/approve", response_model=ProgrammeOut)
def approve_programme(
    programme_id: uuid.UUID, request: Request, db: Session = Depends(get_db), current: CurrentUser = Depends(require_admin)
):
    p = db.get(ProgrammeActivite, programme_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activité introuvable.")
    if p.status != DocumentStatus.EN_ATTENTE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Seule une activité en attente peut être publiée.")

    p.status = DocumentStatus.PUBLIE
    p.rejection_reason = None
    db.commit()
    db.refresh(p)

    notify(
        db, user_id=p.author_id, type=NotificationType.PROGRAMME_PUBLISHED,
        message=f"L'activité « {p.title} » a été publiée au programme.", resource_type="programme", resource_id=p.id,
    )
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="PROGRAMME_APPROVED",
        resource_type="programme", resource_id=str(p.id), resource_label=p.title, ip_address=get_client_ip(request),
    )
    p = _base_query(db).filter(ProgrammeActivite.id == p.id).first()
    return _out(p)


@router.post("/{programme_id}/reject", response_model=ProgrammeOut)
def reject_programme(
    programme_id: uuid.UUID,
    payload: ProgrammeRejectRequest,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    p = db.get(ProgrammeActivite, programme_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activité introuvable.")
    if p.status != DocumentStatus.EN_ATTENTE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Seule une activité en attente peut être refusée.")

    p.status = DocumentStatus.REFUSE
    p.rejection_reason = payload.reason
    db.commit()
    db.refresh(p)

    notify(
        db, user_id=p.author_id, type=NotificationType.PROGRAMME_REJECTED,
        message=f"L'activité « {p.title} » a été refusée : {payload.reason}",
        resource_type="programme", resource_id=p.id,
    )
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="PROGRAMME_REJECTED",
        resource_type="programme", resource_id=str(p.id), resource_label=p.title, ip_address=get_client_ip(request),
    )
    p = _base_query(db).filter(ProgrammeActivite.id == p.id).first()
    return _out(p)
