"""
Galerie photo (étape 12). Mêmes règles que les documents : upload réel avec
vérification de signature binaire, workflow EN_ATTENTE -> PUBLIE | REFUSE, et
cloisonnement strict par section appliqué côté serveur.
"""
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.api.deps import CurrentUser, get_client_ip, get_current_user, require_admin
from app.api.v1.documents import HEADER_SNIFF_BYTES, _save_with_size_limit
from app.core.config import settings
from app.core.database import get_db
from app.models.document import DocumentStatus
from app.models.gallery import GalleryPhoto
from app.models.notification import NotificationType
from app.models.programme import ProgrammeActivite
from app.models.section import Section
from app.models.user import User
from app.schemas.gallery import (
    GalleryPhotoOut,
    GalleryPhotoRejectRequest,
    GalleryPhotoUpdate,
    PaginatedGalleryPhotos,
)
from app.services.audit_service import log_action
from app.services.file_validation import IMAGE_EXTENSIONS, FileValidationError, validate_upload
from app.services.notification_service import notify, notify_all_admins
from app.storage.factory import get_storage_backend

router = APIRouter(prefix="/gallery", tags=["gallery"])


def _actor_label(db: Session, current: CurrentUser) -> str:
    user = db.get(User, current.id)
    return user.username if user else str(current.id)


def _base_query(db: Session):
    return db.query(GalleryPhoto).options(joinedload(GalleryPhoto.section), joinedload(GalleryPhoto.author))


