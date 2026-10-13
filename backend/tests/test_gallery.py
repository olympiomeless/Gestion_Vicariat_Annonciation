import io

from tests.conftest import MINIMAL_PDF_BYTES, MINIMAL_PNG_BYTES


def _login(client, username, password):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _upload(client, token, *, caption="Une belle photo", content=MINIMAL_PNG_BYTES, filename="photo.png", section_id=None):
    data = {"caption": caption}
    if section_id is not None:
        data["section_id"] = str(section_id)
    files = {"file": (filename, io.BytesIO(content), "image/png")}
    return client.post("/api/v1/gallery", headers=auth_headers(token), data=data, files=files)


def test_section_uploads_photo_en_attente(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    resp = _upload(client, token)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "EN_ATTENTE"
    assert body["section_id"] == str(section_user_nda.section_id)


def test_upload_ignores_spoofed_section_id(client, section_user_nda, section_stmarc):
    token = _login(client, "nda", "SectionPass1")
    resp = _upload(client, token, section_id=section_stmarc.id)
    assert resp.status_code == 201
    assert resp.json()["section_id"] == str(section_user_nda.section_id)


def test_upload_rejects_non_image_extension(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    resp = _upload(client, token, content=MINIMAL_PDF_BYTES, filename="rapport.pdf")
    assert resp.status_code == 400
    assert "image" in resp.json()["detail"].lower()


def test_upload_rejects_spoofed_extension(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    resp = _upload(client, token, content=b"MZ\x90\x00not-an-image-at-all", filename="fake.png")
    assert resp.status_code == 400


def test_pending_photo_not_visible_to_other_sections(client, section_user_nda, section_user_stmarc):
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")

    photo = _upload(client, nda_token, caption="Photo privée NDA").json()

    listing = client.get("/api/v1/gallery", headers=auth_headers(stmarc_token))
    assert listing.json()["total"] == 0

    direct = client.get(f"/api/v1/gallery/{photo['id']}", headers=auth_headers(stmarc_token))
    assert direct.status_code == 404

    file_resp = client.get(f"/api/v1/gallery/{photo['id']}/file", headers=auth_headers(stmarc_token))
    assert file_resp.status_code == 404


def test_section_cannot_modify_or_delete_other_section_photo(client, section_user_nda, section_user_stmarc):
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")

    photo = _upload(client, nda_token, caption="Photo NDA").json()

    edit = client.put(f"/api/v1/gallery/{photo['id']}", headers=auth_headers(stmarc_token), json={"caption": "x"})
    assert edit.status_code == 404
    delete = client.delete(f"/api/v1/gallery/{photo['id']}", headers=auth_headers(stmarc_token))
    assert delete.status_code == 404


def test_admin_approve_makes_photo_visible_and_downloadable(client, admin_user, section_user_nda, section_user_stmarc):
    admin_token = _login(client, "admin", "AdminPass1")
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")

    photo = _upload(client, nda_token, caption="Photo publiable").json()

    approve = client.post(f"/api/v1/gallery/{photo['id']}/approve", headers=auth_headers(admin_token))
    assert approve.status_code == 200
    assert approve.json()["status"] == "PUBLIE"

    visible = client.get(f"/api/v1/gallery/{photo['id']}", headers=auth_headers(stmarc_token))
    assert visible.status_code == 200

    file_resp = client.get(f"/api/v1/gallery/{photo['id']}/file", headers=auth_headers(stmarc_token))
    assert file_resp.status_code == 200
    assert file_resp.content == MINIMAL_PNG_BYTES

    cannot_edit = client.put(f"/api/v1/gallery/{photo['id']}", headers=auth_headers(stmarc_token), json={"caption": "x"})
    assert cannot_edit.status_code == 404


def test_reject_with_reason_and_resubmission(client, admin_user, section_user_nda):
    admin_token = _login(client, "admin", "AdminPass1")
    nda_token = _login(client, "nda", "SectionPass1")

    photo = _upload(client, nda_token, caption="Photo floue").json()

    reject = client.post(
        f"/api/v1/gallery/{photo['id']}/reject", headers=auth_headers(admin_token), json={"reason": "Photo trop floue."}
    )
    assert reject.status_code == 200
    assert reject.json()["status"] == "REFUSE"

    fixed = client.put(
        f"/api/v1/gallery/{photo['id']}", headers=auth_headers(nda_token), json={"caption": "Nouvelle légende"}
    )
    assert fixed.status_code == 200
    assert fixed.json()["status"] == "EN_ATTENTE"
    assert fixed.json()["rejection_reason"] is None


def test_section_cannot_approve_or_reject(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    photo = _upload(client, token).json()
    assert client.post(f"/api/v1/gallery/{photo['id']}/approve", headers=auth_headers(token)).status_code == 403
    assert client.post(
        f"/api/v1/gallery/{photo['id']}/reject", headers=auth_headers(token), json={"reason": "x"}
    ).status_code == 403


def test_delete_removes_file_from_storage(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    photo = _upload(client, token).json()

    delete = client.delete(f"/api/v1/gallery/{photo['id']}", headers=auth_headers(token))
    assert delete.status_code == 204

    gone = client.get(f"/api/v1/gallery/{photo['id']}", headers=auth_headers(token))
    assert gone.status_code == 404
