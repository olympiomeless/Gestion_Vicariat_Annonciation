import secrets
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_current_user, require_admin, CurrentUser
from app.api.v1.documents import HEADER_SNIFF_BYTES, _save_with_size_limit
from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_password
from app.models.section import Section
from app.models.user import Role, User
from app.schemas.section import SectionCreate, SectionCreateOut, SectionOut, SectionUpdate
from app.services.audit_service import log_action
from app.services.file_validation import IMAGE_EXTENSIONS, FileValidationError, validate_upload
from app.services.notification_service import notify
from app.models.notification import NotificationType
from app.storage.factory import get_storage_backend

router = APIRouter(prefix="/sections", tags=["sections"])

PHOTO_MIME = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


@router.get("", response_model=list[SectionOut])
def list_sections(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    query = db.query(Section)
    if not include_inactive:
        query = query.filter(Section.is_active.is_(True))
    return query.order_by(Section.display_order, Section.name).all()


@router.get("/{section_id}", response_model=SectionOut)
def get_section(section_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    section = db.get(Section, section_id)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section introuvable.")
    return section


@router.post("", response_model=SectionCreateOut, status_code=status.HTTP_201_CREATED)
def create_section(
    payload: SectionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    if db.query(Section).filter(Section.slug == payload.slug).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Une section avec cet identifiant existe déjà.")

    username = payload.username.lower().strip() if payload.username else None
    if username and db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un compte existe déjà avec cet identifiant.")

    section = Section(**payload.model_dump(exclude={"username"}))
    db.add(section)
    db.flush()  # attribue section.id, sans valider encore la transaction

    generated_password = None
    if username:
        role = db.query(Role).filter(Role.name == Role.SECTION).first()
        if role is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Rôle SECTION introuvable.")
        generated_password = secrets.token_urlsafe(9)
        account = User(
            username=username,
            full_name=section.name,
            password_hash=hash_password(generated_password),
            role_id=role.id,
            section_id=section.id,
            is_active=True,
        )
        db.add(account)

    db.commit()
    db.refresh(section)

    log_action(
        db,
        user_id=current.id,
        user_label=str(current.id),
        action="SECTION_CREATED",
        resource_type="section",
        resource_id=str(section.id),
        resource_label=section.name,
        ip_address=get_client_ip(request),
    )

    if username:
        account = db.query(User).filter(User.username == username).first()
        if account is not None:
            notify(
                db,
                user_id=account.id,
                type=NotificationType.NEW_ACCOUNT,
                message=f"Un compte SECTION vient d'être créé pour vous par le Bureau du Vicariat.",
            )
        log_action(
            db,
            user_id=current.id,
            user_label=str(current.id),
            action="USER_CREATED",
            resource_type="user",
            resource_id=str(account.id) if account else "",
            resource_label=username,
            ip_address=get_client_ip(request),
        )

    out = SectionCreateOut.model_validate(section)
    out.generated_username = username
    out.generated_password = generated_password
    return out


@router.put("/{section_id}", response_model=SectionOut)
def update_section(
    section_id: uuid.UUID,
    payload: SectionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    section = db.get(Section, section_id)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section introuvable.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(section, field, value)
    db.add(section)
    db.commit()
    db.refresh(section)

    log_action(
        db,
        user_id=current.id,
        user_label=str(current.id),
        action="SECTION_UPDATED",
        resource_type="section",
        resource_id=str(section.id),
        resource_label=section.name,
        ip_address=get_client_ip(request),
    )
    return section


@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_section(
    section_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    section = db.get(Section, section_id)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section introuvable.")

    from app.models.user import User

    if db.query(User).filter(User.section_id == section_id).count() > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible de supprimer une section à laquelle des utilisateurs sont encore rattachés. Désactivez-la plutôt, ou réassignez ces utilisateurs.",
        )

    label = section.name
    old_filename = section.photo_filename
    db.delete(section)
    db.commit()

    log_action(
        db,
        user_id=current.id,
        user_label=str(current.id),
        action="SECTION_DELETED",
        resource_type="section",
        resource_id=str(section_id),
        resource_label=label,
        ip_address=get_client_ip(request),
    )
    if old_filename:
        try:
            get_storage_backend().delete(old_filename)
        except Exception:
            pass
    return None


@router.post("/{section_id}/photo", response_model=SectionOut)
async def upload_section_photo(
    section_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    section = db.get(Section, section_id)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section introuvable.")

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
    old_filename = section.photo_filename
    _save_with_size_limit(storage, file, validated.stored_filename, settings.max_upload_size_bytes)
    section.photo_filename = validated.stored_filename
    db.add(section)
    db.commit()
    db.refresh(section)

    if old_filename:
        try:
            storage.delete(old_filename)
        except Exception:
            pass

    log_action(
        db, user_id=current.id, user_label=str(current.id), action="SECTION_PHOTO_UPLOADED",
        resource_type="section", resource_id=str(section.id), resource_label=section.name,
        ip_address=get_client_ip(request),
    )
    return section


@router.delete("/{section_id}/photo", response_model=SectionOut)
def remove_section_photo(
    section_id: uuid.UUID, request: Request, db: Session = Depends(get_db), current: CurrentUser = Depends(require_admin)
):
    section = db.get(Section, section_id)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section introuvable.")

    old_filename = section.photo_filename
    section.photo_filename = None
    db.add(section)
    db.commit()
    db.refresh(section)

    if old_filename:
        try:
            get_storage_backend().delete(old_filename)
        except Exception:
            pass

    log_action(
        db, user_id=current.id, user_label=str(current.id), action="SECTION_PHOTO_REMOVED",
        resource_type="section", resource_id=str(section.id), resource_label=section.name,
        ip_address=get_client_ip(request),
    )
    return section


@router.get("/{section_id}/photo")
def get_section_photo(section_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    """
    Aperçu authentifié pour l'espace d'administration — voir aussi
    GET /public/sections/{section_id}/photo (sans authentification, pour le
    site public). Comme pour le bureau, une photo de section n'a pas de statut
    de validation : elle est publique dès qu'elle est déposée par un administrateur.
    """
    section = db.get(Section, section_id)
    if section is None or not section.photo_filename:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo introuvable.")

    storage = get_storage_backend()
    try:
        stream = storage.open(section.photo_filename)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable sur le serveur.")

    extension = section.photo_filename.rsplit(".", 1)[-1].lower()
    return StreamingResponse(stream, media_type=PHOTO_MIME.get(extension, "application/octet-stream"))
