"""add programme notification types

Revision ID: a95e84ad2b08
Revises: 64cac2ed52ff
Create Date: 2026-09-23 08:09:31.264411

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a95e84ad2b08'
down_revision: Union[str, None] = '64cac2ed52ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ajout de nouvelles valeurs à l'enum PostgreSQL existant (workflow de
    # validation du programme, étape 11). PostgreSQL 12+ autorise ADD VALUE
    # dans une transaction tant que la nouvelle valeur n'est pas utilisée
    # dans la même transaction.
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'PROGRAMME_SUBMITTED'")
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'PROGRAMME_PUBLISHED'")
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'PROGRAMME_REJECTED'")


def downgrade() -> None:
    # PostgreSQL ne permet pas de retirer une valeur d'un enum existant.
    # Une véritable rétrogradation nécessiterait de recréer le type ; on ne
    # le fait pas ici car cela casserait les notifications déjà enregistrées
    # avec ces valeurs.
    pass
