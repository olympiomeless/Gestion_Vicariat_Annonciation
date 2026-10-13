import io

from tests.conftest import MINIMAL_PDF_BYTES, MINIMAL_PNG_BYTES


def _login(client, username, password):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_public_sections_reachable_without_authentication(client, section_nda, section_stmarc):
    resp = client.get("/api/v1/public/sections")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_public_bureau_and_effectifs_reachable_without_authentication(client, admin_user):
    admin_token = _login(client, "admin", "AdminPass1")
    client.post("/api/v1/bureau", headers=auth_headers(admin_token), json={"full_name": "AP X", "role_title": "Président"})
    client.post("/api/v1/effectifs", headers=auth_headers(admin_token), json={"categorie": "Cadets", "effectif": 100})

    bureau = client.get("/api/v1/public/bureau")
    assert bureau.status_code == 200
    assert len(bureau.json()) == 1

    effectifs = client.get("/api/v1/public/effectifs")
    assert effectifs.status_code == 200
    assert len(effectifs.json()) == 1


def test_public_programme_only_shows_published(client, admin_user, section_user_nda):
    nda_token = _login(client, "nda", "SectionPass1")
    admin_token = _login(client, "admin", "AdminPass1")

    pending = client.post(
        "/api/v1/programme", headers=auth_headers(nda_token),
        json={"title": "En attente", "activity_date": "2026-12-01"},
    ).json()
    published = client.post(
        "/api/v1/programme", headers=auth_headers(nda_token),
        json={"title": "Publiée", "activity_date": "2026-12-05"},
    ).json()
    client.post(f"/api/v1/programme/{published['id']}/approve", headers=auth_headers(admin_token))

    resp = client.get("/api/v1/public/programme")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Publiée"
    titles = [item["title"] for item in body["items"]]
    assert "En attente" not in titles


def test_public_actualites_only_shows_published(client, admin_user, section_user_nda):
    nda_token = _login(client, "nda", "SectionPass1")
    admin_token = _login(client, "admin", "AdminPass1")

    draft = client.post("/api/v1/actualites", headers=auth_headers(nda_token), json={"title": "Brouillon", "body": "x"}).json()
    to_publish = client.post(
        "/api/v1/actualites", headers=auth_headers(nda_token), json={"title": "À publier", "body": "Contenu public"}
    ).json()
    client.post(f"/api/v1/actualites/{to_publish['id']}/submit", headers=auth_headers(nda_token))
    client.post(f"/api/v1/actualites/{to_publish['id']}/approve", headers=auth_headers(admin_token))

    resp = client.get("/api/v1/public/actualites")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "À publier"


def test_public_gallery_hides_pending_photo_and_its_file(client, admin_user, section_user_nda):
    nda_token = _login(client, "nda", "SectionPass1")
    admin_token = _login(client, "admin", "AdminPass1")

    files = {"file": ("photo.png", io.BytesIO(MINIMAL_PNG_BYTES), "image/png")}
    pending = client.post(
        "/api/v1/gallery", headers=auth_headers(nda_token), data={"caption": "En attente"}, files=files
    ).json()

    files2 = {"file": ("photo2.png", io.BytesIO(MINIMAL_PNG_BYTES), "image/png")}
    published = client.post(
        "/api/v1/gallery", headers=auth_headers(nda_token), data={"caption": "Publiée"}, files=files2
    ).json()
    client.post(f"/api/v1/gallery/{published['id']}/approve", headers=auth_headers(admin_token))

    listing = client.get("/api/v1/public/gallery")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    # La photo en attente n'est jamais accessible publiquement, ni ses métadonnées ni son fichier.
    pending_file = client.get(f"/api/v1/public/gallery/{pending['id']}/file")
    assert pending_file.status_code == 404

    published_file = client.get(f"/api/v1/public/gallery/{published['id']}/file")
    assert published_file.status_code == 200
    assert published_file.content == MINIMAL_PNG_BYTES


def test_public_documents_hides_pending_and_refused(client, admin_user, section_user_nda, doc_category):
    nda_token = _login(client, "nda", "SectionPass1")
    admin_token = _login(client, "admin", "AdminPass1")

    def upload(name):
        files = {"file": ("r.pdf", io.BytesIO(MINIMAL_PDF_BYTES), "application/pdf")}
        return client.post(
            "/api/v1/documents", headers=auth_headers(nda_token),
            data={"name": name, "category_id": str(doc_category.id)}, files=files,
        ).json()

    pending = upload("Doc en attente")
    to_publish = upload("Doc à publier")
    to_refuse = upload("Doc à refuser")
    client.post(f"/api/v1/documents/{to_publish['id']}/approve", headers=auth_headers(admin_token))
    client.post(
        f"/api/v1/documents/{to_refuse['id']}/reject", headers=auth_headers(admin_token), json={"reason": "x"}
    )

    listing = client.get("/api/v1/public/documents")
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Doc à publier"

    assert client.get(f"/api/v1/public/documents/{pending['id']}/download").status_code == 404
    assert client.get(f"/api/v1/public/documents/{to_refuse['id']}/download").status_code == 404

    ok = client.get(f"/api/v1/public/documents/{to_publish['id']}/download")
    assert ok.status_code == 200
    assert ok.content == MINIMAL_PDF_BYTES


def test_public_endpoints_never_require_authorization_header(client):
    # Vérifie explicitement l'absence totale d'exigence d'authentification :
    # aucun de ces appels ne doit renvoyer 401.
    for path in ["/api/v1/public/sections", "/api/v1/public/bureau", "/api/v1/public/effectifs",
                 "/api/v1/public/programme", "/api/v1/public/actualites", "/api/v1/public/gallery",
                 "/api/v1/public/documents"]:
        resp = client.get(path)
        assert resp.status_code != 401, f"{path} ne doit jamais exiger d'authentification"
