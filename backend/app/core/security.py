"""
Primitives de sécurité : hachage de mot de passe, JWT d'accès, et jetons
opaques (refresh / réinitialisation de mot de passe) stockés hachés en base.

Principes appliqués :
- Les mots de passe ne sont JAMAIS stockés en clair (argon2 via passlib).
- Les refresh tokens et tokens de réinitialisation sont générés aléatoirement
  côté serveur, puis seul leur HASH SHA-256 est stocké en base — comme pour un
  mot de passe, une fuite de la base ne permet pas de rejouer les jetons.
- Les JWT d'accès sont courts (30 min par défaut) et ne sont jamais persistés :
  leur seule invalidation possible est l'expiration ou la révocation de la
  session (refresh token) qui a permis de les émettre.
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(*, user_id: str, role: str, section_id: Optional[str]) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "section_id": str(section_id) if section_id else None,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Lève jose.JWTError si le token est invalide, malformé ou expiré."""
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Type de jeton invalide")
    return payload


def _hash_opaque_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_opaque_token() -> tuple[str, str]:
    """Génère un jeton aléatoire (refresh / reset). Retourne (jeton_brut, hash_a_stocker)."""
    raw = secrets.token_urlsafe(48)
    return raw, _hash_opaque_token(raw)


def hash_opaque_token_for_lookup(raw_token: str) -> str:
    return _hash_opaque_token(raw_token)


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "generate_opaque_token",
    "hash_opaque_token_for_lookup",
    "JWTError",
]
