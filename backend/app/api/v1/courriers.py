"""
Courriers entre une section et le Bureau du Vicariat : messages libres ou
demandes de fichiers (ex. attestations de camp), traités par l'administrateur
sous forme de file d'attente — voir app/models/courrier.py pour le détail du
workflow et des statuts.

Règles serveur (même esprit que section_bureau.py / documents.py) :
- Une section ne peut créer/consulter/supprimer que SES PROPRES courriers
  (section_id toujours dérivé du compte connecté pour un compte SECTION).
- Seul un administrateur peut "traiter" un courrier (note + fichier de
  réponse optionnels) — jamais la section elle-même.
- Une section ne peut supprimer un courrier que tant qu'il est NOUVEAU
  (retirer une demande envoyée par erreur avant qu'elle ne soit traitée).
"""
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.api.deps import CurrentUser, get_client_ip, get_current_user, require_admin
from app.api.v1.documents import HEADER_SNIFF_BYTES, _save_with_size_limit
from app.core.config import settings
from app.core.database import get_db
from app.models.courrier import Courrier, CourrierKind, CourrierStatus
from app.models.notification import NotificationType
from app.models.section import Section
from app.models.user import User
from app.schemas.courrier import CourrierOut, CourrierRespondRequest
from app.services.audit_service import log_action
from app.services.file_validation import FileValidationError, validate_upload
from app.services.notification_service import notify, notify_all_admins
from app.storage.factory import get_storage_backend

router = APIRouter(prefix="/courriers", tags=["courriers"])


def _actor_label(db: Session, current: CurrentUser) -> str:
    user = db.get(User, current.id)
    return user.username if user else str(current.id)


def _base_query(db: Session):
    return db.query(Courrier).options(
        joinedload(Courrier.section), joinedload(Courrier.author), joinedload(Courrier.handled_by)
    )


