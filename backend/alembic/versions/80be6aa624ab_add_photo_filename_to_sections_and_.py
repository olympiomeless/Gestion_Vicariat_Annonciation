"""add photo_filename to sections and bureau_members

Revision ID: 80be6aa624ab
Revises: 9b4d6af7cd6d
Create Date: 2026-09-30 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80be6aa624ab'
down_revision: Union[str, None] = '9b4d6af7cd6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nom de fichier stocké (géré par le backend de stockage) pour une photo
    # réellement déposée depuis l'administration — voir app/api/v1/sections.py
    # et app/api/v1/bureau.py, routes .../photo. Les colonnes existantes
    # (photo_url, photo_key) restent en place pour compatibilité.
    op.add_column('sections', sa.Column('photo_filename', sa.String(length=255), nullable=True))
    op.add_column('bureau_members', sa.Column('photo_filename', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('bureau_members', 'photo_filename')
    op.drop_column('sections', 'photo_filename')
