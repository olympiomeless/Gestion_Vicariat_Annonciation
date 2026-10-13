"""
API PUBLIQUE (étape 14) : aucune authentification requise, aucune donnée
privée exposée. Chaque requête filtre explicitement sur le statut PUBLIE (ou
équivalent) — jamais seulement dans le frontend — pour qu'un brouillon, une
soumission en attente ou un contenu refusé ne soit JAMAIS accessible par ce
chemin, quelle que soit la manière dont on essaie de l'atteindre (liste,
accès direct par ID, téléchargement).

Cette API remplace le mécanisme précédent de lecture directe de fichiers
Google Sheets (CSV) par le site statique : le site public peut interroger ces
mêmes endpoints pour rester à jour sans republier de code.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.api.v1.mouvement import get_or_create_mouvement_content
from app.core.database import get_db
from app.models.actualite import Actualite, ActualiteStatus
from app.models.bureau import BureauMember
from app.models.document import Document, DocumentCategory, DocumentStatus
from app.models.effectif import EffectifCategorie
from app.models.gallery import GalleryPhoto
from app.models.programme import ProgrammeActivite
from app.models.section import Section
from app.schemas.public import (
    PaginatedPublicActualites,
    PaginatedPublicDocuments,
    PaginatedPublicGallery,
    PaginatedPublicProgramme,
    PublicActualiteOut,
    PublicBureauMemberOut,
    PublicDocumentOut,
    PublicEffectifOut,
    PublicGalleryPhotoOut,
    PublicMouvementOut,
    PublicProgrammeOut,
    PublicSectionOut,
)
from app.storage.factory import get_storage_backend

router = APIRouter(prefix="/public", tags=["public"])

PHOTO_MIME = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


@router.get("/mouvement", response_model=PublicMouvementOut)
def public_mouvement(db: Session = Depends(get_db)):
    return get_or_create_mouvement_content(db)


@router.get("/sections", response_model=list[PublicSectionOut])
def public_sections(db: Session = Depends(get_db)):
    return (
        db.query(Section)
        .filter(Section.is_active.is_(True))
        .order_by(Section.display_order.asc())
        .all()
    )


@router.get("/sections/{section_id}/photo")
def public_section_photo(section_id: uuid.UUID, db: Session = Depends(get_db)):
    # Une photo de section n'a pas de statut de validation à part entière :
    # elle est publique dès qu'un administrateur la dépose. Pas de filtre sur
    # is_active ici (contrairement à la liste) : une image seule ne révèle
    # rien de sensible, et ça évite une image cassée dans l'admin pour une
    # section temporairement masquée.
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


@router.get("/bureau", response_model=list[PublicBureauMemberOut])
def public_bureau(db: Session = Depends(get_db)):
    return (
        db.query(BureauMember)
        .filter(BureauMember.is_active.is_(True))
        .order_by(BureauMember.display_order.asc())
        .all()
    )


@router.get("/bureau/{member_id}/photo")
def public_bureau_photo(member_id: uuid.UUID, db: Session = Depends(get_db)):
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


@router.get("/effectifs", response_model=list[PublicEffectifOut])
def public_effectifs(db: Session = Depends(get_db)):
    return db.query(EffectifCategorie).order_by(EffectifCategorie.display_order.asc()).all()


@router.get("/programme", response_model=PaginatedPublicProgramme)
def public_programme(
    section_slug: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = (
        db.query(ProgrammeActivite)
        .options(joinedload(ProgrammeActivite.section))
        .filter(ProgrammeActivite.status == DocumentStatus.PUBLIE)
    )
    if section_slug:
        query = query.join(Section, ProgrammeActivite.section_id == Section.id).filter(Section.slug == section_slug)

    total = query.count()
    items = query.order_by(ProgrammeActivite.activity_date.asc()).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedPublicProgramme(
        items=[
            PublicProgrammeOut.model_validate(
                {
                    **p.__dict__,
                    "section_slug": p.section.slug if p.section else None,
                    "section_name": p.section.name if p.section else None,
                }
            )
            for p in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/actualites", response_model=PaginatedPublicActualites)
def public_actualites(
    section_slug: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Actualite)
        .options(joinedload(Actualite.section))
        .filter(Actualite.status == ActualiteStatus.PUBLIE)
    )
    if section_slug:
        query = query.join(Section, Actualite.section_id == Section.id).filter(Section.slug == section_slug)

    total = query.count()
    items = query.order_by(Actualite.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedPublicActualites(
        items=[
            PublicActualiteOut.model_validate(
                {
                    **a.__dict__,
                    "section_slug": a.section.slug if a.section else None,
                    "section_name": a.section.name if a.section else None,
                }
            )
            for a in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/gallery", response_model=PaginatedPublicGallery)
def public_gallery(
    section_slug: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = (
        db.query(GalleryPhoto)
        .options(joinedload(GalleryPhoto.section))
        .filter(GalleryPhoto.status == DocumentStatus.PUBLIE)
    )
    if section_slug:
        query = query.join(Section, GalleryPhoto.section_id == Section.id).filter(Section.slug == section_slug)

    total = query.count()
    items = query.order_by(GalleryPhoto.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedPublicGallery(
        items=[
            PublicGalleryPhotoOut.model_validate(
                {
                    **p.__dict__,
                    "section_slug": p.section.slug if p.section else None,
                    "section_name": p.section.name if p.section else None,
                }
            )
            for p in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/gallery/{photo_id}/file")
def public_gallery_file(photo_id: uuid.UUID, db: Session = Depends(get_db)):
    photo = db.get(GalleryPhoto, photo_id)
    # 404 dans tous les cas où la photo n'est pas publique : introuvable ou
    # pas encore validée, on ne fait aucune différence visible depuis l'extérieur.
    if photo is None or photo.status != DocumentStatus.PUBLIE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo introuvable.")

    storage = get_storage_backend()
    try:
        stream = storage.open(photo.stored_filename)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fichier introuvable sur le serveur.")

    extension = photo.stored_filename.rsplit(".", 1)[-1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(
        extension, "application/octet-stream"
    )
    return StreamingResponse(stream, media_type=mime)


@router.get("/documents", response_model=PaginatedPublicDocuments)
def public_documents(
    category_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Document)
        .options(joinedload(Document.category), joinedload(Document.section))
        .filter(Document.status == DocumentStatus.PUBLIE)
    )
    if category_id:
        query = query.filter(Document.category_id == category_id)

    total = query.count()
    items = query.order_by(Document.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedPublicDocuments(
        items=[
            PublicDocumentOut.model_validate(
                {
                    **d.__dict__,
                    "category_name": d.category.name if d.category else None,
                    "section_name": d.section.name if d.section else None,
                }
            )
            for d in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/documents/{document_id}/download")
def public_document_download(document_id: uuid.UUID, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if doc is None or doc.status != DocumentStatus.PUBLIE:
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


@router.get("/documents/categories", response_model=list[str])
def public_document_categories(db: Session = Depends(get_db)):
    names = (
        db.query(DocumentCategory.name)
        .join(Document, Document.category_id == DocumentCategory.id)
        .filter(Document.status == DocumentStatus.PUBLIE)
        .distinct()
        .order_by(DocumentCategory.name)
        .all()
    )
    return [n[0] for n in names]
