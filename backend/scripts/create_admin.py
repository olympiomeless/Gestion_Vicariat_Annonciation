"""
Crée le premier compte administrateur, de façon interactive et sécurisée.

Le mot de passe n'est JAMAIS passé en argument de ligne de commande (il
resterait visible dans l'historique du shell / la liste des process) : il est
soit saisi de façon interactive (masqué), soit lu depuis la variable
d'environnement ADMIN_INITIAL_PASSWORD si elle est déjà présente dans le shell
courant (utile pour un déploiement automatisé, à condition de ne jamais la
committer dans un fichier .env versionné).

Usage :
    cd backend && source .venv/bin/activate && python scripts/create_admin.py
"""
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import Role, User  # noqa: E402
from app.schemas.auth import validate_password_strength  # noqa: E402


def run() -> None:
    db = SessionLocal()
    try:
        admin_role = db.query(Role).filter(Role.name == Role.ADMIN).first()
        if admin_role is None:
            print("Le rôle ADMIN n'existe pas encore. Lancez d'abord : python scripts/seed_roles.py")
            sys.exit(1)

        username = input("Identifiant de connexion (ex. « admin ») : ").strip().lower()
        if not username:
            print("L'identifiant est requis.")
            sys.exit(1)
        if db.query(User).filter(User.username == username).first():
            print(f"Un compte existe déjà avec l'identifiant {username}.")
            sys.exit(1)

        email = input("E-mail de l'administrateur (optionnel, Entrée pour ignorer) : ").strip().lower()
        if email:
            if "@" not in email:
                print("Adresse e-mail invalide.")
                sys.exit(1)
            if db.query(User).filter(User.email == email).first():
                print(f"Un compte existe déjà avec l'e-mail {email}.")
                sys.exit(1)
        else:
            email = None

        full_name = input("Nom complet : ").strip()
        if not full_name:
            print("Le nom complet est requis.")
            sys.exit(1)

        password = os.environ.get("ADMIN_INITIAL_PASSWORD")
        if password:
            print("Mot de passe lu depuis ADMIN_INITIAL_PASSWORD.")
        else:
            password = getpass.getpass("Mot de passe (au moins 10 caractères, majuscule+minuscule+chiffre) : ")
            confirm = getpass.getpass("Confirmez le mot de passe : ")
            if password != confirm:
                print("Les deux mots de passe ne correspondent pas.")
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
