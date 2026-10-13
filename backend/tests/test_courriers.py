import io

from tests.conftest import MINIMAL_PDF_BYTES


def _login(client, username, password):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _create(client, token, *, kind="MESSAGE", subject="Objet du courrier", body="Corps du message.", section_id=None, file=None):
    data = {"kind": kind, "subject": subject, "body": body}
    if section_id is not None:
        data["section_id"] = str(section_id)
    files = None
    if file is not None:
        files = {"file": file}
    return client.post("/api/v1/courriers", headers=auth_headers(token), data=data, files=files)


def test_section_creates_message(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    resp = _create(client, token, kind="MESSAGE", subject="Demande d'information")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["kind"] == "MESSAGE"
    assert body["status"] == "NOUVEAU"
    assert body["section_id"] == str(section_user_nda.section_id)
    assert body["has_attachment"] is False


def test_section_creates_demande_fichier_with_attachment(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    resp = _create(
        client,
        token,
        kind="DEMANDE_FICHIER",
        subject="Attestation de camp pour Jean X",
        body="Merci de fournir l'attestation de camp 2026 pour Jean X.",
        file=("justificatif.pdf", io.BytesIO(MINIMAL_PDF_BYTES), "application/pdf"),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["kind"] == "DEMANDE_FICHIER"
    assert body["has_attachment"] is True
    assert body["attachment_original_filename"] == "justificatif.pdf"

    download = client.get(f"/api/v1/courriers/{body['id']}/attachment", headers=auth_headers(token))
    assert download.status_code == 200
    assert download.content == MINIMAL_PDF_BYTES


def test_section_create_ignores_spoofed_section_id(client, section_user_nda, section_stmarc):
    token = _login(client, "nda", "SectionPass1")
    resp = _create(client, token, section_id=section_stmarc.id)
    assert resp.status_code == 201
    assert resp.json()["section_id"] == str(section_user_nda.section_id)


def test_admin_without_section_id_is_rejected(client, admin_user):
    token = _login(client, "admin", "AdminPass1")
    resp = _create(client, token)
    assert resp.status_code == 400


def test_admin_can_create_for_a_specific_section(client, admin_user, section_nda):
    token = _login(client, "admin", "AdminPass1")
    resp = _create(client, token, section_id=section_nda.id)
    assert resp.status_code == 201
    assert resp.json()["section_id"] == str(section_nda.id)


def test_other_section_cannot_view_or_list(client, section_user_nda, section_user_stmarc):
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")

    created = _create(client, nda_token, subject="Privé NDA").json()

    listing = client.get("/api/v1/courriers", headers=auth_headers(stmarc_token))
    assert all(item["id"] != created["id"] for item in listing.json())

    direct = client.get(f"/api/v1/courriers/{created['id']}", headers=auth_headers(stmarc_token))
    assert direct.status_code == 404


def test_admin_sees_all_and_can_filter_by_section(client, admin_user, section_user_nda, section_user_stmarc):
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")
    admin_token = _login(client, "admin", "AdminPass1")

    _create(client, nda_token, subject="De NDA")
    _create(client, stmarc_token, subject="De Saint-Marc")

    all_listing = client.get("/api/v1/courriers", headers=auth_headers(admin_token))
    assert len(all_listing.json()) == 2

    filtered = client.get(
        f"/api/v1/courriers?section_id={section_user_nda.section_id}", headers=auth_headers(admin_token)
    )
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["subject"] == "De NDA"


def test_admin_responds_with_note_only(client, admin_user, section_user_nda):
    nda_token = _login(client, "nda", "SectionPass1")
    admin_token = _login(client, "admin", "AdminPass1")

    created = _create(client, nda_token, subject="Besoin d'une réponse").json()

    resp = client.post(
        f"/api/v1/courriers/{created['id']}/respond",
        headers=auth_headers(admin_token),
        data={"response_note": "Bien reçu, voici la réponse."},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "TRAITE"
    assert body["response_note"] == "Bien reçu, voici la réponse."
    assert body["has_response_file"] is False
    assert body["handled_by_name"] == admin_user.full_name


def test_admin_responds_to_demande_fichier_with_file(client, admin_user, section_user_nda):
    nda_token = _login(client, "nda", "SectionPass1")
    admin_token = _login(client, "admin", "AdminPass1")

    created = _create(client, nda_token, kind="DEMANDE_FICHIER", subject="Attestation de camp").json()

    resp = client.post(
        f"/api/v1/courriers/{created['id']}/respond",
        headers=auth_headers(admin_token),
        data={"response_note": "Voici l'attestation demandée."},
        files={"file": ("attestation.pdf", io.BytesIO(MINIMAL_PDF_BYTES), "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "TRAITE"
    assert body["has_response_file"] is True
    assert body["response_original_filename"] == "attestation.pdf"

    download = client.get(f"/api/v1/courriers/{created['id']}/response-file", headers=auth_headers(nda_token))
    assert download.status_code == 200
    assert download.content == MINIMAL_PDF_BYTES


def test_section_cannot_respond(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    created = _create(client, token).json()
    resp = client.post(
        f"/api/v1/courriers/{created['id']}/respond", headers=auth_headers(token), data={"response_note": "x"}
    )
    assert resp.status_code == 403


def test_section_can_delete_own_pending_courrier(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    created = _create(client, token).json()
    resp = client.delete(f"/api/v1/courriers/{created['id']}", headers=auth_headers(token))
    assert resp.status_code == 204

    listing = client.get("/api/v1/courriers", headers=auth_headers(token))
    assert all(item["id"] != created["id"] for item in listing.json())


def test_section_cannot_delete_other_section_courrier(client, section_user_nda, section_user_stmarc):
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")
    created = _create(client, nda_token).json()

    resp = client.delete(f"/api/v1/courriers/{created['id']}", headers=auth_headers(stmarc_token))
    assert resp.status_code == 404


def test_section_cannot_delete_once_handled(client, admin_user, section_user_nda):
    nda_token = _login(client, "nda", "SectionPass1")
    admin_token = _login(client, "admin", "AdminPass1")
    created = _create(client, nda_token).json()

    client.post(
        f"/api/v1/courriers/{created['id']}/respond", headers=auth_headers(admin_token), data={"response_note": "ok"}
    )

    resp = client.delete(f"/api/v1/courriers/{created['id']}", headers=auth_headers(nda_token))
    assert resp.status_code == 400
