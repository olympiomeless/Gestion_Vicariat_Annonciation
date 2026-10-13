"""add mouvement content

Revision ID: 9b4d6af7cd6d
Revises: 9973a557c7bc
Create Date: 2026-09-30 10:00:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b4d6af7cd6d'
down_revision: Union[str, None] = '9973a557c7bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


mouvement_content = sa.table(
    'mouvement_content',
    sa.column('id', sa.UUID()),
    sa.column('intro_title', sa.Text()),
    sa.column('intro_paragraph_1', sa.Text()),
    sa.column('intro_paragraph_2', sa.Text()),
    sa.column('intro_paragraph_3', sa.Text()),
    sa.column('theme_annee_label', sa.Text()),
    sa.column('theme_annee_quote', sa.Text()),
    sa.column('limite_nord', sa.Text()),
    sa.column('limite_sud', sa.Text()),
    sa.column('limite_ouest', sa.Text()),
    sa.column('tutelle', sa.Text()),
    sa.column('aumonier_name', sa.Text()),
    sa.column('aumonier_role', sa.Text()),
    sa.column('vicaire_text', sa.Text()),
)


def upgrade() -> None:
    op.create_table(
        'mouvement_content',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('intro_title', sa.Text(), nullable=False),
        sa.Column('intro_paragraph_1', sa.Text(), nullable=False),
        sa.Column('intro_paragraph_2', sa.Text(), nullable=False),
        sa.Column('intro_paragraph_3', sa.Text(), nullable=False),
        sa.Column('theme_annee_label', sa.Text(), nullable=False),
        sa.Column('theme_annee_quote', sa.Text(), nullable=False),
        sa.Column('limite_nord', sa.Text(), nullable=False),
        sa.Column('limite_sud', sa.Text(), nullable=False),
        sa.Column('limite_ouest', sa.Text(), nullable=False),
        sa.Column('tutelle', sa.Text(), nullable=False),
        sa.Column('aumonier_name', sa.Text(), nullable=False),
        sa.Column('aumonier_role', sa.Text(), nullable=False),
        sa.Column('vicaire_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # Une seule ligne, initialisée avec le contenu d'origine du site (celui
    # qui était jusqu'ici codé en dur dans public-site/index.html) : rien ne
    # doit disparaître du site public avant la première modification par
    # l'administrateur via l'espace d'administration.
    op.bulk_insert(
        mouvement_content,
        [
            {
                'id': uuid.uuid4(),
                'intro_title': "Un vicariat, une identité, une mission",
                'intro_paragraph_1': (
                    "Au cœur du Mouvement d'Action Catholique pour l'Enfance Cœurs Vaillants – "
                    "Âmes Vaillantes (CV-AV) du diocèse de Yopougon, le Vicariat Forain de "
                    "l'Annonciation occupe une place particulière parmi les treize vicariats qui "
                    "font vivre la mission du mouvement auprès des enfants et des jeunes."
                ),
                'intro_paragraph_2': (
                    "Plus qu'une simple circonscription administrative, notre vicariat est un "
                    "espace de communion, de formation, de service et d'engagement, où des "
                    "accompagnateurs mettent leur temps et leurs talents au service de "
                    "l'épanouissement spirituel, humain et social des enfants qui leur sont "
                    "confiés — sous la tutelle du Bureau Diocésain des CV-AV de Yopougon."
                ),
                'intro_paragraph_3': (
                    "La force du vicariat réside dans la complémentarité de ses cinq sections, "
                    "classées ci-dessous par ordre d'ancienneté : chacune apporte sa pierre à un "
                    "même édifice, chaque maillon essentiel à la solidité de l'ensemble."
                ),
                'theme_annee_label': "Thème de l'année pastorale 2025-2026 — Diocèse de Yopougon",
                'theme_annee_quote': (
                    "Avec la Vierge Marie, par la prière du chapelet, prions avec confiance pour "
                    "la paix dans nos familles, dans nos villages et dans notre pays."
                ),
                'limite_nord': "Vicariat de Saint-André",
                'limite_sud': "Vicariat de Saint-Vincent-de-Paul",
                'limite_ouest': "Vicariat de Saint-Pierre",
                'tutelle': "Bureau Diocésain CV-AV Yopougon",
                'aumonier_name': "Abbé Kablan Georges",
                'aumonier_role': "Aumônier du Vicariat de l'Annonciation (Saint-Marc)",
                'vicaire_text': (
                    "Le mouvement CV-AV du diocèse de Yopougon bénéficie également de "
                    "l'accompagnement du Père Paul-Arnaud Yao, Vicaire à la paroisse Sainte "
                    "Jeanne d'Arc."
                ),
            }
        ],
    )


def downgrade() -> None:
    op.drop_table('mouvement_content')
