def _login(client, username, password):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _create(client, token, *, title="Titre", body="Contenu de l'actualité.", section_id=None):
    payload = {"title": title, "body": body}
    if section_id is not None:
        payload["section_id"] = str(section_id)
    return client.post("/api/v1/actualites", headers=auth_headers(token), json=payload)


def test_section_creates_draft_and_sees_it(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    resp = _create(client, token, title="Sortie du mois")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "BROUILLON"
    assert body["section_id"] == str(section_user_nda.section_id)

    listing = client.get("/api/v1/actualites", headers=auth_headers(token))
    assert listing.json()["total"] == 1


def test_section_create_ignores_spoofed_section_id(client, section_user_nda, section_stmarc):
    token = _login(client, "nda", "SectionPass1")
    resp = _create(client, token, title="Faux", section_id=section_stmarc.id)
    assert resp.status_code == 201
    assert resp.json()["section_id"] == str(section_user_nda.section_id)


def test_draft_not_visible_to_other_sections(client, section_user_nda, section_user_stmarc):
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")

    created = _create(client, nda_token, title="Brouillon privé NDA").json()

    listing = client.get("/api/v1/actualites", headers=auth_headers(stmarc_token))
    assert listing.json()["total"] == 0

    direct = client.get(f"/api/v1/actualites/{created['id']}", headers=auth_headers(stmarc_token))
    assert direct.status_code == 404


def test_full_submit_approve_publish_workflow(client, admin_user, section_user_nda, section_user_stmarc):
    admin_token = _login(client, "admin", "AdminPass1")
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")

    created = _create(client, nda_token, title="Journée de prière").json()
    actu_id = created["id"]

    submit = client.post(f"/api/v1/actualites/{actu_id}/submit", headers=auth_headers(nda_token))
    assert submit.status_code == 200
    assert submit.json()["status"] == "SOUMIS"

    # Toujours invisible pour Saint-Marc tant que non publiée.
    assert client.get(f"/api/v1/actualites/{actu_id}", headers=auth_headers(stmarc_token)).status_code == 404

    approve = client.post(f"/api/v1/actualites/{actu_id}/approve", headers=auth_headers(admin_token))
    assert approve.status_code == 200
    assert approve.json()["status"] == "PUBLIE"
    assert approve.json()["published_at"] is not None

    # Publiée : visible par tout le monde, y compris en lecture pour Saint-Marc.
    visible = client.get(f"/api/v1/actualites/{actu_id}", headers=auth_headers(stmarc_token))
    assert visible.status_code == 200

    # Mais Saint-Marc ne peut pas la modifier.
    edit = client.put(f"/api/v1/actualites/{actu_id}", headers=auth_headers(stmarc_token), json={"title": "Piraté"})
    assert edit.status_code == 404


def test_reject_with_reason_resets_to_brouillon_on_edit(client, admin_user, section_user_nda):
    admin_token = _login(client, "admin", "AdminPass1")
    nda_token = _login(client, "nda", "SectionPass1")

    actu_id = _create(client, nda_token, title="Actu incomplète").json()["id"]
    client.post(f"/api/v1/actualites/{actu_id}/submit", headers=auth_headers(nda_token))

    reject = client.post(
        f"/api/v1/actualites/{actu_id}/reject", headers=auth_headers(admin_token), json={"reason": "Titre à préciser."}
    )
    assert reject.status_code == 200
    assert reject.json()["status"] == "REFUSE"

    fixed = client.put(f"/api/v1/actualites/{actu_id}", headers=auth_headers(nda_token), json={"title": "Actu corrigée"})
    assert fixed.status_code == 200
    assert fixed.json()["status"] == "BROUILLON"
    assert fixed.json()["rejection_reason"] is None


def test_section_cannot_approve_or_reject(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    actu_id = _create(client, token, title="Auto-validation ?").json()["id"]
    client.post(f"/api/v1/actualites/{actu_id}/submit", headers=auth_headers(token))

    assert client.post(f"/api/v1/actualites/{actu_id}/approve", headers=auth_headers(token)).status_code == 403
    assert client.post(
        f"/api/v1/actualites/{actu_id}/reject", headers=auth_headers(token), json={"reason": "x"}
    ).status_code == 403


def test_section_cannot_modify_or_delete_other_section_actualite(client, section_user_nda, section_user_stmarc):
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")

    actu_id = _create(client, nda_token, title="Actu NDA").json()["id"]

    assert client.put(
        f"/api/v1/actualites/{actu_id}", headers=auth_headers(stmarc_token), json={"title": "x"}
    ).status_code == 404
    assert client.delete(f"/api/v1/actualites/{actu_id}", headers=auth_headers(stmarc_token)).status_code == 404


def test_admin_can_create_vicariat_wide_actualite(client, admin_user):
    admin_token = _login(client, "admin", "AdminPass1")
    resp = _create(client, admin_token, title="Info générale du Vicariat")
    assert resp.status_code == 201
    assert resp.json()["section_id"] is None


def test_cannot_submit_twice(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    actu_id = _create(client, token, title="Actu").json()["id"]
    client.post(f"/api/v1/actualites/{actu_id}/submit", headers=auth_headers(token))
    resp = client.post(f"/api/v1/actualites/{actu_id}/submit", headers=auth_headers(token))
    assert resp.status_code == 400
