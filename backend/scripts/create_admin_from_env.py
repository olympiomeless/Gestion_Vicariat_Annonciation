"""
Crée le premier compte administrateur de façon NON interactive, à partir de
variables d'environnement — pensé pour un déploiement automatisé (Render,
Railway, etc.) où aucune entrée clavier interactive n'est disponible pendant
le build/démarrage.

Variables d'environnement lues :
    ADMIN_USERNAME          — identifiant de connexion (obligatoire pour que
                               le script fasse quoi que ce soit)
    ADMIN_FULL_NAME         — nom complet (requis seulement si le compte
                               n'existe pas encore)
    ADMIN_EMAIL             — optionnel
    ADMIN_INITIAL_PASSWORD  — mot de passe en clair (requis seulement si le
                               compte n'existe pas encore)

Comportement volontairement sûr pour être relancé à CHAQUE démarrage du
serveur, indéfiniment, sans jamais bloquer le déploiement :
- Si ADMIN_USERNAME n'est pas défini : ne fait rien, sort silencieusement
  (code 0).
- Si un compte avec cet identifiant (ou cet e-mail) existe déjà : ne fait
  rien d'autre qu'un message, ne modifie rien, sort en succès (idempotent)
  — et ce, MÊME SI ADMIN_FULL_NAME / ADMIN_INITIAL_PASSWORD ont depuis été
  retirés de la configuration. L'existence du compte est toujours vérifiée
  avant d'exiger ces deux variables.
- Seule la toute première exécution (compte pas encore créé) a besoin de
  ADMIN_FULL_NAME et ADMIN_INITIAL_PASSWORD.

Une fois le compte créé, vous pouvez retirer ADMIN_INITIAL_PASSWORD (et
ADMIN_FULL_NAME) de la configuration de votre hébergeur si vous voulez —
ce n'est plus nécessaire. Laisser ADMIN_USERNAME en place ne pose aucun
problème, le script continuera de ne rien faire à chaque redémarrage.

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

    email = (os.environ.get("ADMIN_EMAIL") or "").strip().lower() or None

    db = SessionLocal()
    try:
        # On vérifie D'ABORD si le compte existe déjà, avant d'exiger quoi
        # que ce soit d'autre (nom complet, mot de passe) — sinon, dès que
        # ADMIN_INITIAL_PASSWORD est retiré après la création initiale (ce
        # qu'on recommande), ce script échouerait à chaque redémarrage
        # suivant et bloquerait tout le démarrage du serveur (la commande de
        # démarrage l'enchaîne avec `&&` avant uvicorn).
        if db.query(User).filter(User.username == username).first():
            print(f"Un compte existe déjà avec l'identifiant « {username} » — rien à faire.")
            return
        if email and db.query(User).filter(User.email == email).first():
            print(f"Un compte existe déjà avec l'e-mail « {email} » — rien à faire.")
            return

        full_name = (os.environ.get("ADMIN_FULL_NAME") or "").strip()
        password = os.environ.get("ADMIN_INITIAL_PASSWORD")

        if not full_name:
            print("Compte à créer mais ADMIN_FULL_NAME est manquant — abandon.")
            sys.exit(1)
        if not password:
            print("Compte à créer mais ADMIN_INITIAL_PASSWORD est manquant — abandon.")
            sys.exit(1)

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
