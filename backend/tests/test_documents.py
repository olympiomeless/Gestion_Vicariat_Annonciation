import io

from tests.conftest import MINIMAL_PDF_BYTES


def _login(client, username, password):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _upload(client, token, *, name, category_id, section_id=None, content=MINIMAL_PDF_BYTES, filename="rapport.pdf"):
    data = {"name": name, "category_id": str(category_id)}
    if section_id is not None:
        data["section_id"] = str(section_id)
    files = {"file": (filename, io.BytesIO(content), "application/pdf")}
    return client.post("/api/v1/documents", headers=auth_headers(token), data=data, files=files)


def test_section_can_upload_and_see_own_document(client, section_user_nda, doc_category):
    token = _login(client, "nda", "SectionPass1")
    resp = _upload(client, token, name="Compte rendu NDA", category_id=doc_category.id)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "EN_ATTENTE"
    assert body["section_id"] == str(section_user_nda.section_id)

    listing = client.get("/api/v1/documents", headers=auth_headers(token))
    assert listing.status_code == 200
    assert listing.json()["total"] == 1


def test_section_upload_ignores_spoofed_section_id(client, section_user_nda, section_stmarc, doc_category):
    """Une section ne peut pas uploader 'pour' une autre section même en trafiquant le formulaire."""
    token = _login(client, "nda", "SectionPass1")
    resp = _upload(client, token, name="Faux document", category_id=doc_category.id, section_id=section_stmarc.id)
    assert resp.status_code == 201
    assert resp.json()["section_id"] == str(section_user_nda.section_id)  # forcé côté serveur, pas stmarc


def test_upload_rejects_disallowed_extension(client, section_user_nda, doc_category):
    token = _login(client, "nda", "SectionPass1")
    resp = _upload(client, token, name="Script malicieux", category_id=doc_category.id, content=b"#!/bin/sh\nrm -rf /", filename="evil.sh")
    assert resp.status_code == 400
    assert "non autorisé" in resp.json()["detail"]


def test_upload_rejects_spoofed_extension(client, section_user_nda, doc_category):
    """Un .pdf dont le contenu n'est pas un vrai PDF doit être rejeté (vérif. de signature binaire)."""
    token = _login(client, "nda", "SectionPass1")
    resp = _upload(
        client, token, name="Faux PDF", category_id=doc_category.id,
        content=b"MZ\x90\x00this-is-actually-an-exe-not-a-pdf", filename="notepad.pdf",
    )
    assert resp.status_code == 400
    assert "signature" in resp.json()["detail"] or "correspond" in resp.json()["detail"]


def test_upload_rejects_oversized_file(client, section_user_nda, doc_category, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 0)  # 0 Mo -> tout est trop gros
    token = _login(client, "nda", "SectionPass1")
    resp = _upload(client, token, name="Trop gros", category_id=doc_category.id, content=MINIMAL_PDF_BYTES * 10000)
    assert resp.status_code == 413


def test_section_a_cannot_see_pending_document_of_section_b(client, section_user_nda, section_user_stmarc, doc_category):
    token_nda = _login(client, "nda", "SectionPass1")
    token_stmarc = _login(client, "stmarc", "SectionPass1")

    upload = _upload(client, token_nda, name="Document privé NDA", category_id=doc_category.id)
    doc_id = upload.json()["id"]

    # Saint-Marc ne doit ni le voir dans sa liste, ni pouvoir y accéder directement par id.
    listing = client.get("/api/v1/documents", headers=auth_headers(token_stmarc))
    assert listing.json()["total"] == 0

    direct = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers(token_stmarc))
    assert direct.status_code == 404  # jamais 403 : ne révèle pas l'existence de la ressource

    download = client.get(f"/api/v1/documents/{doc_id}/download", headers=auth_headers(token_stmarc))
    assert download.status_code == 404


def test_section_a_cannot_modify_or_delete_section_b_document(client, section_user_nda, section_user_stmarc, doc_category):
    token_nda = _login(client, "nda", "SectionPass1")
    token_stmarc = _login(client, "stmarc", "SectionPass1")

    doc_id = _upload(client, token_nda, name="Document NDA", category_id=doc_category.id).json()["id"]

    edit = client.put(f"/api/v1/documents/{doc_id}", headers=auth_headers(token_stmarc), json={"name": "Piraté"})
    assert edit.status_code in (403, 404)

    delete = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers(token_stmarc))
    assert delete.status_code in (403, 404)

    # Le document original est intact.
    still_there = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers(token_nda))
    assert still_there.status_code == 200
    assert still_there.json()["name"] == "Document NDA"


