"""fix user fk cascade behavior for delete

Revision ID: 9973a557c7bc
Revises: 3717f1d048ab
Create Date: 2026-09-23 09:01:52.585340

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9973a557c7bc'
down_revision: Union[str, None] = '3717f1d048ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Corrige le comportement des clés étrangères vers users.id à la
    # suppression d'un compte : les jetons de session et les notifications
    # doivent disparaître avec le compte (CASCADE), tandis que le journal
    # d'audit et le champ "révisé par" d'un document doivent survivre en
    # perdant simplement la référence (SET NULL) — jamais une erreur bloquante.
    # Les FK vers author_id (documents/actualités/programme/galerie) restent
    # volontairement en RESTRICT : le contenu et son auteur ne doivent jamais
    # être perdus ; l'API refuse la suppression d'un compte auteur de contenu
    # et invite à le désactiver à la place.
    op.drop_constraint('audit_logs_user_id_fkey', 'audit_logs', type_='foreignkey')
    op.create_foreign_key('audit_logs_user_id_fkey', 'audit_logs', 'users', ['user_id'], ['id'], ondelete='SET NULL')
    op.drop_constraint('documents_reviewed_by_id_fkey', 'documents', type_='foreignkey')
    op.create_foreign_key('documents_reviewed_by_id_fkey', 'documents', 'users', ['reviewed_by_id'], ['id'], ondelete='SET NULL')
    op.drop_constraint('notifications_user_id_fkey', 'notifications', type_='foreignkey')
    op.create_foreign_key('notifications_user_id_fkey', 'notifications', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('password_reset_tokens_user_id_fkey', 'password_reset_tokens', type_='foreignkey')
    op.create_foreign_key('password_reset_tokens_user_id_fkey', 'password_reset_tokens', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('refresh_tokens_user_id_fkey', 'refresh_tokens', type_='foreignkey')
    op.create_foreign_key('refresh_tokens_user_id_fkey', 'refresh_tokens', 'users', ['user_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    op.drop_constraint('refresh_tokens_user_id_fkey', 'refresh_tokens', type_='foreignkey')
    op.create_foreign_key('refresh_tokens_user_id_fkey', 'refresh_tokens', 'users', ['user_id'], ['id'])
    op.drop_constraint('password_reset_tokens_user_id_fkey', 'password_reset_tokens', type_='foreignkey')
    op.create_foreign_key('password_reset_tokens_user_id_fkey', 'password_reset_tokens', 'users', ['user_id'], ['id'])
    op.drop_constraint('notifications_user_id_fkey', 'notifications', type_='foreignkey')
    op.create_foreign_key('notifications_user_id_fkey', 'notifications', 'users', ['user_id'], ['id'])
    op.drop_constraint('documents_reviewed_by_id_fkey', 'documents', type_='foreignkey')
    op.create_foreign_key('documents_reviewed_by_id_fkey', 'documents', 'users', ['reviewed_by_id'], ['id'])
    op.drop_constraint('audit_logs_user_id_fkey', 'audit_logs', type_='foreignkey')
    op.create_foreign_key('audit_logs_user_id_fkey', 'audit_logs', 'users', ['user_id'], ['id'])
