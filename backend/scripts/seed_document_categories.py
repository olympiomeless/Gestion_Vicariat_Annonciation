"""
Crée les catégories de documents prédéfinies (point 7 du cahier des charges).
Idempotent. L'administrateur peut ensuite en ajouter d'autres depuis l'API
(POST /api/v1/documents/categories) ; celles-ci sont marquées `is_system` et
ne peuvent pas être supprimées.

Usage :
    cd backend && source .venv/bin/activate && python scripts/seed_document_categories.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.models.document import DocumentCategory  # noqa: E402

DEFAULT_CATEGORIES = [
    "Rapport",
    "Compte rendu",
    "Programme",
    "Formation",
    "Administration",
    "Communication",
    "Photos",
    "Affiches",
    "Documents officiels",
    "Autres",
]


def run() -> None:
    db = SessionLocal()
    try:
        for name in DEFAULT_CATEGORIES:
            existing = db.query(DocumentCategory).filter(DocumentCategory.name == name).first()
            if existing is None:
                db.add(DocumentCategory(name=name, is_system=True))
                print(f"Catégorie créée : {name}")
            else:
                print(f"Catégorie déjà présente : {name}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
