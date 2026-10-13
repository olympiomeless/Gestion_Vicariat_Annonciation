# Guide de lancement — Plateforme Vicariat de l'Annonciation

Ce guide explique comment installer et lancer, de zéro, les trois
composants de la plateforme : l'API backend, l'interface d'administration,
et le site public. Il regroupe et complète les README présents dans
`backend/`, `admin-app/` et `public-site/`, avec les points qui posent le
plus souvent problème au premier lancement.

## 1. Vue d'ensemble

| Composant | Dossier | Techno | Rôle |
|---|---|---|---|
| API | `backend/` | FastAPI + PostgreSQL | Cœur de la plateforme : comptes, sections, documents, programme, bureau, courriers, etc. |
| Interface d'administration | `admin-app/` | React + Vite + TypeScript | Espace `/admin` (administrateur) et espace `/section` (chaque section) |
| Site public | `public-site/` | HTML statique | Site vitrine (`index.html`) consultable par tout le monde, sans connexion |

L'API doit tourner en premier : les deux autres composants en dépendent.

## 2. Prérequis

- **Python 3.11** — exactement cette version, pas une version plus récente.
  Sur une machine où `python3` pointe vers Python 3.13 (cas fréquent sur une
  installation récente), l'installation des dépendances échoue au moment de
  compiler `psycopg2-binary`, car ce paquet n'a pas encore de version
  précompilée pour 3.13. Vérifiez avec `python3.11 --version` ; si cette
  commande n'existe pas, installez Python 3.11 séparément avant de
  continuer (`sudo apt install python3.11 python3.11-venv` sous
  Debian/Ubuntu, ou l'équivalent de votre système).
- **PostgreSQL 16** (ou une version proche), installé et démarré localement.
- **Node.js 20+** et npm, pour l'interface d'administration.
- Un terminal (Git Bash ou WSL sous Windows ; le reste de ce guide suppose
  des commandes Unix).

## 3. Lancer l'API (backend)

```bash
cd backend
py -3.12 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

### 3.1 Configuration

```bash
cp .env.example .env
```

Éditez `.env` et renseignez au minimum :

- `DATABASE_URL` — ex. `postgresql+psycopg2://vicariat:changeme@localhost:5432/vicariat`
- `JWT_SECRET` — une valeur aléatoire longue, générée avec :
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(64))"
  ```

Les autres valeurs (`STORAGE_LOCAL_PATH`, `CORS_ORIGINS`, etc.) peuvent
rester à leur valeur par défaut en développement local.

### 3.2 Base de données

```bash
sudo -u postgres psql -c "CREATE ROLE vicariat WITH LOGIN PASSWORD 'changeme';"
sudo -u postgres psql -c "CREATE DATABASE vicariat OWNER vicariat;"
sudo -u postgres psql -c "CREATE DATABASE vicariat_test OWNER vicariat;"   # pour les tests automatisés
```

Adaptez le nom d'utilisateur/mot de passe à ce que vous avez mis dans
`DATABASE_URL`.

### 3.3 Migrations et données de référence

```bash
alembic upgrade head                        # crée toutes les tables
python scripts/seed_roles.py                # rôles ADMIN / SECTION
python scripts/seed_document_categories.py  # catégories de documents par défaut
python scripts/create_admin.py              # crée le premier compte administrateur (interactif)
```

`create_admin.py` demande un identifiant de connexion et un mot de passe —
notez-les, c'est le compte qui permettra de se connecter à l'espace
administration la première fois.

Si vous reprenez les données de l'ancien site (bureau, sections, programme,
actualités), lancez ensuite, une fois l'admin créé :

```bash
python scripts/migrate_existing_site_data.py
```

Ce script est idempotent : le relancer ne duplique pas les données déjà
importées.

### 3.4 Démarrer le serveur

```bash
uvicorn app.main:app --reload
```

L'API est disponible sur `http://localhost:8000`, avec une documentation
interactive sur `http://localhost:8000/docs`.

### 3.5 Vérifier que tout fonctionne

```bash
python -m pytest tests/ -v
```

La suite de tests automatisés (authentification, permissions, documents,
programme, bureau, bureau de section, courriers, etc.) doit passer
entièrement — c'est le meilleur signal que l'installation est correcte
avant de passer à la suite.

## 4. Lancer l'interface d'administration

Dans un autre terminal, avec l'API déjà lancée :

```bash
cd admin-app
cp .env.example .env.local     # VITE_API_BASE_URL=http://localhost:8000/api/v1 par défaut
npm install
npm run dev
```

