"""add rang_diocese to mouvement content

Revision ID: d9cb9b7fcdbc
Revises: 80be6aa624ab
Create Date: 2026-09-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9cb9b7fcdbc'
down_revision: Union[str, None] = '80be6aa624ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


mouvement_content = sa.table(
    'mouvement_content',
    sa.column('rang_diocese', sa.Text()),
)


def upgrade() -> None:
    op.add_column(
        'mouvement_content',
        sa.Column('rang_diocese', sa.Text(), nullable=False, server_default=''),
    )
    # Valeur d'origine (celle codée en dur jusqu'ici dans le bandeau d'accueil
    # du site public) pour la ligne déjà en base, avant la première édition
    # par l'administrateur.
    op.execute(mouvement_content.update().values(rang_diocese='1/13'))
    op.alter_column('mouvement_content', 'rang_diocese', server_default=None)


def downgrade() -> None:
    op.drop_column('mouvement_content', 'rang_diocese')
