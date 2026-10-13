"""add username login identifier to users, make email optional

Revision ID: f1a2b3c4d5e6
Revises: d9cb9b7fcdbc
Create Date: 2026-10-07 09:00:00.000000

"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'd9cb9b7fcdbc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


USERNAME_RE = re.compile(r'[^a-z0-9._-]')


def _slugify(email: str | None, fallback: str) -> str:
    raw = (email or '').split('@')[0].lower()
    raw = USERNAME_RE.sub('', raw)
    if not raw:
        raw = fallback
    if not raw[0].isalnum():
        raw = 'u' + raw
    return raw[:40]


def upgrade() -> None:
    # Chaque section doit avoir un identifiant de connexion propre (distinct
    # de l'e-mail, qui devient optionnel) — point 7 de la demande : « chaque
    # section aura un identifiant et un mot de passe par défaut ».
    op.add_column('users', sa.Column('username', sa.String(length=100), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, email FROM users ORDER BY created_at")).fetchall()
    seen: set[str] = set()
    for row in rows:
        base = _slugify(row.email, fallback=f"utilisateur{str(row.id)[:8]}")
        candidate = base
        n = 2
        while candidate in seen:
            candidate = f"{base}-{n}"
            n += 1
        seen.add(candidate)
        bind.execute(sa.text("UPDATE users SET username = :u WHERE id = :id"), {"u": candidate, "id": row.id})

    op.alter_column('users', 'username', nullable=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # L'e-mail n'est plus la clé de connexion : il devient optionnel (les
    # comptes SECTION n'en ont pas nécessairement un).
    op.alter_column('users', 'email', nullable=True)


def downgrade() -> None:
    op.alter_column('users', 'email', nullable=False)
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_column('users', 'username')
