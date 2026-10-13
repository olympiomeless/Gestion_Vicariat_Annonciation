"""
Bureau propre à chaque section (distinct du Bureau du Vicariat, voir
app/api/v1/bureau.py, qui reste exclusivement administré par l'ADMIN).

Workflow identique à celui du programme (app/api/v1/programme.py) :
EN_ATTENTE -> PUBLIE | REFUSE. Une section propose, l'administrateur valide —
aucune section (même celle propriétaire) ne peut publier elle-même, et un
administrateur qui crée une entrée passe lui aussi par EN_ATTENTE (même
convention que partout ailleurs dans ce backend : pas d'auto-publication).

Règles serveur :
- Une section ne peut créer/modifier/supprimer que les membres de SON PROPRE
  bureau (section_id toujours dérivé du compte connecté pour un compte
  SECTION, jamais du client).
- Seul un administrateur peut publier/refuser.
- Un membre non publié n'est visible que par sa section et l'admin.
"""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.api.deps import CurrentUser, get_client_ip, get_current_user, require_admin
from app.api.v1.documents import HEADER_SNIFF_BYTES, _save_with_size_limit
from app.core.config import settings
from app.core.database import get_db
from app.models.document import DocumentStatus
from app.models.notification import NotificationType
from app.models.section_bureau import SectionBureauMember
from app.models.user import User
from app.schemas.section_bureau import (
    SectionBureauMemberCreate,
    SectionBureauMemberOut,
    SectionBureauMemberRejectRequest,
    SectionBureauMemberUpdate,
)
from app.services.audit_service import log_action
from app.services.file_validation import IMAGE_EXTENSIONS, FileValidationError, validate_upload
from app.services.notification_service import notify, notify_all_admins
from app.storage.factory import get_storage_backend

router = APIRouter(prefix="/section-bureau", tags=["section-bureau"])

PHOTO_MIME = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def _actor_label(db: Session, current: CurrentUser) -> str:
    user = db.get(User, current.id)
    return user.username if user else str(current.id)


def _base_query(db: Session):
    return db.query(SectionBureauMember).options(
        joinedload(SectionBureauMember.section), joinedload(SectionBureauMember.author)
    )


def _out(m: SectionBureauMember) -> SectionBureauMemberOut:
    return SectionBureauMemberOut(
        id=m.id,
        section_id=m.section_id,
        section_name=getattr(m.section, "name", None) if getattr(m, "section", None) else None,
        full_name=m.full_name,
        role_title=m.role_title,
        display_order=m.display_order,
        has_photo=m.has_photo,
        author_id=m.author_id,
        author_name=getattr(m.author, "full_name", None) if getattr(m, "author", None) else None,
        status=m.status,
        rejection_reason=m.rejection_reason,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _can_view(current: CurrentUser, m: SectionBureauMember) -> bool:
    if current.is_admin:
        return True
    if m.status == DocumentStatus.PUBLIE:
        return True
    return m.section_id == current.section_id


def _can_manage(current: CurrentUser, m: SectionBureauMember) -> bool:
    if current.is_admin:
        return True
    return m.section_id == current.section_id and m.author_id == current.id


@router.get("", response_model=list[SectionBureauMemberOut])
def list_section_bureau(
    section_id: uuid.UUID | None = None,
    status_filter: DocumentStatus | None = None,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    query = _base_query(db)
    if not current.is_admin:
        query = query.filter(
            (SectionBureauMember.status == DocumentStatus.PUBLIE)
            | (SectionBureauMember.section_id == current.section_id)
        )
    if section_id is not None:
        query = query.filter(SectionBureauMember.section_id == section_id)
    if status_filter is not None:
        query = query.filter(SectionBureauMember.status == status_filter)

    items = query.order_by(SectionBureauMember.display_order.asc()).all()
    return [_out(m) for m in items]


@router.get("/{member_id}", response_model=SectionBureauMemberOut)
def get_section_bureau_member(
    member_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)
):
    m = _base_query(db).filter(SectionBureauMember.id == member_id).first()
    if m is None or not _can_view(current, m):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membre introuvable.")
    return _out(m)


@router.post("", response_model=SectionBureauMemberOut, status_code=status.HTTP_201_CREATED)
def create_section_bureau_member(
    payload: SectionBureauMemberCreate,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    if current.is_admin:
        section_id = payload.section_id
        if section_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Veuillez préciser la section pour ce membre de bureau.",
            )
    else:
        section_id = current.section_id
        if section_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Ce compte n'est rattaché à aucune section."
            )

    m = SectionBureauMember(
        section_id=section_id,
        full_name=payload.full_name,
        role_title=payload.role_title,
        display_order=payload.display_order,
        author_id=current.id,
        status=DocumentStatus.EN_ATTENTE,
    )
    db.add(m)
    db.commit()
    db.refresh(m)

    notify_all_admins(
        db, type=NotificationType.SECTION_BUREAU_SUBMITTED,
        message=f"Nouveau membre proposé pour le bureau de section : « {m.full_name} ».",
        resource_type="section_bureau_member", resource_id=m.id,
    )
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="SECTION_BUREAU_MEMBER_CREATED",
        resource_type="section_bureau_member", resource_id=str(m.id), resource_label=m.full_name,
        ip_address=get_client_ip(request),
    )
    m = _base_query(db).filter(SectionBureauMember.id == m.id).first()
    return _out(m)