def test_section_cannot_approve_own_document(client, section_user_nda, doc_category):
    token = _login(client, "nda", "SectionPass1")
    doc_id = _upload(client, token, name="Auto-approbation ?", category_id=doc_category.id).json()["id"]
    resp = client.post(f"/api/v1/documents/{doc_id}/approve", headers=auth_headers(token))
    assert resp.status_code == 403


def test_admin_approve_workflow_makes_document_visible_to_other_sections(
    client, admin_user, section_user_nda, section_user_stmarc, doc_category
):
    admin_token = _login(client, "admin", "AdminPass1")
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")

    doc_id = _upload(client, nda_token, name="Rapport public NDA", category_id=doc_category.id).json()["id"]

    # Avant publication : Saint-Marc ne le voit pas.
    assert client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers(stmarc_token)).status_code == 404

    approve = client.post(f"/api/v1/documents/{doc_id}/approve", headers=auth_headers(admin_token))
    assert approve.status_code == 200
    assert approve.json()["status"] == "PUBLIE"

    # Après publication : visible par tout le monde, y compris Saint-Marc, en lecture seule.
    visible = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers(stmarc_token))
    assert visible.status_code == 200

    cannot_edit = client.put(f"/api/v1/documents/{doc_id}", headers=auth_headers(stmarc_token), json={"name": "x"})
    assert cannot_edit.status_code in (403, 404)

    download = client.get(f"/api/v1/documents/{doc_id}/download", headers=auth_headers(stmarc_token))
    assert download.status_code == 200
    assert download.content == MINIMAL_PDF_BYTES


def test_admin_reject_with_reason_and_resubmission_flow(client, admin_user, section_user_nda, doc_category):
    admin_token = _login(client, "admin", "AdminPass1")
    nda_token = _login(client, "nda", "SectionPass1")

    doc_id = _upload(client, nda_token, name="Document incomplet", category_id=doc_category.id).json()["id"]

    reject = client.post(
        f"/api/v1/documents/{doc_id}/reject",
        headers=auth_headers(admin_token),
        json={"reason": "Document incomplet, merci de fournir la version signée."},
    )
    assert reject.status_code == 200
    assert reject.json()["status"] == "REFUSE"
    assert "signée" in reject.json()["rejection_reason"]

    # La section corrige les métadonnées : repasse automatiquement en attente.
    fixed = client.put(
        f"/api/v1/documents/{doc_id}", headers=auth_headers(nda_token), json={"description": "Version corrigée et signée"}
    )
    assert fixed.status_code == 200
    assert fixed.json()["status"] == "EN_ATTENTE"
    assert fixed.json()["rejection_reason"] is None


def test_published_document_cannot_be_edited_by_section_without_admin(client, admin_user, section_user_nda, doc_category):
    admin_token = _login(client, "admin", "AdminPass1")
    nda_token = _login(client, "nda", "SectionPass1")

    doc_id = _upload(client, nda_token, name="Doc", category_id=doc_category.id).json()["id"]
    client.post(f"/api/v1/documents/{doc_id}/approve", headers=auth_headers(admin_token))

    resp = client.put(f"/api/v1/documents/{doc_id}", headers=auth_headers(nda_token), json={"name": "Modifié"})
    assert resp.status_code == 400


def test_admin_sees_and_manages_all_documents(client, admin_user, section_user_nda, section_user_stmarc, doc_category):
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")
    admin_token = _login(client, "admin", "AdminPass1")

    _upload(client, nda_token, name="Doc NDA", category_id=doc_category.id)
    _upload(client, stmarc_token, name="Doc Saint-Marc", category_id=doc_category.id)

    listing = client.get("/api/v1/documents", headers=auth_headers(admin_token))
    assert listing.json()["total"] == 2


def test_categories_crud_and_system_protection(client, admin_user):
    admin_token = _login(client, "admin", "AdminPass1")

    create = client.post("/api/v1/documents/categories", headers=auth_headers(admin_token), json={"name": "Divers"})
    assert create.status_code == 201
    cat_id = create.json()["id"]

    delete = client.delete(f"/api/v1/documents/categories/{cat_id}", headers=auth_headers(admin_token))
    assert delete.status_code == 204


def test_section_cannot_create_category(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    resp = client.post("/api/v1/documents/categories", headers=auth_headers(token), json={"name": "Hack"})
    assert resp.status_code == 403
