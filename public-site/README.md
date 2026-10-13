# Site public — Vicariat de l'Annonciation

`index.html` est le site vitrine (accueil, mouvement, sections, programme,
bureau, galerie, actualités, contact). Il garde exactement le même design,
la même structure et le même contenu que l'ancien `site_static.html`, mais
lit maintenant ses données depuis l'API de la nouvelle plateforme
(`../backend`) au lieu des feuilles Google Sheets.

## Comment ça marche

Au chargement de la page, `syncFromApi()` (dans le script en bas du fichier)
interroge ces endpoints, qui ne nécessitent aucune connexion :

- `GET /api/v1/public/sections`
- `GET /api/v1/public/bureau`
- `GET /api/v1/public/effectifs`
- `GET /api/v1/public/programme`
- `GET /api/v1/public/actualites`
- `GET /api/v1/public/gallery` (+ `GET /api/v1/public/gallery/{id}/file` pour chaque photo)

Chacun de ces appels ne retourne QUE du contenu déjà validé et publié
(statut `PUBLIE`) — jamais un brouillon, une soumission en attente ou un
contenu refusé, quelle que soit la section qui l'a proposé (voir
`backend/app/api/v1/public.py`).

Si l'API est injoignable (backend éteint, hors ligne, erreur réseau), chaque
appel échoue silencieusement et la page garde le contenu déjà intégré dans le
fichier HTML au moment de sa dernière publication — jamais une section vide
ou une erreur visible pour le visiteur.

## Configurer l'URL de l'API

Par défaut le site pointe vers `http://localhost:8000/api/v1` (utile en
développement local). Une fois le backend déployé (Render/Railway...),
deux façons de changer l'URL :

1. Éditer directement la ligne `var API_BASE_URL = ...` dans le script.
2. Sans toucher au fichier : ajouter, AVANT ce script, dans l'entête de la
   page publiée :
   ```html
   <script>window.VICARIAT_API_BASE_URL = "https://votre-backend.example.com/api/v1";</script>
   ```

## CORS

Le backend n'autorise que les origines listées dans la variable d'environnement
`CORS_ORIGINS` (voir `backend/.env`). Une fois ce site déployé sur son domaine
définitif, ce domaine doit être ajouté à `CORS_ORIGINS` sur le serveur du
backend, sinon le navigateur bloquera les appels à l'API (le site restera
visible grâce au contenu de secours intégré, mais ne se mettra plus à jour).

## Limite connue

Les images de marque (photo d'accueil, logo) ne sont pas encore pilotables
depuis l'administration — il n'existe pas encore de table dédiée côté
backend pour ces réglages. Elles restent celles intégrées à cette page tant
que cette fonctionnalité n'a pas été ajoutée à une étape ultérieure.
