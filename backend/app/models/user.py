import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_pk


class Role(Base):
    """
    Table des rôles plutôt qu'un enum figé : permet à l'administrateur
    d'ajouter d'autres rôles plus tard sans migration de schéma (point 3
    du cahier des charges : "prévoir la possibilité d'ajouter ultérieurement
    d'autres rôles").
    """

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="role")

    # Noms de rôles utilisés par la logique métier (voir app/core/permissions.py)
    ADMIN = "ADMIN"
    SECTION = "SECTION"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    # Identifiant de connexion (point 7 : « chaque section aura un identifiant
    # et un mot de passe par défaut ») — remplace l'e-mail comme clé de login.
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    # L'e-mail devient optionnel : les comptes SECTION n'en ont pas forcément
    # un, seul l'identifiant est garanti. Reste utile pour « mot de passe
    # oublié » quand il est renseigné.
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    role_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    role: Mapped["Role"] = relationship(back_populates="users")

    # Uniquement renseigné pour les utilisateurs de rôle SECTION.
    # Un utilisateur ADMIN a section_id = NULL (accès global).
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("sections.id"), nullable=True
    )
    section: Mapped[Optional["Section"]] = relationship(back_populates="users")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.username} role={self.role.name if self.role else None}>"


class RefreshToken(Base):
    """
    Session de connexion opaque. Seul le hash SHA-256 du jeton brut est stocké
    (comme pour un mot de passe) : une fuite de la base ne permet pas de
    rejouer une session. Révocable individuellement (déconnexion) ou en masse
    (réinitialisation de mot de passe, désactivation de compte).
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
