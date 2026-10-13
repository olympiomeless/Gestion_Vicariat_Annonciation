"""
Tableaux de bord Admin et Section (étape 6 / étape 7 du cahier des charges).

Toutes les statistiques sont calculées en base à chaque appel — aucune donnée
n'est simulée ou codée en dur. Le tableau de bord Section ne reçoit jamais les
données d'une autre section : le `section_id` effectif est toujours dérivé du
compte connecté côté serveur (voir app/api/deps.py), jamais du paramètre de
requête envoyé par un utilisateur non-admin.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, require_admin
from app.api.v1.documents import _base_query, _document_out
from app.core.database import get_db
from app.models.actualite import Actualite, ActualiteStatus
from app.models.document import Document, DocumentStatus
from app.models.gallery import GalleryPhoto
from app.models.programme import ProgrammeActivite
from app.models.section import Section
from app.models.user import User
from app.schemas.dashboard import AdminDashboardStats, SectionDashboardStats, SectionStat

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/admin", response_model=AdminDashboardStats)
def admin_dashboard(db: Session = Depends(get_db), current: CurrentUser = Depends(require_admin)):
    sections = db.query(Section).all()

    documents_count = db.query(func.count(Document.id)).scalar() or 0
    documents_pending_count = (
        db.query(func.count(Document.id)).filter(Document.status == DocumentStatus.EN_ATTENTE).scalar() or 0
    )
    documents_published_count = (
        db.query(func.count(Document.id)).filter(Document.status == DocumentStatus.PUBLIE).scalar() or 0
    )
    documents_refused_count = (
        db.query(func.count(Document.id)).filter(Document.status == DocumentStatus.REFUSE).scalar() or 0
    )

    actualites_count = db.query(func.count(Actualite.id)).scalar() or 0
    actualites_pending_count = (
        db.query(func.count(Actualite.id)).filter(Actualite.status == ActualiteStatus.SOUMIS).scalar() or 0
    )
    programmes_count = db.query(func.count(ProgrammeActivite.id)).scalar() or 0
    gallery_photos_count = db.query(func.count(GalleryPhoto.id)).scalar() or 0
    gallery_photos_pending_count = (
        db.query(func.count(GalleryPhoto.id)).filter(GalleryPhoto.status == DocumentStatus.EN_ATTENTE).scalar() or 0
    )

    recent_documents = _base_query(db).order_by(Document.created_at.desc()).limit(10).all()
    pending_documents = (
        _base_query(db)
        .filter(Document.status == DocumentStatus.EN_ATTENTE)
        .order_by(Document.created_at.asc())
        .limit(20)
        .all()
    )

    sections_breakdown: list[SectionStat] = []
    for section in sections:
        users_count = db.query(func.count(User.id)).filter(User.section_id == section.id).scalar() or 0
        section_documents_count = (
            db.query(func.count(Document.id)).filter(Document.section_id == section.id).scalar() or 0
        )
        section_documents_pending = (
            db.query(func.count(Document.id))
            .filter(Document.section_id == section.id, Document.status == DocumentStatus.EN_ATTENTE)
            .scalar()
            or 0
        )
        sections_breakdown.append(
            SectionStat(
                section_id=section.id,
                section_name=section.name,
                users_count=users_count,
                documents_count=section_documents_count,
                documents_pending_count=section_documents_pending,
            )
        )

    return AdminDashboardStats(
        sections_count=len(sections),
        users_count=db.query(func.count(User.id)).scalar() or 0,
        users_active_count=db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0,
        documents_count=documents_count,
        documents_pending_count=documents_pending_count,
        documents_published_count=documents_published_count,
        documents_refused_count=documents_refused_count,
        actualites_count=actualites_count,
        actualites_pending_count=actualites_pending_count,
        programmes_count=programmes_count,
        gallery_photos_count=gallery_photos_count,
        gallery_photos_pending_count=gallery_photos_pending_count,
        recent_documents=[_document_out(d) for d in recent_documents],
        pending_documents=[_document_out(d) for d in pending_documents],
        sections_breakdown=sections_breakdown,
    )


@router.get("/section", response_model=SectionDashboardStats)
def section_dashboard(
    section_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
):
    # Un compte SECTION ne peut jamais consulter le tableau de bord d'une
    # autre section, même en modifiant le paramètre `section_id` de la
    # requête : sa propre section (dérivée du JWT) prévaut toujours.
    if current.is_admin:
        if section_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="section_id est requis pour un compte administrateur.",
            )
        effective_section_id = section_id
    else:
        if current.section_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce compte n'est rattaché à aucune section.",
            )
        effective_section_id = current.section_id

    section = db.get(Section, effective_section_id)
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section introuvable.")

    documents_count = (
        db.query(func.count(Document.id)).filter(Document.section_id == section.id).scalar() or 0
    )
    documents_pending_count = (
        db.query(func.count(Document.id))
        .filter(Document.section_id == section.id, Document.status == DocumentStatus.EN_ATTENTE)
        .scalar()
        or 0
    )
    documents_published_count = (
        db.query(func.count(Document.id))
        .filter(Document.section_id == section.id, Document.status == DocumentStatus.PUBLIE)
        .scalar()
        or 0
    )
    documents_refused_count = (
        db.query(func.count(Document.id))
        .filter(Document.section_id == section.id, Document.status == DocumentStatus.REFUSE)
        .scalar()
        or 0
    )
    actualites_count = (
        db.query(func.count(Actualite.id)).filter(Actualite.section_id == section.id).scalar() or 0
    )
    programmes_count = (
        db.query(func.count(ProgrammeActivite.id)).filter(ProgrammeActivite.section_id == section.id).scalar() or 0
    )
    gallery_photos_count = (
        db.query(func.count(GalleryPhoto.id)).filter(GalleryPhoto.section_id == section.id).scalar() or 0
    )

    recent_documents = (
        _base_query(db)
        .filter(Document.section_id == section.id)
        .order_by(Document.created_at.desc())
        .limit(10)
        .all()
    )

    return SectionDashboardStats(
        section_id=section.id,
        section_name=section.name,
        documents_count=documents_count,
        documents_pending_count=documents_pending_count,
        documents_published_count=documents_published_count,
        documents_refused_count=documents_refused_count,
        actualites_count=actualites_count,
        programmes_count=programmes_count,
        gallery_photos_count=gallery_photos_count,
        recent_documents=[_document_out(d) for d in recent_documents],
    )
