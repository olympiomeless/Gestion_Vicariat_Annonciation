"""
Migration des données de l'ancien site (fiches Google Sheets utilisées par le
site statique `site_static.html`) vers la nouvelle base PostgreSQL.

Sources (étape 1 du cahier des charges : analyse du site existant) :
    migration_data/sections.csv     -> table `sections`         (mise à jour, jamais de suppression)
    migration_data/bureau.csv       -> table `bureau_members`
    migration_data/effectifs.csv    -> table `effectif_categories`
    migration_data/programme.csv    -> table `programmes`       (importées déjà PUBLIE)
    migration_data/actualites.csv   -> table `actualites`       (importées déjà PUBLIE)

Principes :
    - IDEMPOTENT : peut être relancé sans dupliquer les données déjà migrées.
    - NON DESTRUCTIF : ne supprime jamais une ligne existante ; une section
      déjà présente est mise à jour, jamais recréée ni effacée.
    - Le contenu importé (programme, actualités) est historique et déjà
      public sur l'ancien site : il est inséré directement au statut PUBLIE,
      sans repasser par le circuit de validation.
    - Nécessite qu'un compte ADMIN existe déjà (voir scripts/create_admin.py)
      : cet admin devient l'auteur technique du contenu importé.

Usage :
    cd backend && source .venv/bin/activate && python scripts/migrate_existing_site_data.py
"""
import csv
import re
import sys
from datetime import date
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal  # noqa: E402
from app.models.actualite import Actualite, ActualiteStatus  # noqa: E402
from app.models.bureau import BureauMember  # noqa: E402
from app.models.document import DocumentStatus  # noqa: E402
from app.models.effectif import EffectifCategorie  # noqa: E402
from app.models.programme import ProgrammeActivite  # noqa: E402
from app.models.section import Section  # noqa: E402
from app.models.user import Role, User  # noqa: E402

DATA_DIR = BACKEND_ROOT / "migration_data"

MOIS_FR = {
    "janvier": 1, "janv": 1, "février": 2, "fevrier": 2, "févr": 2, "fevr": 2, "mars": 3,
    "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "août": 8, "aout": 8,
    "septembre": 9, "sept": 9, "octobre": 10, "oct": 10, "novembre": 11, "nov": 11,
    "décembre": 12, "decembre": 12, "déc": 12, "dec": 12,
}

# Correspondance slug (ancien système, identifiant "id interne") -> nom
# affiché des sections, pour les actualités marquées "vicariat" (générales,
# non rattachées à une section précise).
VICARIAT_WIDE_SLUG = "vicariat"


def _read_csv(filename: str) -> list[dict]:
    path = DATA_DIR / filename
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _parse_french_date(raw: str) -> date:
    """
    Parse au mieux une date en français, potentiellement imprécise ou en
    intervalle ("26 au 28 décembre 2025", "Avril 2026", "Mai — Juin 2026",
    "31 juillet au 12 août 2026"). Retient systématiquement la PREMIÈRE date
    de l'intervalle ; le texte original est conservé tel quel dans la
    description pour ne perdre aucune information (voir `import_programme`).
    """
    text = raw.strip().lower().replace("1er", "1")
    year_match = re.search(r"(20\d{2})", text)
    year = int(year_match.group(1)) if year_match else date.today().year

    month = None
    for name, num in MOIS_FR.items():
        if re.search(rf"\b{name}\b", text):
            month = num
            break
    if month is None:
        # Aucun mois reconnu (ne devrait pas arriver avec les données fournies) :
        # on retombe sur le 1er janvier de l'année trouvée plutôt que d'échouer.
        return date(year, 1, 1)

    day_match = re.search(r"\b(\d{1,2})\b", text)
    day = int(day_match.group(1)) if day_match else 1
    day = min(max(day, 1), 28)  # défense simple contre un jour invalide pour le mois
    return date(year, month, day)


def _get_migration_author(db) -> User:
    admin = db.query(User).join(Role).filter(Role.name == Role.ADMIN).order_by(User.created_at.asc()).first()
    if admin is None:
        raise RuntimeError(
            "Aucun compte administrateur trouvé. Créez-en un d'abord avec "
            "`python scripts/create_admin.py`, puis relancez cette migration."
        )
    return admin


def import_sections(db) -> dict[str, Section]:
    rows = _read_csv("sections.csv")
    by_slug: dict[str, Section] = {}
    for i, row in enumerate(rows):
        slug = row["id (ne pas modifier)"].strip()
        section = db.query(Section).filter(Section.slug == slug).first()
        if section is None:
            section = Section(slug=slug, name=row["nom"].strip(), display_order=i)
            db.add(section)
            print(f"  + Section créée : {slug} ({row['nom']})")
        else:
            print(f"  = Section déjà présente, mise à jour : {slug}")

        section.name = row["nom"].strip()
        section.badge_label = row["badge"].strip() or None
        section.quartier = row["quartier"].strip() or None
        section.responsable_name = row["responsable"].strip() or None
        try:
            section.effectif_total = int(row["effectif"].strip())
        except (KeyError, ValueError):
            pass
        by_slug[slug] = section
    db.commit()
    for section in by_slug.values():
        db.refresh(section)
    return by_slug


