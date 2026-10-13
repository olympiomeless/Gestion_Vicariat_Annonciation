"""
Regroupe tous les modèles pour que Base.metadata les connaisse (nécessaire à
Alembic --autogenerate et à la création des tables).
"""
from app.models.user import Role, User, RefreshToken, PasswordResetToken  # noqa: F401
from app.models.section import Section  # noqa: F401
from app.models.document import DocumentCategory, Document, DocumentStatus  # noqa: F401
from app.models.actualite import Actualite, ActualiteStatus  # noqa: F401
from app.models.programme import ProgrammeActivite  # noqa: F401
from app.models.gallery import GalleryPhoto  # noqa: F401
from app.models.notification import Notification, NotificationType  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.bureau import BureauMember  # noqa: F401
from app.models.section_bureau import SectionBureauMember  # noqa: F401
from app.models.effectif import EffectifCategorie  # noqa: F401
from app.models.mouvement import MouvementContent  # noqa: F401
from app.models.courrier import Courrier, CourrierKind, CourrierStatus  # noqa: F401

__all__ = [
    "Role",
    "User",
    "RefreshToken",
    "PasswordResetToken",
    "Section",
    "DocumentCategory",
    "Document",
    "DocumentStatus",
    "Actualite",
    "ActualiteStatus",
    "ProgrammeActivite",
    "GalleryPhoto",
    "Notification",
    "NotificationType",
    "AuditLog",
    "BureauMember",
    "SectionBureauMember",
    "EffectifCategorie",
    "MouvementContent",
    "Courrier",
    "CourrierKind",
    "CourrierStatus",
]
