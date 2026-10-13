"""
Crée le premier compte administrateur de façon NON interactive, à partir de
variables d'environnement — pensé pour un déploiement automatisé (Render,
Railway, etc.) où aucune entrée clavier interactive n'est disponible pendant
le build/démarrage.

Variables d'environnement lues :
    ADMIN_USERNAME          — identifiant de connexion (obligatoire pour que
                               le script fasse quoi que ce soit)
    ADMIN_FULL_NAME         — nom complet (obligatoire si ADMIN_USERNAME est
                               défini)
    ADMIN_EMAIL             — optionnel
    ADMIN_INITIAL_PASSWORD  — mot de passe en clair, obligatoire si
                               ADMIN_USERNAME est défini

Comportement volontairement sûr pour être relancé à chaque déploiement :
- Si ADMIN_USERNAME n'est pas défini : ne fait rien, sort silencieusement
  (code 0) — pratique pour l'enchaîner systématiquement après les
  migrations sans risquer de bloquer un déploiement qui n'en a pas besoin.
- Si un compte avec cet identifiant (ou cet e-mail) existe déjà : ne fait
  rien d'autre qu'un message, ne modifie rien, sort en succès (idempotent).

Ces variables ne doivent jamais être laissées en place une fois le compte
créé — supprimez ADMIN_INITIAL_PASSWORD de la configuration de votre
hébergeur après la première exécution réussie.

Usage :
    cd backend && python scripts/create_admin_from_env.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import Role, User  # noqa: E402
from app.schemas.auth import validate_password_strength  # noqa: E402


def run() -> None:
    username = (os.environ.get("ADMIN_USERNAME") or "").strip().lower()
    if not username:
        print("ADMIN_USERNAME non défini — création du compte administrateur ignorée.")
        return

    full_name = (os.environ.get("ADMIN_FULL_NAME") or "").strip()
    email = (os.environ.get("ADMIN_EMAIL") or "").strip().lower() or None
    password = os.environ.get("ADMIN_INITIAL_PASSWORD")

    if not full_name:
        print("ADMIN_USERNAME est défini mais ADMIN_FULL_NAME est manquant — abandon.")
        sys.exit(1)
    if not password:
        print("ADMIN_USERNAME est défini mais ADMIN_INITIAL_PASSWORD est manquant — abandon.")
        sys.exit(1)

    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == username).first():
            print(f"Un compte existe déjà avec l'identifiant « {username} » — rien à faire.")
            return
        if email and db.query(User).filter(User.email == email).first():
            print(f"Un compte existe déjà avec l'e-mail « {email} » — rien à faire.")
            return

        admin_role = db.query(Role).filter(Role.name == Role.ADMIN).first()
        if admin_role is None:
            print("Le rôle ADMIN n'existe pas encore. Lancez d'abord scripts/seed_roles.py.")
            sys.exit(1)

        try:
            validate_password_strength(password)
        except ValueError as exc:
            print(f"Mot de passe refusé : {exc}")
            sys.exit(1)

        admin = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role_id=admin_role.id,
            section_id=None,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"Compte administrateur créé avec succès : {username}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
