"""
Vérifie le script de migration des données de l'ancien site (étape 13) :
import correct, non destructif, et idempotent (relançable sans dupliquer).
"""
import importlib
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = str(Path(__file__).resolve().parents[1] / "scripts")


@pytest.fixture()
def migration_module():
    if SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, SCRIPTS_DIR)
    module = importlib.import_module("migrate_existing_site_data")
    return importlib.reload(module)


def test_migration_requires_an_existing_admin(db_session, migration_module, roles):
    with pytest.raises(RuntimeError):
        migration_module._get_migration_author(db_session)


def test_migration_imports_all_content_and_is_idempotent(db_session, migration_module, admin_user):
    from app.models.actualite import Actualite
    from app.models.bureau import BureauMember
    from app.models.effectif import EffectifCategorie
    from app.models.programme import ProgrammeActivite
    from app.models.section import Section

    migration_module.run_with_session(db_session)

    assert db_session.query(Section).count() == 5
    assert db_session.query(BureauMember).count() == 19
    assert db_session.query(EffectifCategorie).count() == 7
    assert db_session.query(ProgrammeActivite).count() == 17
    assert db_session.query(Actualite).count() == 6

    nda = db_session.query(Section).filter(Section.slug == "nda").first()
    assert nda.name == "Notre-Dame de l'Annonciation"
    assert nda.effectif_total == 104

    # Deuxième exécution : aucune duplication.
    migration_module.run_with_session(db_session)
    assert db_session.query(Section).count() == 5
    assert db_session.query(BureauMember).count() == 19
    assert db_session.query(EffectifCategorie).count() == 7
    assert db_session.query(ProgrammeActivite).count() == 17
    assert db_session.query(Actualite).count() == 6


def test_migrated_content_is_published_and_visible_publicly(client, db_session, migration_module, admin_user):
    migration_module.run_with_session(db_session)

    resp = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "AdminPass1"}
    )
    token = resp.json()["access_token"]

    programme = client.get("/api/v1/programme", headers={"Authorization": f"Bearer {token}"})
    assert programme.status_code == 200
    assert programme.json()["total"] == 17
    assert all(item["status"] == "PUBLIE" for item in programme.json()["items"])