L'interface est servie sur `http://localhost:5173`. Connectez-vous avec le
compte créé par `create_admin.py` (espace administration), ou avec un
compte de section (voir § 6).

Pour un build de production (dossier `dist/` statique à déployer) :

```bash
npm run build
```

Pensez à définir `VITE_API_BASE_URL` vers l'URL de l'API en production
**avant** ce build : Vite intègre cette valeur au moment de la compilation,
pas au moment de l'exécution.

## 5. Lancer le site public

`public-site/index.html` et `public-site/portail.html` sont de simples
fichiers HTML statiques : aucune installation n'est nécessaire, ils peuvent
être ouverts directement dans un navigateur ou servis par n'importe quel
serveur de fichiers statiques, par exemple :

```bash
cd public-site
python3 -m http.server 8080
```

Par défaut, le site interroge l'API sur `http://localhost:8000/api/v1`. Pour
pointer vers une autre URL (par exemple un backend déployé), ajoutez avant
le script de la page :

```html
<script>window.VICARIAT_API_BASE_URL = "https://votre-backend.example.com/api/v1";</script>
```

Si l'API est injoignable, le site garde le contenu déjà intégré au fichier
lors de sa dernière publication — jamais de page vide pour le visiteur.

## 6. Comptes et accès

Il existe deux rôles :

- **ADMIN** — accès complet, espace `/admin`. Le premier compte est créé
  par `scripts/create_admin.py` (§ 3.3).
- **SECTION** — accès limité à sa propre section, espace `/section`.

Un compte SECTION se crée de deux façons depuis l'espace administration :

1. **À la création de la section** (recommandé) — dans « Sections » → « +
   Nouvelle section », en renseignant le champ optionnel « Identifiant de
   connexion de la section ». Un mot de passe par défaut est alors généré
   automatiquement et affiché **une seule fois**, dans une fenêtre dédiée —
   notez-le ou transmettez-le immédiatement à la section, qui pourra le
   changer dès sa première connexion (bouton « Mon compte »).
2. **Séparément**, depuis « Utilisateurs » → « + Nouvel utilisateur », en
   choisissant le rôle « Section » et en définissant vous-même
   l'identifiant et le mot de passe initial — utile pour créer un compte
   sur une section déjà existante.

La connexion se fait par **identifiant**, pas par e-mail (l'e-mail est
optionnel, utilisé uniquement pour « mot de passe oublié » quand il est
renseigné).

## 7. Tour des fonctionnalités principales

Côté administration (`/admin`) :

- **Documents, Actualités, Programme, Galerie** — modération de ce que
  chaque section soumet (publication ou refus avec motif).
- **Bureau** — bureau du Vicariat, géré uniquement par l'administrateur.
- **Bureaux de sections** — chaque section propose les membres de son
  propre bureau ; l'administrateur valide avant publication.
- **Courriers** — messages et demandes de fichiers (ex. attestations de
  camp) envoyés par les sections ; l'administrateur répond avec une note
  et/ou un fichier déposé.
- **Utilisateurs, Sections, Effectifs, Le mouvement, Journal d'audit**.

Côté section (`/section`) : les mêmes espaces de dépôt, limités à sa propre
section, plus « Courriers » pour écrire au Bureau du Vicariat et « Mon
compte » pour changer son mot de passe.

## 8. Dépannage

**`la colonne users.username n'existe pas` (ou erreur similaire au
démarrage)** — les migrations n'ont pas été appliquées sur cette base.
Lancez `alembic upgrade head` (§ 3.3).

**Échec de compilation de `psycopg2-binary` pendant `pip install`** —
vous utilisez probablement Python 3.13 ou plus récent au lieu de 3.11.
Recréez l'environnement virtuel avec `python3.11 -m venv .venv` (§ 3).

**`429 Too Many Requests` sur la connexion** — la connexion est limitée
à 5 tentatives par minute par mesure de sécurité. Attendez une minute et
réessayez ; ce n'est pas un bug.

**Le site public ne se met pas à jour après un déploiement** — vérifiez
que le domaine du site a bien été ajouté à `CORS_ORIGINS` côté backend
(voir `public-site/README.md`).

## 9. Déploiement en production

Ce guide couvre le lancement en local. Pour le déploiement (Render,
Railway, Netlify, etc.), voir les sections dédiées de `backend/README.md`
et `admin-app/README.md`, qui détaillent les variables d'environnement à
définir côté hébergeur.