@router.put("/{member_id}", response_model=SectionBureauMemberOut)
def update_section_bureau_member(
    member_id: uuid.UUID,
    payload: SectionBureauMemberUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    m = db.get(SectionBureauMember, member_id)
    if m is None or not _can_manage(current, m):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membre introuvable.")
    if not current.is_admin and m.status == DocumentStatus.PUBLIE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un membre déjà publié ne peut être modifié que par un administrateur.",
        )

    for field in ("full_name", "role_title", "display_order"):
        value = getattr(payload, field)
        if value is not None:
            setattr(m, field, value)

    # Une correction après refus repasse automatiquement en attente de validation.
    if not current.is_admin and m.status == DocumentStatus.REFUSE:
        m.status = DocumentStatus.EN_ATTENTE
        m.rejection_reason = None

    db.commit()
    db.refresh(m)
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="SECTION_BUREAU_MEMBER_UPDATED",
        resource_type="section_bureau_member", resource_id=str(m.id), resource_label=m.full_name,
        ip_address=get_client_ip(request),
    )
    m = _base_query(db).filter(SectionBureauMember.id == m.id).first()
    return _out(m)


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_section_bureau_member(
    member_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    m = db.get(SectionBureauMember, member_id)
    if m is None or not _can_manage(current, m):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membre introuvable.")
    if not current.is_admin and m.status == DocumentStatus.PUBLIE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un membre publié ne peut être supprimé que par un administrateur.",
        )

    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="SECTION_BUREAU_MEMBER_DELETED",
        resource_type="section_bureau_member", resource_id=str(m.id), resource_label=m.full_name,
        ip_address=get_client_ip(request),
    )
    old_filename = m.photo_filename
    db.delete(m)
    db.commit()

    if old_filename:
        try:
            get_storage_backend().delete(old_filename)
        except Exception:
            pass


@router.post("/{member_id}/approve", response_model=SectionBureauMemberOut)
def approve_section_bureau_member(
    member_id: uuid.UUID, request: Request, db: Session = Depends(get_db), current: CurrentUser = Depends(require_admin)
):
    m = db.get(SectionBureauMember, member_id)
    if m is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membre introuvable.")
    if m.status != DocumentStatus.EN_ATTENTE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Seul un membre en attente peut être publié.")

    m.status = DocumentStatus.PUBLIE
    m.rejection_reason = None
    db.commit()
    db.refresh(m)

    notify(
        db, user_id=m.author_id, type=NotificationType.SECTION_BUREAU_PUBLISHED,
        message=f"« {m.full_name} » a été publié(e) au bureau de votre section.",
        resource_type="section_bureau_member", resource_id=m.id,
    )
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="SECTION_BUREAU_MEMBER_APPROVED",
        resource_type="section_bureau_member", resource_id=str(m.id), resource_label=m.full_name,
        ip_address=get_client_ip(request),
    )
    m = _base_query(db).filter(SectionBureauMember.id == m.id).first()
    return _out(m)