def _out(c: Courrier) -> CourrierOut:
    return CourrierOut(
        id=c.id,
        section_id=c.section_id,
        section_name=getattr(c.section, "name", None) if getattr(c, "section", None) else None,
        kind=c.kind,
        subject=c.subject,
        body=c.body,
        has_attachment=c.has_attachment,
        attachment_original_filename=c.attachment_original_filename,
        status=c.status,
        response_note=c.response_note,
        has_response_file=c.has_response_file,
        response_original_filename=c.response_original_filename,
        handled_at=c.handled_at,
        handled_by_id=c.handled_by_id,
        handled_by_name=getattr(c.handled_by, "full_name", None) if getattr(c, "handled_by", None) else None,
        author_id=c.author_id,
        author_name=getattr(c.author, "full_name", None) if getattr(c, "author", None) else None,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _can_view(current: CurrentUser, c: Courrier) -> bool:
    if current.is_admin:
        return True
    return c.section_id == current.section_id


def _can_manage(current: CurrentUser, c: Courrier) -> bool:
    # Gérer (supprimer) : uniquement la section propriétaire, jamais une
    # autre section — un administrateur gère via /respond, pas via delete.
    return not current.is_admin and c.section_id == current.section_id


@router.get("", response_model=list[CourrierOut])
def list_courriers(
    section_id: uuid.UUID | None = None,
    status_filter: CourrierStatus | None = None,
    kind: CourrierKind | None = None,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    query = _base_query(db)
    if current.is_admin:
        if section_id is not None:
            query = query.filter(Courrier.section_id == section_id)
    else:
        # Isolation stricte côté serveur : une section ne voit jamais les
        # courriers d'une autre section, quel que soit le paramètre envoyé.
        query = query.filter(Courrier.section_id == current.section_id)

    if status_filter is not None:
        query = query.filter(Courrier.status == status_filter)
    if kind is not None:
        query = query.filter(Courrier.kind == kind)

    items = query.order_by(Courrier.created_at.desc()).all()
    return [_out(c) for c in items]


@router.get("/{courrier_id}", response_model=CourrierOut)
def get_courrier(courrier_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    c = _base_query(db).filter(Courrier.id == courrier_id).first()
    if c is None or not _can_view(current, c):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courrier introuvable.")
    return _out(c)


@router.post("", response_model=CourrierOut, status_code=status.HTTP_201_CREATED)
async def create_courrier(
    request: Request,
    kind: CourrierKind = Form(...),
    subject: str = Form(..., min_length=1, max_length=255),
    body: str = Form(..., min_length=1),
    section_id: uuid.UUID | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    if current.is_admin:
        target_section_id = section_id
        if target_section_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Veuillez préciser la section concernée par ce courrier."
            )
        if db.get(Section, target_section_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section introuvable.")
    else:
        # Une section ne peut jamais envoyer un courrier au nom d'une autre
        # section, même en trafiquant le champ section_id du formulaire.
        target_section_id = current.section_id
        if target_section_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Ce compte n'est rattaché à aucune section."
            )

    attachment_filename = None
    attachment_original_filename = None
    if file is not None and file.filename:
        header = await file.read(HEADER_SNIFF_BYTES)
        await file.seek(0)
        try:
            validated = validate_upload(
                original_filename=file.filename,
                header_bytes=header,
                declared_size=None,
                max_size_bytes=settings.max_upload_size_bytes,
            )
        except FileValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

        storage = get_storage_backend()
        _save_with_size_limit(storage, file, validated.stored_filename, settings.max_upload_size_bytes)
        attachment_filename = validated.stored_filename
        attachment_original_filename = file.filename[:255]

    c = Courrier(
        section_id=target_section_id,
        author_id=current.id,
        kind=kind,
        subject=subject,
        body=body,
        attachment_filename=attachment_filename,
        attachment_original_filename=attachment_original_filename,
        status=CourrierStatus.NOUVEAU,
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    notify_all_admins(
        db,
        type=NotificationType.COURRIER_SUBMITTED,
        message=f"Nouveau courrier reçu de la section « {c.section.name if c.section else ''} » : « {c.subject} ».",
        resource_type="courrier",
        resource_id=c.id,
    )
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="COURRIER_CREATED",
        resource_type="courrier", resource_id=str(c.id), resource_label=c.subject,
        ip_address=get_client_ip(request),
    )
    c = _base_query(db).filter(Courrier.id == c.id).first()
    return _out(c)


@router.delete("/{courrier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_courrier(
    courrier_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    c = db.get(Courrier, courrier_id)
    if c is None or not _can_view(current, c):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courrier introuvable.")
    if not _can_manage(current, c):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez pas supprimer ce courrier.")
    if c.status != CourrierStatus.NOUVEAU:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Un courrier déjà traité ne peut plus être retiré."
        )

    label = c.subject
    attachment_filename = c.attachment_filename
    db.delete(c)
    db.commit()

    if attachment_filename:
        try:
            get_storage_backend().delete(attachment_filename)
        except Exception:
            pass

    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="COURRIER_DELETED",
        resource_type="courrier", resource_id=str(courrier_id), resource_label=label,
        ip_address=get_client_ip(request),
    )
    return None


@router.post("/{courrier_id}/respond", response_model=CourrierOut)
async def respond_courrier(
    courrier_id: uuid.UUID,
    request: Request,
    response_note: str | None = Form(default=None, max_length=2000),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    c = db.get(Courrier, courrier_id)
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courrier introuvable.")

    if file is not None and file.filename:
        header = await file.read(HEADER_SNIFF_BYTES)
        await file.seek(0)
        try:
            validated = validate_upload(
                original_filename=file.filename,
                header_bytes=header,
                declared_size=None,
                max_size_bytes=settings.max_upload_size_bytes,
            )
        except FileValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

        storage = get_storage_backend()
        old_response_filename = c.response_filename
        _save_with_size_limit(storage, file, validated.stored_filename, settings.max_upload_size_bytes)
        c.response_filename = validated.stored_filename
        c.response_original_filename = file.filename[:255]
        if old_response_filename:
            try:
                storage.delete(old_response_filename)
            except Exception:
                pass

    from datetime import datetime, timezone

    c.response_note = response_note
    c.status = CourrierStatus.TRAITE
    c.handled_at = datetime.now(timezone.utc)
    c.handled_by_id = current.id
    db.add(c)
    db.commit()
    db.refresh(c)

    notify(
        db, user_id=c.author_id, type=NotificationType.COURRIER_TRAITE,
        message=f"Votre courrier « {c.subject} » a été traité par le Bureau du Vicariat.",
        resource_type="courrier", resource_id=c.id,
    )
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="COURRIER_TRAITE",
        resource_type="courrier", resource_id=str(c.id), resource_label=c.subject,
        ip_address=get_client_ip(request),
    )
    c = _base_query(db).filter(Courrier.id == c.id).first()
    return _out(c)


@router.get("/{courrier_id}/attachment")
def download_courrier_attachment(
    courrier_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)
):
    c = db.get(Courrier, courrier_id)
    if c is None or not _can_view(current, c) or not c.attachment_filename:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pièce jointe introuvable.")

    storage = get_storage_backend()
    try:
        stream = storage.open(c.attachment_filename)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable sur le serveur.")

    return StreamingResponse(
        stream,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{c.attachment_original_filename or "fichier"}"'},
    )


@router.get("/{courrier_id}/response-file")
def download_courrier_response_file(
    courrier_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)
):
    c = db.get(Courrier, courrier_id)
    if c is None or not _can_view(current, c) or not c.response_filename:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier de réponse introuvable.")

    storage = get_storage_backend()
    try:
        stream = storage.open(c.response_filename)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable sur le serveur.")

    return StreamingResponse(
        stream,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{c.response_original_filename or "fichier"}"'},
    )
