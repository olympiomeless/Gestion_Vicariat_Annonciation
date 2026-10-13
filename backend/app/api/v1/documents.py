import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.api.deps import CurrentUser, get_client_ip, get_current_user, require_admin
from app.core.config import settings
from app.core.database import get_db
from app.models.document import Document, DocumentCategory, DocumentStatus
from app.models.notification import NotificationType
from app.models.section import Section
from app.models.user import Role, User
from app.schemas.document import (
    DocumentCategoryCreate,
    DocumentCategoryOut,
    DocumentOut,
    DocumentRejectRequest,
    DocumentUpdate,
    PaginatedDocuments,
)
from app.services.audit_service import log_action
from app.services.file_validation import FileValidationError, validate_upload
from app.services.notification_service import notify, notify_all_admins
from app.storage.factory import get_storage_backend

router = APIRouter(prefix="/documents", tags=["documents"])

HEADER_SNIFF_BYTES = 64


def _actor_label(db: Session, current: CurrentUser) -> str:
    user = db.get(User, current.id)
    return user.username if user else str(current.id)


def _document_out(doc: Document) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        name=doc.name,
        description=doc.description,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        size_bytes=doc.size_bytes,
        category_id=doc.category_id,
        category_name=doc.category.name if doc.category else None,
        section_id=doc.section_id,
        section_name=doc.section.name if getattr(doc, "section", None) else None,
        author_id=doc.author_id,
        author_name=doc.author.full_name if getattr(doc, "author", None) else None,
        status=doc.status,
        rejection_reason=doc.rejection_reason,
        reviewed_at=doc.reviewed_at,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def _base_query(db: Session):
    return (
        db.query(Document)
        .options(joinedload(Document.category), joinedload(Document.author), joinedload(Document.section))
    )


def _can_view_document(current: CurrentUser, doc: Document) -> bool:
    if current.is_admin:
        return True
    if doc.section_id is not None and doc.section_id == current.section_id:
        return True
    # Un document "Vicariat" (section_id NULL) publié est visible par tous
    # les comptes connectés ; un document d'une AUTRE section n'est visible
    # que s'il est publié.
    if doc.status == DocumentStatus.PUBLIE:
        return True
    return False


def _can_manage_document(current: CurrentUser, doc: Document) -> bool:
    """Modifier / supprimer / remplacer le fichier."""
    if current.is_admin:
        return True
    return doc.section_id is not None and doc.section_id == current.section_id and doc.author_id == current.id


