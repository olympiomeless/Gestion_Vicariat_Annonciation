"""Logique métier de l'authentification : login, refresh, logout, mot de passe oublié."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token_for_lookup,
    hash_password,
    verify_password,
)
from app.models.user import PasswordResetToken, RefreshToken, User
from app.services.audit_service import log_action

MAX_FAILED_ATTEMPTS_WINDOW_MIN = 15


class AuthError(Exception):
    """Erreur métier d'authentification (identifiants invalides, compte inactif, etc.)."""


def authenticate(db: Session, *, username: str, password: str, ip: Optional[str]) -> User:
    user = db.query(User).filter(User.username == username.lower().strip()).first()
    if user is None or not verify_password(password, user.password_hash):
        log_action(
            db,
            user_id=user.id if user else None,
            user_label=username,
            action="LOGIN_FAILED",
            resource_type="auth",
            result="FAILURE",
            ip_address=ip,
        )
        raise AuthError("Identifiant ou mot de passe incorrect.")

    if not user.is_active:
        log_action(
            db,
            user_id=user.id,
            user_label=user.username,
            action="LOGIN_BLOCKED_INACTIVE",
            resource_type="auth",
            result="FAILURE",
            ip_address=ip,
        )
        raise AuthError("Ce compte a été désactivé. Contactez un administrateur.")

    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    log_action(
        db,
        user_id=user.id,
        user_label=user.username,
        action="LOGIN_SUCCESS",
        resource_type="auth",
        result="SUCCESS",
        ip_address=ip,
        commit=False,
    )
    db.commit()
    db.refresh(user)
    return user


def issue_tokens(db: Session, *, user: User, ip: Optional[str], user_agent: Optional[str]) -> tuple[str, str, int]:
    """Retourne (access_token, refresh_token_brut, expires_in_secondes)."""
    access_token = create_access_token(user_id=str(user.id), role=user.role.name, section_id=user.section_id)

    raw_refresh, refresh_hash = generate_opaque_token()
    now = datetime.now(timezone.utc)
    token_row = RefreshToken(
        user_id=user.id,
        token_hash=refresh_hash,
        user_agent=(user_agent or "")[:255],
        ip_address=ip,
        created_at=now,
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(token_row)
    db.commit()

    return access_token, raw_refresh, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def rotate_refresh_token(db: Session, *, raw_refresh_token: str, ip: Optional[str], user_agent: Optional[str]):
    """Valide un refresh token, le révoque, et en émet un nouveau (rotation)."""
    token_hash = hash_opaque_token_for_lookup(raw_refresh_token)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    now = datetime.now(timezone.utc)
    if row is None or row.revoked_at is not None or row.expires_at < now:
        raise AuthError("Session expirée, merci de vous reconnecter.")

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise AuthError("Compte désactivé ou introuvable.")

    # Rotation : l'ancien jeton est immédiatement révoqué, un seul jeton
    # valide à la fois par "session" — limite l'impact d'un vol de jeton.
    row.revoked_at = now
    db.add(row)
    db.commit()

    access_token, new_refresh, expires_in = issue_tokens(db, user=user, ip=ip, user_agent=user_agent)
    return user, access_token, new_refresh, expires_in


def revoke_refresh_token(db: Session, *, raw_refresh_token: str) -> None:
    token_hash = hash_opaque_token_for_lookup(raw_refresh_token)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if row and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.add(row)
        db.commit()


def revoke_all_sessions_for_user(db: Session, *, user_id: uuid.UUID) -> None:
    now = datetime.now(timezone.utc)
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
    ).update({"revoked_at": now})
    db.commit()


def request_password_reset(db: Session, *, email: str) -> Optional[str]:
    """
    Retourne le jeton BRUT de réinitialisation si un compte existe, sinon None.
    Le message renvoyé à l'API doit être IDENTIQUE dans les deux cas (pour ne
    pas révéler si un e-mail existe en base). L'envoi effectif par e-mail
    n'est pas branché ici (pas de service SMTP configuré) : en développement
    le jeton est retourné pour permettre de tester le flux de bout en bout.
    """
    user = db.query(User).filter(User.email == email.lower().strip()).first() if email else None
    if user is None or not user.is_active:
        return None

    raw_token, token_hash = generate_opaque_token()
    now = datetime.now(timezone.utc)
    reset_row = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        created_at=now,
        expires_at=now + timedelta(hours=1),
    )
    db.add(reset_row)
    db.commit()
    return raw_token


def reset_password(db: Session, *, raw_token: str, new_password: str) -> None:
    token_hash = hash_opaque_token_for_lookup(raw_token)
    row = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()

    now = datetime.now(timezone.utc)
    if row is None or row.used_at is not None or row.expires_at < now:
        raise AuthError("Lien de réinitialisation invalide ou expiré.")

    user = db.get(User, row.user_id)
    if user is None:
        raise AuthError("Compte introuvable.")

    user.password_hash = hash_password(new_password)
    row.used_at = now
    db.add(user)
    db.add(row)
    db.commit()

    # Une réinitialisation de mot de passe invalide toutes les sessions
    # existantes — bonne pratique de sécurité standard.
    revoke_all_sessions_for_user(db, user_id=user.id)


def change_password(db: Session, *, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise AuthError("Mot de passe actuel incorrect.")
    user.password_hash = hash_password(new_password)
    db.add(user)
    db.commit()
    revoke_all_sessions_for_user(db, user_id=user.id)