def _out(p: GalleryPhoto) -> GalleryPhotoOut:
    return GalleryPhotoOut(
        id=p.id,
        caption=p.caption,
        original_filename=p.original_filename,
        section_id=p.section_id,
        section_name=getattr(p.section, "name", None) if getattr(p, "section", None) else None,
        programme_id=p.programme_id,
        author_id=p.author_id,
        author_name=getattr(p.author, "full_name", None) if getattr(p, "author", None) else None,
        status=p.status,
        rejection_reason=p.rejection_reason,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _can_view(current: CurrentUser, p: GalleryPhoto) -> bool:
    if current.is_admin:
        return True
    if p.status == DocumentStatus.PUBLIE:
        return True
    return p.section_id is not None and p.section_id == current.section_id


def _can_manage(current: CurrentUser, p: GalleryPhoto) -> bool:
    if current.is_admin:
        return True
    return p.section_id is not None and p.section_id == current.section_id and p.author_id == current.id


@router.get("", response_model=PaginatedGalleryPhotos)
def list_gallery(
    status_filter: DocumentStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    query = _base_query(db)
    if not current.is_admin:
        query = query.filter(
            (GalleryPhoto.status == DocumentStatus.PUBLIE) | (GalleryPhoto.section_id == current.section_id)
        )
    if status_filter is not None:
        query = query.filter(GalleryPhoto.status == status_filter)

    total = query.count()
    items = query.order_by(GalleryPhoto.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedGalleryPhotos(items=[_out(p) for p in items], total=total, page=page, page_size=page_size)


@router.get("/{photo_id}", response_model=GalleryPhotoOut)
def get_photo(photo_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    p = _base_query(db).filter(GalleryPhoto.id == photo_id).first()
    if p is None or not _can_view(current, p):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo introuvable.")
    return _out(p)


@router.post("", response_model=GalleryPhotoOut, status_code=status.HTTP_201_CREATED)
async def upload_photo(
    request: Request,
    caption: str | None = Form(default=None),
    section_id: uuid.UUID | None = Form(default=None),
    programme_id: uuid.UUID | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    if current.is_admin:
        target_section_id = section_id
        if target_section_id is not None and db.get(Section, target_section_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section introuvable.")
    else:
        # Jamais confiance dans le section_id envoyé par le client.
        target_section_id = current.section_id

    if programme_id is not None and db.get(ProgrammeActivite, programme_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activité de programme introuvable.")

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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La galerie n'accepte que des images (JPG, JPEG, PNG, WEBP).",
        )

    storage = get_storage_backend()
    size_bytes = _save_with_size_limit(storage, file, validated.stored_filename, settings.max_upload_size_bytes)

    photo = GalleryPhoto(
        stored_filename=validated.stored_filename,
        original_filename=(file.filename or "photo.jpg")[:255],
        caption=caption,
        section_id=target_section_id,
        programme_id=programme_id,
        author_id=current.id,
        status=DocumentStatus.EN_ATTENTE,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    _ = size_bytes  # conservé pour cohérence avec le flux d'upload documents ; non stocké (pas de colonne dédiée)

    notify_all_admins(
        db, type=NotificationType.PHOTO_SUBMITTED,
        message="Une nouvelle photo a été soumise pour la galerie.", resource_type="gallery_photo", resource_id=photo.id,
    )
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="PHOTO_UPLOADED",
        resource_type="gallery_photo", resource_id=str(photo.id), resource_label=photo.original_filename,
        ip_address=get_client_ip(request),
    )
    photo = _base_query(db).filter(GalleryPhoto.id == photo.id).first()
    return _out(photo)


@router.put("/{photo_id}", response_model=GalleryPhotoOut)
def update_photo(
    photo_id: uuid.UUID,
    payload: GalleryPhotoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    p = db.get(GalleryPhoto, photo_id)
    if p is None or not _can_manage(current, p):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo introuvable.")
    if not current.is_admin and p.status == DocumentStatus.PUBLIE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cette photo est déjà publiée : contactez un administrateur pour la modifier.",
        )

    if payload.caption is not None:
        p.caption = payload.caption

    if not current.is_admin and p.status == DocumentStatus.REFUSE:
        p.status = DocumentStatus.EN_ATTENTE
        p.rejection_reason = None

    db.commit()
    db.refresh(p)
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="PHOTO_UPDATED",
        resource_type="gallery_photo", resource_id=str(p.id), resource_label=p.original_filename,
        ip_address=get_client_ip(request),
    )
    p = _base_query(db).filter(GalleryPhoto.id == p.id).first()
    return _out(p)


@router.delete("/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(
    photo_id: uuid.UUID, request: Request, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)
):
    p = db.get(GalleryPhoto, photo_id)
    if p is None or not _can_manage(current, p):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo introuvable.")
    if not current.is_admin and p.status == DocumentStatus.PUBLIE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une photo publiée ne peut être supprimée que par un administrateur.",
        )

    stored_filename = p.stored_filename
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="PHOTO_DELETED",
        resource_type="gallery_photo", resource_id=str(p.id), resource_label=p.original_filename,
        ip_address=get_client_ip(request),
    )
    db.delete(p)
    db.commit()

    try:
        get_storage_backend().delete(stored_filename)
    except Exception:
        pass  # la métadonnée est déjà supprimée ; un fichier orphelin sur disque n'est pas bloquant


@router.post("/{photo_id}/approve", response_model=GalleryPhotoOut)
def approve_photo(
    photo_id: uuid.UUID, request: Request, db: Session = Depends(get_db), current: CurrentUser = Depends(require_admin)
):
    p = db.get(GalleryPhoto, photo_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo introuvable.")
    if p.status != DocumentStatus.EN_ATTENTE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Seule une photo en attente peut être publiée.")

    p.status = DocumentStatus.PUBLIE
    p.rejection_reason = None
    db.commit()
    db.refresh(p)

    notify(
        db, user_id=p.author_id, type=NotificationType.PHOTO_APPROVED,
        message="Votre photo a été publiée dans la galerie.", resource_type="gallery_photo", resource_id=p.id,
    )
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="PHOTO_APPROVED",
        resource_type="gallery_photo", resource_id=str(p.id), resource_label=p.original_filename,
        ip_address=get_client_ip(request),
    )
    p = _base_query(db).filter(GalleryPhoto.id == p.id).first()
    return _out(p)


@router.post("/{photo_id}/reject", response_model=GalleryPhotoOut)
def reject_photo(
    photo_id: uuid.UUID,
    payload: GalleryPhotoRejectRequest,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    p = db.get(GalleryPhoto, photo_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo introuvable.")
    if p.status != DocumentStatus.EN_ATTENTE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Seule une photo en attente peut être refusée.")

    p.status = DocumentStatus.REFUSE
    p.rejection_reason = payload.reason
    db.commit()
    db.refresh(p)

    notify(
        db, user_id=p.author_id, type=NotificationType.PHOTO_REJECTED,
        message=f"Votre photo a été refusée : {payload.reason}", resource_type="gallery_photo", resource_id=p.id,
    )
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="PHOTO_REJECTED",
        resource_type="gallery_photo", resource_id=str(p.id), resource_label=p.original_filename,
        ip_address=get_client_ip(request),
    )
    p = _base_query(db).filter(GalleryPhoto.id == p.id).first()
    return _out(p)


@router.get("/{photo_id}/file")
def download_photo(
    photo_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)
):
    p = db.get(GalleryPhoto, photo_id)
    if p is None or not _can_view(current, p):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo introuvable.")

    storage = get_storage_backend()
    try:
        stream = storage.open(p.stored_filename)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable sur le serveur.")

    extension = p.stored_filename.rsplit(".", 1)[-1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(
        extension, "application/octet-stream"
    )
    return StreamingResponse(
        stream,
        media_type=mime,
        headers={"Content-Disposition": f'inline; filename="{p.original_filename}"'},
    )
