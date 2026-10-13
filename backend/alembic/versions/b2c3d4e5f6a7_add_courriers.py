"""add courriers table and notification types

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-13 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Courriers échangés entre une section et le Bureau du Vicariat : message
    # libre ou demande de fichier, traités (note + fichier optionnels) par un
    # administrateur. Deux enums nouveaux (courrier_kind, courrier_status) :
    # pas de create_type=False ici, ils n'existent pas encore en base.
    op.create_table(
        'courriers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('section_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kind', sa.Enum('MESSAGE', 'DEMANDE_FICHIER', name='courrier_kind'), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('attachment_filename', sa.String(length=255), nullable=True),
        sa.Column('attachment_original_filename', sa.String(length=255), nullable=True),
        sa.Column('status', sa.Enum('NOUVEAU', 'TRAITE', name='courrier_status'), nullable=False),
        sa.Column('response_note', sa.Text(), nullable=True),
        sa.Column('response_filename', sa.String(length=255), nullable=True),
        sa.Column('response_original_filename', sa.String(length=255), nullable=True),
        sa.Column('handled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('handled_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['section_id'], ['sections.id']),
        sa.ForeignKeyConstraint(['author_id'], ['users.id']),
        sa.ForeignKeyConstraint(['handled_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_courriers_section_id'), 'courriers', ['section_id'])
    op.create_index(op.f('ix_courriers_kind'), 'courriers', ['kind'])
    op.create_index(op.f('ix_courriers_status'), 'courriers', ['status'])

    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'COURRIER_SUBMITTED'")
    op.execute("ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'COURRIER_TRAITE'")


def downgrade() -> None:
    op.drop_index(op.f('ix_courriers_status'), table_name='courriers')
    op.drop_index(op.f('ix_courriers_kind'), table_name='courriers')
    op.drop_index(op.f('ix_courriers_section_id'), table_name='courriers')
    op.drop_table('courriers')
    op.execute("DROP TYPE IF EXISTS courrier_status")
    op.execute("DROP TYPE IF EXISTS courrier_kind")
    # Retirer une valeur d'un enum existant (notification_type) n'est pas
    # supporté par PostgreSQL : non réversible, intentionnellement (voir
    # a95e84ad2b08 / a1b2c3d4e5f6 pour la même remarque).
