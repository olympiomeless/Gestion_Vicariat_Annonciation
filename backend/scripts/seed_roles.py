"""
Crée les rôles de base (ADMIN, SECTION) s'ils n'existent pas encore.
Idempotent : peut être relancé sans risque.

Usage :
    cd backend && source .venv/bin/activate && python scripts/seed_roles.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.models.user import Role  # noqa: E402


def run() -> None:
    db = SessionLocal()
    try:
        for name, description in [
            (Role.ADMIN, "Bureau du Vicariat — accès global à la plateforme"),
            (Role.SECTION, "Responsable d'une section — accès limité à sa section"),
        ]:
            existing = db.query(Role).filter(Role.name == name).first()
            if existing is None:
                db.add(Role(name=name, description=description))
                print(f"Rôle créé : {name}")
            else:
                print(f"Rôle déjà présent : {name}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