@router.post("/{member_id}/reject", response_model=SectionBureauMemberOut)
def reject_section_bureau_member(
    member_id: uuid.UUID,
    payload: SectionBureauMemberRejectRequest,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    m = db.get(SectionBureauMember, member_id)
    if m is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membre introuvable.")
    if m.status != DocumentStatus.EN_ATTENTE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Seul un membre en attente peut être refusé.")

    m.status = DocumentStatus.REFUSE
    m.rejection_reason = payload.reason
    db.commit()
    db.refresh(m)

    notify(
        db, user_id=m.author_id, type=NotificationType.SECTION_BUREAU_REJECTED,
        message=f"« {m.full_name} » a été refusé(e) pour le bureau de votre section : {payload.reason}",
        resource_type="section_bureau_member", resource_id=m.id,
    )
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="SECTION_BUREAU_MEMBER_REJECTED",
        resource_type="section_bureau_member", resource_id=str(m.id), resource_label=m.full_name,
        ip_address=get_client_ip(request),
    )
    m = _base_query(db).filter(SectionBureauMember.id == m.id).first()
    return _out(m)


@router.post("/{member_id}/photo", response_model=SectionBureauMemberOut)
async def upload_section_bureau_photo(
    member_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    m = db.get(SectionBureauMember, member_id)
    if m is None or not _can_manage(current, m):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membre introuvable.")
    if not current.is_admin and m.status == DocumentStatus.PUBLIE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La photo d'un membre déjà publié ne peut être changée que par un administrateur.",
        )

    header = await file.read(HEADER_SNIFF_BYTES)
    await file.seek(0)
    try:
        validated = validate_upload(
            original_filename=file.filename or "",
            header_bytes=header,
            declared_size=None,
            max_size_bytes=settings.max_upload_size_bytes,
        )
    except FileValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if validated.extension not in IMAGE_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La photo doit être une image (JPG, JPEG, PNG, WEBP).")

    storage = get_storage_backend()
    old_filename = m.photo_filename
    _save_with_size_limit(storage, file, validated.stored_filename, settings.max_upload_size_bytes)
    m.photo_filename = validated.stored_filename
    db.add(m)
    db.commit()
    db.refresh(m)

    if old_filename:
        try:
            storage.delete(old_filename)
        except Exception:
            pass

    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="SECTION_BUREAU_MEMBER_PHOTO_UPLOADED",
        resource_type="section_bureau_member", resource_id=str(m.id), resource_label=m.full_name,
        ip_address=get_client_ip(request),
    )
    m = _base_query(db).filter(SectionBureauMember.id == m.id).first()
    return _out(m)


@router.delete("/{member_id}/photo", response_model=SectionBureauMemberOut)
def remove_section_bureau_photo(
    member_id: uuid.UUID, request: Request, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)
):
    m = db.get(SectionBureauMember, member_id)
    if m is None or not _can_manage(current, m):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membre introuvable.")

    old_filename = m.photo_filename
    m.photo_filename = None
    db.add(m)
    db.commit()
    db.refresh(m)

    if old_filename:
        try:
            get_storage_backend().delete(old_filename)
        except Exception:
            pass

    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="SECTION_BUREAU_MEMBER_PHOTO_REMOVED",
        resource_type="section_bureau_member", resource_id=str(m.id), resource_label=m.full_name,
        ip_address=get_client_ip(request),
    )
    m = _base_query(db).filter(SectionBureauMember.id == m.id).first()
    return _out(m)


@router.get("/{member_id}/photo")
def get_section_bureau_photo(
    member_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)
):
    m = db.get(SectionBureauMember, member_id)
    if m is None or not _can_view(current, m) or not m.photo_filename:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo introuvable.")

    storage = get_storage_backend()
    try:
        stream = storage.open(m.photo_filename)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable sur le serveur.")

    extension = m.photo_filename.rsplit(".", 1)[-1].lower()
    return StreamingResponse(stream, media_type=PHOTO_MIME.get(extension, "application/octet-stream"))
