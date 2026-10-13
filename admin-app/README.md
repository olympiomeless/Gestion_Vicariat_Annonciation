# Vicariat de l'Annonciation — Interface d'administration

Application React (Vite + TypeScript) qui fournit les deux espaces de
travail de la plateforme :

- **Espace administration** (`/admin/*`) — réservé au rôle `ADMIN` : tableau
  de bord global, gestion des utilisateurs, des sections, du bureau, des
  effectifs, modération de tous les documents / actualités / activités /
  photos de toutes les sections, journal d'audit.
- **Espace section** (`/section/*`) — réservé au rôle `SECTION` : tableau de
  bord de la section, dépôt et suivi de ses propres documents, actualités,
  activités de programme et photos.

Chaque page appelle réellement l'API du backend (`../backend`) : il n'y a
aucune donnée simulée, aucun bouton qui ne fait rien. Tout ce qui est créé,
modifié, validé ou supprimé dans l'interface est persistant côté serveur et
reste visible après actualisation de la page.

## Prérequis

- Node.js 20+
- Le backend FastAPI doit tourner (voir `../backend/README.md`) et exposer
  son API sur l'URL indiquée dans `.env.local`.

## Configuration

Copier `.env.example` vers `.env.local` et ajuster si besoin :

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

En production, cette variable doit pointer vers l'URL publique de l'API
déployée (voir le backend README pour Render/Railway), et le domaine de ce
frontend doit être ajouté à `CORS_ORIGINS` côté backend.

## Démarrage en développement

```bash
npm install
npm run dev
```

L'application est servie sur `http://localhost:5173`. Se connecter avec un
compte créé via `python scripts/create_admin.py` côté backend (rôle ADMIN),
ou avec un compte de section créé depuis l'espace administration une fois
connecté.

## Build de production

```bash
npm run build
```

Génère un dossier `dist/` statique, déployable sur n'importe quel
hébergeur de fichiers statiques (Netlify, Vercel, Render Static Site, etc.).
Penser à définir `VITE_API_BASE_URL` au moment du build (variable
d'environnement de la plateforme d'hébergement), car Vite l'intègre au
bundle à la compilation.

## Architecture du code

- `src/api/client.ts` — client HTTP centralisé : ajoute le jeton d'accès,
  rafraîchit automatiquement la session via le cookie httpOnly de refresh
  token en cas de 401, gère l'upload avec barre de progression réelle
  (`XMLHttpRequest`) et le téléchargement de fichiers protégés (blob +
  lien temporaire, puisque les jetons ne peuvent pas être passés dans un
  simple `<a href>`).
- `src/api/resources.ts` — une fonction par endpoint du backend, typée.
- `src/api/types.ts` — types TypeScript alignés sur les schémas Pydantic
  du backend.
- `src/auth/` — contexte d'authentification (`AuthContext`) et garde de
  route par rôle (`ProtectedRoute`), avec redirection automatique vers le
  bon espace selon le rôle du compte connecté.
- `src/components/` — briques réutilisables : notifications toast,
  confirmation modale pour toute action destructive (jamais de
  `window.confirm`), saisie de motif pour les refus (jamais de
  `window.prompt`), badges de statut, pagination, états de chargement.
- `src/layout/` — les deux coquilles de navigation (`AdminLayout`,
  `SectionLayout`).
- `src/pages/shared/` — pages partagées entre les deux espaces
  (Documents, Actualités, Programme, Galerie, Notifications), dont le
  comportement s'adapte via une prop `scope: 'admin' | 'section'` — la
  visibilité et les droits réels restent de toute façon appliqués côté
  serveur, jamais seulement dans l'interface.
- `src/pages/admin/` et `src/pages/section/` — pages propres à chaque
  espace (tableaux de bord, utilisateurs, sections, bureau, effectifs,
  journal d'audit).

## Sécurité côté client

L'interface respecte scrupuleusement les décisions du serveur : elle
n'affiche que les actions autorisées, mais **toute vérification de droits
est de toute façon refaite côté API** (voir `backend/README.md` et les 101
tests du backend). Un contournement de l'interface (appel direct à l'API)
ne permettrait donc jamais à une section d'agir sur les ressources d'une
autre section.
