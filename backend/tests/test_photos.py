import io

from tests.conftest import MINIMAL_PDF_BYTES, MINIMAL_PNG_BYTES


def _login(client, username, password):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- Bureau ----------

def test_admin_can_upload_view_and_remove_bureau_photo(client, admin_user):
    token = _login(client, admin_user.username, "AdminPass1")
    create = client.post(
        "/api/v1/bureau", headers=auth_headers(token), json={"full_name": "AP Test Photo", "role_title": "Trésorier"}
    )
    member_id = create.json()["id"]
    assert create.json()["has_photo"] is False

    upload = client.post(
        f"/api/v1/bureau/{member_id}/photo", headers=auth_headers(token),
        files={"file": ("photo.png", io.BytesIO(MINIMAL_PNG_BYTES), "image/png")},
    )
    assert upload.status_code == 200, upload.text
    assert upload.json()["has_photo"] is True

    # Aperçu authentifié.
    preview = client.get(f"/api/v1/bureau/{member_id}/photo", headers=auth_headers(token))
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "image/png"

    # Aperçu public, sans authentification.
    public = client.get(f"/api/v1/public/bureau/{member_id}/photo")
    assert public.status_code == 200
    assert public.headers["content-type"] == "image/png"

    remove = client.delete(f"/api/v1/bureau/{member_id}/photo", headers=auth_headers(token))
    assert remove.status_code == 200
    assert remove.json()["has_photo"] is False
    assert client.get(f"/api/v1/public/bureau/{member_id}/photo").status_code == 404


def test_bureau_photo_upload_rejects_non_image(client, admin_user):
    token = _login(client, admin_user.username, "AdminPass1")
    member_id = client.post(
        "/api/v1/bureau", headers=auth_headers(token), json={"full_name": "AC Test", "role_title": "Secrétaire"}
    ).json()["id"]

    resp = client.post(
        f"/api/v1/bureau/{member_id}/photo", headers=auth_headers(token),
        files={"file": ("rapport.pdf", io.BytesIO(MINIMAL_PDF_BYTES), "application/pdf")},
    )
    assert resp.status_code == 400


def test_section_cannot_upload_bureau_photo(client, admin_user, section_user_nda):
    admin_token = _login(client, admin_user.username, "AdminPass1")
    member_id = client.post(
        "/api/v1/bureau", headers=auth_headers(admin_token), json={"full_name": "AA Test", "role_title": "Membre"}
    ).json()["id"]

    section_token = _login(client, section_user_nda.username, "SectionPass1")
    resp = client.post(
        f"/api/v1/bureau/{member_id}/photo", headers=auth_headers(section_token),
        files={"file": ("photo.png", io.BytesIO(MINIMAL_PNG_BYTES), "image/png")},
    )
    assert resp.status_code == 403


# ---------- Sections ----------

def test_admin_can_upload_replace_and_remove_section_photo(client, admin_user, section_nda):
    token = _login(client, admin_user.username, "AdminPass1")

    first = client.post(
        f"/api/v1/sections/{section_nda.id}/photo", headers=auth_headers(token),
        files={"file": ("logo.png", io.BytesIO(MINIMAL_PNG_BYTES), "image/png")},
    )
    assert first.status_code == 200, first.text
    assert first.json()["has_photo"] is True

    # Remplacer : doit rester accessible et ne garder qu'un seul fichier utile.
    second = client.post(
        f"/api/v1/sections/{section_nda.id}/photo", headers=auth_headers(token),
        files={"file": ("logo2.png", io.BytesIO(MINIMAL_PNG_BYTES), "image/png")},
    )
    assert second.status_code == 200
    assert second.json()["has_photo"] is True

    public = client.get(f"/api/v1/public/sections/{section_nda.id}/photo")
    assert public.status_code == 200

    remove = client.delete(f"/api/v1/sections/{section_nda.id}/photo", headers=auth_headers(token))
    assert remove.status_code == 200
    assert remove.json()["has_photo"] is False
    assert client.get(f"/api/v1/public/sections/{section_nda.id}/photo").status_code == 404


def test_section_cannot_upload_section_photo(client, section_user_nda, section_nda):
    token = _login(client, section_user_nda.username, "SectionPass1")
    resp = client.post(
        f"/api/v1/sections/{section_nda.id}/photo", headers=auth_headers(token),
        files={"file": ("logo.png", io.BytesIO(MINIMAL_PNG_BYTES), "image/png")},
    )
    assert resp.status_code == 403


def test_public_sections_listing_reports_has_photo(client, admin_user, section_nda):
    token = _login(client, admin_user.username, "AdminPass1")
    client.post(
        f"/api/v1/sections/{section_nda.id}/photo", headers=auth_headers(token),
        files={"file": ("logo.png", io.BytesIO(MINIMAL_PNG_BYTES), "image/png")},
    )
    listing = client.get("/api/v1/public/sections")
    assert listing.status_code == 200
    match = next(s for s in listing.json() if s["id"] == str(section_nda.id))
    assert match["has_photo"] is True
