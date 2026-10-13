"""
Bureau du Vicariat (contenu unique, pas de notion de section) : lecture par
tout utilisateur connecté, écriture réservée à l'administrateur. L'accès
public (site vitrine, sans connexion) est exposé séparément (étape 14).
"""
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_client_ip, get_current_user, require_admin
from app.api.v1.documents import HEADER_SNIFF_BYTES, _save_with_size_limit
from app.core.config import settings
from app.core.database import get_db
from app.models.bureau import BureauMember
from app.models.user import User
from app.schemas.bureau import BureauMemberCreate, BureauMemberOut, BureauMemberUpdate
from app.services.audit_service import log_action
from app.services.file_validation import IMAGE_EXTENSIONS, FileValidationError, validate_upload
from app.storage.factory import get_storage_backend

router = APIRouter(prefix="/bureau", tags=["bureau"])

PHOTO_MIME = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def _actor_label(db: Session, current: CurrentUser) -> str:
    user = db.get(User, current.id)
    return user.username if user else str(current.id)


@router.get("", response_model=list[BureauMemberOut])
def list_bureau(db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    return (
        db.query(BureauMember)
        .filter(BureauMember.is_active.is_(True))
        .order_by(BureauMember.display_order.asc())
        .all()
    )


@router.post("", response_model=BureauMemberOut, status_code=status.HTTP_201_CREATED)
def create_bureau_member(
    payload: BureauMemberCreate, request: Request, db: Session = Depends(get_db), current: CurrentUser = Depends(require_admin)
):
    member = BureauMember(**payload.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="BUREAU_MEMBER_CREATED",
        resource_type="bureau_member", resource_id=str(member.id), resource_label=member.full_name,
        ip_address=get_client_ip(request),
    )
    return member


@router.put("/{member_id}", response_model=BureauMemberOut)
def update_bureau_member(
    member_id: uuid.UUID,
    payload: BureauMemberUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    member = db.get(BureauMember, member_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membre du bureau introuvable.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(member, field, value)

    db.commit()
    db.refresh(member)
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="BUREAU_MEMBER_UPDATED",
        resource_type="bureau_member", resource_id=str(member.id), resource_label=member.full_name,
        ip_address=get_client_ip(request),
    )
    return member


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bureau_member(
    member_id: uuid.UUID, request: Request, db: Session = Depends(get_db), current: CurrentUser = Depends(require_admin)
):
    member = db.get(BureauMember, member_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membre du bureau introuvable.")

    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="BUREAU_MEMBER_DELETED",
        resource_type="bureau_member", resource_id=str(member.id), resource_label=member.full_name,
        ip_address=get_client_ip(request),
    )
    db.delete(member)
    db.commit()

    if member.photo_filename:
        try:
            get_storage_backend().delete(member.photo_filename)
        except Exception:
            pass


@router.post("/{member_id}/photo", response_model=BureauMemberOut)
async def upload_bureau_photo(
    member_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    member = db.get(BureauMember, member_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membre du bureau introuvable.")

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
    old_filename = member.photo_filename
    _save_with_size_limit(storage, file, validated.stored_filename, settings.max_upload_size_bytes)
    member.photo_filename = validated.stored_filename
    db.add(member)
    db.commit()
    db.refresh(member)

    if old_filename:
        try:
            storage.delete(old_filename)
        except Exception:
            pass

    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="BUREAU_MEMBER_PHOTO_UPLOADED",
        resource_type="bureau_member", resource_id=str(member.id), resource_label=member.full_name,
        ip_address=get_client_ip(request),
    )
    return member


@router.delete("/{member_id}/photo", response_model=BureauMemberOut)
def remove_bureau_photo(
    member_id: uuid.UUID, request: Request, db: Session = Depends(get_db), current: CurrentUser = Depends(require_admin)
):
    member = db.get(BureauMember, member_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membre du bureau introuvable.")

    old_filename = member.photo_filename
    member.photo_filename = None
    db.add(member)
    db.commit()
    db.refresh(member)

    if old_filename:
        try:
            get_storage_backend().delete(old_filename)
        except Exception:
            pass

    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="BUREAU_MEMBER_PHOTO_REMOVED",
        resource_type="bureau_member", resource_id=str(member.id), resource_label=member.full_name,
        ip_address=get_client_ip(request),
    )
    return member


@router.get("/{member_id}/photo")
def get_bureau_photo(member_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    """
    Aperçu authentifié pour l'espace d'administration — voir aussi
    GET /public/bureau/{member_id}/photo (sans authentification, pour le site
    public). Une photo de membre du bureau n'a pas de statut de validation :
    elle est publique dès qu'elle est déposée par un administrateur.
    """
    member = db.get(BureauMember, member_id)
    if member is None or not member.photo_filename:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo introuvable.")

    storage = get_storage_backend()
    try:
        stream = storage.open(member.photo_filename)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable sur le serveur.")

    extension = member.photo_filename.rsplit(".", 1)[-1].lower()
    return StreamingResponse(stream, media_type=PHOTO_MIME.get(extension, "application/octet-stream"))
