# Vicariat de l'Annonciation — Backend

API de la plateforme de gestion du Vicariat de l'Annonciation (Mouvement
Cœurs Vaillants-Âmes Vaillantes, Diocèse de Yopougon). FastAPI + PostgreSQL,
avec authentification réelle, cloisonnement strict entre sections appliqué
côté serveur, upload et validation de documents/actualités/programme/galerie,
et une API publique pour le site vitrine.

## Stack

- **Python 3.11**, **FastAPI**, **Uvicorn**
- **PostgreSQL 16**, **SQLAlchemy 2.0** (ORM typé), **Alembic** (migrations versionnées)
- **argon2** (hachage des mots de passe), **JWT** (access tokens) + **jetons opaques hachés** (refresh tokens, en cookie httpOnly)
- **slowapi** (rate limiting sur l'authentification)
- **pytest** (92 tests automatisés : authentification, permissions, upload/validation de documents, actualités, programme, galerie, bureau/effectifs, migration, API publique)

## Installation locale

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Éditez .env : DATABASE_URL, JWT_SECRET (générez avec la commande indiquée dans le fichier), etc.

# Créez les bases PostgreSQL (adapter les identifiants à votre .env) :
sudo -u postgres psql -c "CREATE ROLE vicariat WITH LOGIN PASSWORD 'changeme';"
sudo -u postgres psql -c "CREATE DATABASE vicariat OWNER vicariat;"
sudo -u postgres psql -c "CREATE DATABASE vicariat_test OWNER vicariat;"  # pour les tests

# Appliquez les migrations
alembic upgrade head

# Données de référence
python scripts/seed_roles.py
python scripts/seed_document_categories.py

# Premier compte administrateur (interactif — mot de passe jamais en dur dans le code)
python scripts/create_admin.py

# Import des données de l'ancien site (bureau, sections, programme, actualités —
# voir migration_data/*.csv). Nécessite qu'un admin existe déjà. Idempotent :
# peut être relancé sans dupliquer les données déjà importées.
python scripts/migrate_existing_site_data.py

# Lancer le serveur
uvicorn app.main:app --reload
```

L'API est alors disponible sur `http://localhost:8000`, avec une
documentation interactive sur `http://localhost:8000/docs`.

## Tests

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

Les tests utilisent une base PostgreSQL séparée (`vicariat_test`, voir
`tests/conftest.py`), recréée à chaque session de tests et nettoyée entre
chaque test — ils ne touchent jamais à la base de développement.

## Architecture

```
app/
  core/        config, connexion DB, sécurité (hachage, JWT), rate limiting
  models/      modèles SQLAlchemy (une table = un fichier)
  schemas/     schémas Pydantic (validation des entrées/sorties de l'API)
  services/    logique métier réutilisable (auth, audit, notifications, validation de fichiers)
  storage/     abstraction de stockage de fichiers (disque local aujourd'hui ;
               interface prête pour S3/Cloudinary/Supabase plus tard sans
               changer les routes qui l'utilisent)
  api/v1/      les routes de l'API, une par domaine fonctionnel
alembic/       migrations de schéma versionnées
scripts/       tâches ponctuelles (créer l'admin, semer les rôles/catégories, migrer l'ancien site)
migration_data/  CSV sources de l'ancien site (bureau, sections, programme, actualités, effectifs)
tests/         suite de tests automatisés
```

### Principe de sécurité central

Toute vérification de permission se fait **côté serveur**, jamais seulement
dans l'interface : chaque route re-dérive le rôle et la section de
l'utilisateur depuis son jeton JWT (jamais depuis un champ envoyé par le
client), et une section ne peut jamais lire, modifier ou supprimer une
ressource qui ne lui appartient pas — vérifié explicitement par des tests
dédiés pour les documents, les actualités, le programme et la galerie
(`test_section_a_cannot_*`, `test_*_ignores_spoofed_section_id`).

### API publique

`GET /api/v1/public/*` (sections, bureau, effectifs, programme, actualités,
galerie, documents) ne nécessite aucune authentification et ne renvoie
**jamais** un contenu qui n'est pas au statut `PUBLIE` — c'est ce que
consomme le site vitrine (`../public-site/index.html`).

## Déploiement (Render ou Railway)

1. **Base de données** : créez un service PostgreSQL managé sur la
   plateforme choisie ; récupérez son `DATABASE_URL`.
2. **Service web** : déployez ce dossier `backend/` comme service Python.
   - Commande de build : `pip install -r requirements.txt`
   - Commande de démarrage : `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. **Variables d'environnement** à définir sur la plateforme (jamais dans le
   code ni committées) : `DATABASE_URL`, `JWT_SECRET` (valeur aléatoire
   longue, différente de celle de développement), `ENVIRONMENT=production`,
   `CORS_ORIGINS` (le ou les domaines réels du site public et de l'interface
   d'administration), `STORAGE_BACKEND=local`, `STORAGE_LOCAL_PATH` (un
   disque persistant si la plateforme le permet — sur un plan sans disque
   persistant, les fichiers uploadés seraient perdus à chaque redéploiement :
   prévoir de migrer `STORAGE_BACKEND` vers S3/Cloudinary/Supabase Storage
   avant la mise en production réelle), `MAX_UPLOAD_SIZE_MB`, `ADMIN_EMAIL`.
4. **Après le premier déploiement**, exécutez une fois, via la console/le
   shell de la plateforme :
   ```bash
   alembic upgrade head
   python scripts/seed_roles.py
   python scripts/seed_document_categories.py
   python scripts/create_admin.py
   python scripts/migrate_existing_site_data.py
   ```
5. **CORS** : ajoutez le domaine réel du site public (et celui de
   l'interface d'administration, une fois construite) à `CORS_ORIGINS`,
   sinon le navigateur bloquera les appels à l'API depuis ces sites.

## État d'avancement

Backend, API et interfaces web entièrement fonctionnels et testés :
authentification, rôles, documents, actualités, programme, galerie, bureau,
effectifs, tableaux de bord, notifications, journal d'audit, migration des
données de l'ancien site, API publique (101 tests automatisés, tous
au vert). L'interface web d'administration et d'espace section est
construite dans `../admin-app` (React + Vite + TypeScript) — voir son
README pour la configuration et le démarrage. Chaque écran (connexion,
tableaux de bord, dépôt de fichiers avec barre de progression, validation
des documents/actualités/activités/photos, gestion des utilisateurs et des
sections, journal d'audit) appelle réellement l'API : aucune donnée
simulée, tout est persistant après actualisation de la page.

Reste à faire pour une mise en production réelle : déployer le backend et
la base PostgreSQL (Render/Railway, voir plus haut), déployer `admin-app`
(build statique) et le site public sur un hébergeur, configurer les noms de
domaine réels dans `CORS_ORIGINS`, créer le premier compte administrateur
avec `python scripts/create_admin.py`, puis exécuter la migration des
données de l'ancien site une seule fois avec
`python scripts/migrate_existing_site_data.py`.