@router.get("/categories", response_model=list[DocumentCategoryOut])
def list_categories(db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    return db.query(DocumentCategory).order_by(DocumentCategory.name).all()


@router.post("/categories", response_model=DocumentCategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: DocumentCategoryCreate, db: Session = Depends(get_db), current: CurrentUser = Depends(require_admin)):
    if db.query(DocumentCategory).filter(DocumentCategory.name == payload.name).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cette catégorie existe déjà.")
    category = DocumentCategory(name=payload.name, is_system=False)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(require_admin)):
    category = db.get(DocumentCategory, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Catégorie introuvable.")
    if category.is_system:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Les catégories prédéfinies ne peuvent pas être supprimées.")
    if db.query(Document).filter(Document.category_id == category_id).count() > 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Des documents utilisent encore cette catégorie.")
    db.delete(category)
    db.commit()
    return None


@router.get("", response_model=PaginatedDocuments)
def list_documents(
    section_id: uuid.UUID | None = Query(default=None),
    category_id: uuid.UUID | None = Query(default=None),
    doc_status: DocumentStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    query = _base_query(db)

    if current.is_admin:
        if section_id is not None:
            query = query.filter(Document.section_id == section_id)
    else:
        # Isolation stricte, appliquée ici côté serveur quel que soit ce que
        # le client demande : une section ne voit JAMAIS les documents privés
        # (EN_ATTENTE / REFUSE) d'une autre section, ni via un paramètre
        # trafiqué. Elle voit : ses propres documents (tous statuts) + les
        # documents publiés d'autres sections / du Vicariat.
        from sqlalchemy import and_, or_

        query = query.filter(
            or_(
                Document.section_id == current.section_id,
                Document.status == DocumentStatus.PUBLIE,
            )
        )

    if category_id is not None:
        query = query.filter(Document.category_id == category_id)
    if doc_status is not None:
        query = query.filter(Document.status == doc_status)
    if search:
        query = query.filter(Document.name.ilike(f"%{search}%"))

    total = query.count()
    items = (
        query.order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedDocuments(items=[_document_out(d) for d in items], total=total, page=page, page_size=page_size)


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    doc = _base_query(db).filter(Document.id == document_id).first()
    if doc is None or not _can_view_document(current, doc):
        # 404 plutôt que 403 pour ne pas révéler l'existence d'une ressource
        # inaccessible à un utilisateur non autorisé.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")
    return _document_out(doc)


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    name: str = Form(...),
    description: str | None = Form(default=None),
    category_id: uuid.UUID = Form(...),
    section_id: uuid.UUID | None = Form(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    category = db.get(DocumentCategory, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Catégorie inconnue.")

    if current.is_admin:
        target_section_id = section_id  # NULL autorisé : document "Vicariat"
        if target_section_id is not None and db.get(Section, target_section_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section introuvable.")
    else:
        # Une section ne peut JAMAIS uploader pour une autre section, même en
        # trafiquant le champ section_id du formulaire : on l'ignore et on
        # force sa propre section, côté serveur.
        target_section_id = current.section_id

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

    storage = get_storage_backend()
    size_bytes = _save_with_size_limit(storage, file, validated.stored_filename, settings.max_upload_size_bytes)

    doc = Document(
        name=name,
        description=description,
        stored_filename=validated.stored_filename,
        original_filename=(file.filename or "fichier")[:255],
        mime_type=validated.mime_type,
        size_bytes=size_bytes,
        category_id=category_id,
        section_id=target_section_id,
        author_id=current.id,
        status=DocumentStatus.EN_ATTENTE,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    notify_all_admins(
        db,
        type=NotificationType.DOCUMENT_SUBMITTED,
        message=f"Nouveau document soumis : « {doc.name} ».",
        resource_type="document",
        resource_id=doc.id,
    )
    log_action(
        db,
        user_id=current.id,
        user_label=_actor_label(db, current),
        action="DOCUMENT_UPLOADED",
        resource_type="document",
        resource_id=str(doc.id),
        resource_label=doc.name,
        ip_address=get_client_ip(request),
    )
    doc = _base_query(db).filter(Document.id == doc.id).first()
    return _document_out(doc)


def _save_with_size_limit(storage, file: UploadFile, stored_filename: str, max_size_bytes: int) -> int:
    """
    Copie le flux vers le stockage en imposant une limite de taille réelle
    (le Content-Length déclaré par le client n'est pas fiable). Supprime le
    fichier partiel et lève une erreur si la limite est dépassée.
    """
    CHUNK = 1024 * 1024
    total = 0
    dest_path = storage.path_for(stored_filename)
    with open(dest_path, "wb") as out:
        while True:
            chunk = file.file.read(CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > max_size_bytes:
                out.close()
                dest_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Fichier trop volumineux (max {max_size_bytes // (1024 * 1024)} Mo).",
                )
            out.write(chunk)
    return total


@router.put("/{document_id}", response_model=DocumentOut)
def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")
    if not _can_manage_document(current, doc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez pas modifier ce document.")
    if not current.is_admin and doc.status == DocumentStatus.PUBLIE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce document est déjà publié : contactez un administrateur pour le modifier.",
        )

    changes = payload.model_dump(exclude_unset=True)
    if "category_id" in changes and db.get(DocumentCategory, changes["category_id"]) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Catégorie inconnue.")
    for field, value in changes.items():
        setattr(doc, field, value)

    # Une section qui corrige un document refusé le repasse automatiquement
    # en attente de validation.
    if not current.is_admin and doc.status == DocumentStatus.REFUSE:
        doc.status = DocumentStatus.EN_ATTENTE
        doc.rejection_reason = None

    db.add(doc)
    db.commit()
    db.refresh(doc)

    log_action(
        db,
        user_id=current.id,
        user_label=_actor_label(db, current),
        action="DOCUMENT_UPDATED",
        resource_type="document",
        resource_id=str(doc.id),
        resource_label=doc.name,
        ip_address=get_client_ip(request),
    )
    doc = _base_query(db).filter(Document.id == doc.id).first()
    return _document_out(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")
    if not _can_manage_document(current, doc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous ne pouvez pas supprimer ce document.")

    label = doc.name
    stored_filename = doc.stored_filename
    db.delete(doc)
    db.commit()

    try:
        get_storage_backend().delete(stored_filename)
    except Exception:
        pass  # la métadonnée est déjà supprimée ; un fichier orphelin sur disque n'est pas bloquant

    log_action(
        db,
        user_id=current.id,
        user_label=_actor_label(db, current),
        action="DOCUMENT_DELETED",
        resource_type="document",
        resource_id=str(document_id),
        resource_label=label,
        ip_address=get_client_ip(request),
    )
    return None


@router.post("/{document_id}/approve", response_model=DocumentOut)
def approve_document(document_id: uuid.UUID, request: Request, db: Session = Depends(get_db), current: CurrentUser = Depends(require_admin)):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")

    doc.status = DocumentStatus.PUBLIE
    doc.rejection_reason = None
    doc.reviewed_by_id = current.id
    doc.reviewed_at = datetime.now(timezone.utc)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    notify(
        db,
        user_id=doc.author_id,
        type=NotificationType.DOCUMENT_APPROVED,
        message=f"Votre document « {doc.name} » a été approuvé et publié.",
        resource_type="document",
        resource_id=doc.id,
    )
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="DOCUMENT_APPROVED",
        resource_type="document", resource_id=str(doc.id), resource_label=doc.name, ip_address=get_client_ip(request),
    )
    doc = _base_query(db).filter(Document.id == doc.id).first()
    return _document_out(doc)


@router.post("/{document_id}/reject", response_model=DocumentOut)
def reject_document(
    document_id: uuid.UUID,
    payload: DocumentRejectRequest,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")

    doc.status = DocumentStatus.REFUSE
    doc.rejection_reason = payload.reason
    doc.reviewed_by_id = current.id
    doc.reviewed_at = datetime.now(timezone.utc)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    notify(
        db,
        user_id=doc.author_id,
        type=NotificationType.DOCUMENT_REJECTED,
        message=f"Votre document « {doc.name} » a été refusé. Motif : {payload.reason}",
        resource_type="document",
        resource_id=doc.id,
    )
    log_action(
        db, user_id=current.id, user_label=_actor_label(db, current), action="DOCUMENT_REJECTED",
        resource_type="document", resource_id=str(doc.id), resource_label=doc.name, ip_address=get_client_ip(request),
    )
    doc = _base_query(db).filter(Document.id == doc.id).first()
    return _document_out(doc)


@router.get("/{document_id}/download")
def download_document(document_id: uuid.UUID, db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    doc = db.get(Document, document_id)
    if doc is None or not _can_view_document(current, doc):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document introuvable.")

    storage = get_storage_backend()
    try:
        stream = storage.open(doc.stored_filename)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable sur le serveur.")

    return StreamingResponse(
        stream,
        media_type=doc.mime_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.original_filename}"'},
    )
