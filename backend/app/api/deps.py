"""
Dépendances FastAPI communes : session DB, utilisateur courant, contrôle de
rôle et d'appartenance à une section.

Règle centrale du projet (point 10 du cahier des charges) : toute vérification
de permission se fait ICI, côté serveur, sur chaque endpoint protégé — jamais
seulement dans l'interface. Aucune route ne doit faire confiance à un
paramètre envoyé par le client pour décider qui peut voir/modifier quoi.
"""
import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import JWTError, decode_access_token
from app.models.user import Role, User

bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    """Représentation légère de l'utilisateur authentifié, dérivée du JWT."""

    def __init__(self, id: uuid.UUID, role: str, section_id: Optional[uuid.UUID]):
        self.id = id
        self.role = role
        self.section_id = section_id

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise.")
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expirée.")

    user_id = payload.get("sub")
    try:
        user_uuid = uuid.UUID(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide.")

    # On revérifie en base à chaque requête que le compte existe encore et
    # est actif : un JWT émis avant une désactivation de compte ne doit plus
    # donner accès, même s'il n'est pas encore expiré.
    user = db.get(User, user_uuid)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Compte désactivé ou introuvable.")

    return CurrentUser(id=user.id, role=user.role.name, section_id=user.section_id)


def get_current_user_full(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Retourne l'objet User complet quand on a besoin de plus que id/role/section."""
    user = db.get(User, current.id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Compte introuvable.")
    return user


def require_roles(*roles: str):
    def _dep(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'avez pas les permissions nécessaires.",
            )
        return current

    return _dep


require_admin = require_roles(Role.ADMIN)
require_any_role = require_roles(Role.ADMIN, Role.SECTION)


def get_client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None
