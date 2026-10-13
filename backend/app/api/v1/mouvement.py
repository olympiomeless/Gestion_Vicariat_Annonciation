"""
Contenu de la section « Le mouvement » du site public : instance UNIQUE
(pas de notion de section), lecture par tout utilisateur connecté, écriture
réservée à l'administrateur. L'accès public (site vitrine, sans connexion)
est exposé séparément dans app/api/v1/public.py, qui réutilise
get_or_create_mouvement_content() ci-dessous pour ne jamais renvoyer une
section vide, même avant la toute première modification par l'administrateur.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_client_ip, get_current_user, require_admin
from app.core.database import get_db
from app.models.mouvement import MouvementContent
from app.models.user import User
from app.schemas.mouvement import MouvementContentOut, MouvementContentUpdate
from app.services.audit_service import log_action

router = APIRouter(prefix="/mouvement", tags=["mouvement"])

# Contenu d'origine du site (repris tel quel de l'ancien site statique) : sert
# de valeurs par défaut la toute première fois que la ligne est créée, pour
# que rien ne disparaisse du site public avant la première édition par
# l'administrateur.
DEFAULTS = dict(
    intro_title="Un vicariat, une identité, une mission",
    intro_paragraph_1=(
        "Au cœur du Mouvement d'Action Catholique pour l'Enfance Cœurs Vaillants – "
        "Âmes Vaillantes (CV-AV) du diocèse de Yopougon, le Vicariat Forain de "
        "l'Annonciation occupe une place particulière parmi les treize vicariats qui "
        "font vivre la mission du mouvement auprès des enfants et des jeunes."
    ),
    intro_paragraph_2=(
        "Plus qu'une simple circonscription administrative, notre vicariat est un "
        "espace de communion, de formation, de service et d'engagement, où des "
        "accompagnateurs mettent leur temps et leurs talents au service de "
        "l'épanouissement spirituel, humain et social des enfants qui leur sont "
        "confiés — sous la tutelle du Bureau Diocésain des CV-AV de Yopougon."
    ),
    intro_paragraph_3=(
        "La force du vicariat réside dans la complémentarité de ses cinq sections, "
        "classées ci-dessous par ordre d'ancienneté : chacune apporte sa pierre à un "
        "même édifice, chaque maillon essentiel à la solidité de l'ensemble."
    ),
    theme_annee_label="Thème de l'année pastorale 2025-2026 — Diocèse de Yopougon",
    theme_annee_quote=(
        "Avec la Vierge Marie, par la prière du chapelet, prions avec confiance pour "
        "la paix dans nos familles, dans nos villages et dans notre pays."
    ),
    limite_nord="Vicariat de Saint-André",
    limite_sud="Vicariat de Saint-Vincent-de-Paul",
    limite_ouest="Vicariat de Saint-Pierre",
    tutelle="Bureau Diocésain CV-AV Yopougon",
    aumonier_name="Abbé Kablan Georges",
    aumonier_role="Aumônier du Vicariat de l'Annonciation (Saint-Marc)",
    vicaire_text=(
        "Le mouvement CV-AV du diocèse de Yopougon bénéficie également de "
        "l'accompagnement du Père Paul-Arnaud Yao, Vicaire à la paroisse Sainte "
        "Jeanne d'Arc."
    ),
    rang_diocese="1/13",
)


def get_or_create_mouvement_content(db: Session) -> MouvementContent:
    content = db.query(MouvementContent).first()
    if content is None:
        content = MouvementContent(**DEFAULTS)
        db.add(content)
        db.commit()
        db.refresh(content)
    return content


def _actor_label(db: Session, current: CurrentUser) -> str:
    user = db.get(User, current.id)
    return user.username if user else str(current.id)


@router.get("", response_model=MouvementContentOut)
def get_mouvement(db: Session = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    return get_or_create_mouvement_content(db)


@router.put("", response_model=MouvementContentOut)
def update_mouvement(
    payload: MouvementContentUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    content = get_or_create_mouvement_content(db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(content, field, value)
    db.commit()
    db.refresh(content)

    log_action(
        db,
        user_id=current.id,
        user_label=_actor_label(db, current),
        action="MOUVEMENT_CONTENT_UPDATED",
        resource_type="mouvement_content",
        resource_id=str(content.id),
        resource_label="Le mouvement",
        ip_address=get_client_ip(request),
    )
    return content
