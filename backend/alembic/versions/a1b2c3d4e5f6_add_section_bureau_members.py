"""add section bureau members table and notification types

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-10-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Chaque section peut désormais gérer son propre bureau (distinct du
    # Bureau du Vicariat), soumis à validation de l'administrateur — même
    # enum document_status que les documents, le programme et la galerie.
    op.create_table(
        'section_bureau_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('section_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role_title', sa.String(length=255), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.Column('photo_filename', sa.String(length=255), nullable=True),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            'status',
            postgresql.ENUM('EN_ATTENTE', 'PUBLIE', 'REFUSE', name='document_status', create_type=False),
            nullable=False,
        ),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['section_id'], ['sections.id']),
        sa.ForeignKeyConstraint(['author_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_section_bureau_members_section_id'), 'section_bureau_members', ['section_id'])
    op.create_index(op.f('ix_section_bureau_members_status'), 'section_bureau_members', ['status'])

    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'SECTION_BUREAU_SUBMITTED'")
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'SECTION_BUREAU_PUBLISHED'")
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'SECTION_BUREAU_REJECTED'")


def downgrade() -> None:
    op.drop_index(op.f('ix_section_bureau_members_status'), table_name='section_bureau_members')
    op.drop_index(op.f('ix_section_bureau_members_section_id'), table_name='section_bureau_members')
    op.drop_table('section_bureau_members')
    # PostgreSQL ne permet pas de retirer une valeur d'un enum existant (voir
    # a95e84ad2b08 pour la même remarque) : non réversible, intentionnellement.