def import_bureau(db) -> None:
    rows = _read_csv("bureau.csv")
    existing_pairs = {(m.full_name, m.role_title) for m in db.query(BureauMember).all()}
    created = 0
    for i, row in enumerate(rows):
        full_name = row["nom"].strip()
        role_title = row["role"].strip()
        if (full_name, role_title) in existing_pairs:
            continue  # déjà migré : on ne duplique jamais un membre du bureau
        member = BureauMember(
            full_name=full_name,
            role_title=role_title,
            paroisse=(row.get("paroisse") or "").strip() or None,
            rang=(row.get("rang") or "").strip() or None,
            photo_key=(row.get("cle_photo (ne pas modifier)") or "").strip() or None,
            display_order=i,
        )
        db.add(member)
        created += 1
    db.commit()
    print(f"  + {created} membre(s) du bureau créé(s) ({len(rows) - created} déjà présents).")


def import_effectifs(db) -> None:
    rows = _read_csv("effectifs.csv")
    existing = {c.categorie for c in db.query(EffectifCategorie).all()}
    created = 0
    for i, row in enumerate(rows):
        categorie = row["categorie (ne pas modifier l'ordre)"].strip()
        if categorie in existing:
            continue  # ne pas écraser une valeur potentiellement déjà corrigée par l'admin
        db.add(EffectifCategorie(categorie=categorie, effectif=int(row["effectif"]), display_order=i))
        created += 1
    db.commit()
    print(f"  + {created} catégorie(s) d'effectif créée(s) ({len(rows) - created} déjà présentes).")


def import_programme(db, sections_by_slug: dict[str, Section], author: User) -> None:
    rows = _read_csv("programme.csv")
    existing_titles = {(p.title, p.activity_date) for p in db.query(ProgrammeActivite).all()}
    created = 0
    for row in rows:
        title = row["titre"].strip()
        raw_date = row["date"].strip()
        activity_date = _parse_french_date(raw_date)
        if (title, activity_date) in existing_titles:
            continue

        # La date d'origine (souvent un intervalle ou un mois seul, ex.
        # "26 au 28 décembre 2025") est toujours conservée telle quelle pour
        # ne perdre aucune précision, même quand `activity_date` n'en retient
        # qu'une approximation exploitable par la base.
        description = f"Date d'origine (import du site précédent) : {raw_date}"

        db.add(
            ProgrammeActivite(
                title=title,
                description=description,
                activity_date=activity_date,
                location=(row.get("lieu") or "").strip() or None,
                target_audience=(row.get("public_cible") or "").strip() or None,
                section_id=None,  # le programme importé est vicarial (pas rattaché à une section précise)
                author_id=author.id,
                status=DocumentStatus.PUBLIE,
            )
        )
        created += 1
    db.commit()
    print(f"  + {created} activité(s) de programme créée(s) ({len(rows) - created} déjà présentes).")


def import_actualites(db, sections_by_slug: dict[str, Section], author: User) -> None:
    rows = _read_csv("actualites.csv")
    section_col = next(c for c in rows[0].keys() if c.startswith("section")) if rows else None
    existing_bodies = {a.body for a in db.query(Actualite).all()}
    created = 0
    for row in rows:
        body = row["texte"].strip()
        if body in existing_bodies:
            continue

        slug = (row.get(section_col) or "").strip().lower()
        section = None if slug == VICARIAT_WIDE_SLUG else sections_by_slug.get(slug)
        raw_date = row["date"].strip()
        published_at = _parse_french_date(raw_date)
        title = f"{raw_date} — {row['auteur'].strip()}"

        db.add(
            Actualite(
                title=title[:255],
                body=body,
                section_id=section.id if section else None,
                author_id=author.id,
                status=ActualiteStatus.PUBLIE,
                published_at=published_at,
            )
        )
        created += 1
    db.commit()
    print(f"  + {created} actualité(s) créée(s) ({len(rows) - created} déjà présentes).")


def run_with_session(db) -> None:
    """
    Corps de la migration, paramétré par une session DB — permet de la tester
    directement contre la base de test (voir tests/test_migration_script.py)
    sans dépendre d'un second moteur SQLAlchemy séparé.
    """
    print("Migration des données de l'ancien site vers la base PostgreSQL...")
    author = _get_migration_author(db)
    print(f"Auteur technique du contenu importé : {author.email}")

    print("\n1. Sections")
    sections_by_slug = import_sections(db)

    print("\n2. Bureau")
    import_bureau(db)

    print("\n3. Effectifs globaux")
    import_effectifs(db)

    print("\n4. Programme")
    import_programme(db, sections_by_slug, author)

    print("\n5. Actualités")
    import_actualites(db, sections_by_slug, author)

    print("\nMigration terminée avec succès.")


def run() -> None:
    db = SessionLocal()
    try:
        run_with_session(db)
    finally:
        db.close()


if __name__ == "__main__":
    run()
