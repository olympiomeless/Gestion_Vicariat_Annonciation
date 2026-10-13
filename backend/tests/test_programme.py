def _login(client, username, password):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _create(client, token, *, title="Sortie catéchèse", activity_date="2026-11-15", section_id=None):
    payload = {"title": title, "activity_date": activity_date}
    if section_id is not None:
        payload["section_id"] = str(section_id)
    return client.post("/api/v1/programme", headers=auth_headers(token), json=payload)


def test_section_creates_activity_en_attente(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    resp = _create(client, token)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "EN_ATTENTE"
    assert body["section_id"] == str(section_user_nda.section_id)


def test_section_create_ignores_spoofed_section_id(client, section_user_nda, section_stmarc):
    token = _login(client, "nda", "SectionPass1")
    resp = _create(client, token, section_id=section_stmarc.id)
    assert resp.status_code == 201
    assert resp.json()["section_id"] == str(section_user_nda.section_id)


def test_pending_activity_not_visible_to_other_sections(client, section_user_nda, section_user_stmarc):
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")

    created = _create(client, nda_token, title="Activité privée NDA").json()

    listing = client.get("/api/v1/programme", headers=auth_headers(stmarc_token))
    assert listing.json()["total"] == 0

    direct = client.get(f"/api/v1/programme/{created['id']}", headers=auth_headers(stmarc_token))
    assert direct.status_code == 404


def test_admin_approve_workflow_makes_activity_public(client, admin_user, section_user_nda, section_user_stmarc):
    admin_token = _login(client, "admin", "AdminPass1")
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")

    created = _create(client, nda_token, title="Retraite spirituelle").json()

    approve = client.post(f"/api/v1/programme/{created['id']}/approve", headers=auth_headers(admin_token))
    assert approve.status_code == 200
    assert approve.json()["status"] == "PUBLIE"

    visible = client.get(f"/api/v1/programme/{created['id']}", headers=auth_headers(stmarc_token))
    assert visible.status_code == 200

    cannot_edit = client.put(
        f"/api/v1/programme/{created['id']}", headers=auth_headers(stmarc_token), json={"title": "x"}
    )
    assert cannot_edit.status_code == 404


def test_reject_with_reason_and_resubmission_on_edit(client, admin_user, section_user_nda):
    admin_token = _login(client, "admin", "AdminPass1")
    nda_token = _login(client, "nda", "SectionPass1")

    created = _create(client, nda_token, title="Activité incomplète").json()

    reject = client.post(
        f"/api/v1/programme/{created['id']}/reject",
        headers=auth_headers(admin_token),
        json={"reason": "Merci de préciser le lieu."},
    )
    assert reject.status_code == 200
    assert reject.json()["status"] == "REFUSE"

    fixed = client.put(
        f"/api/v1/programme/{created['id']}", headers=auth_headers(nda_token), json={"location": "Paroisse NDA"}
    )
    assert fixed.status_code == 200
    assert fixed.json()["status"] == "EN_ATTENTE"
    assert fixed.json()["rejection_reason"] is None


def test_section_cannot_approve_or_reject(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    created = _create(client, token).json()
    assert client.post(f"/api/v1/programme/{created['id']}/approve", headers=auth_headers(token)).status_code == 403
    assert client.post(
        f"/api/v1/programme/{created['id']}/reject", headers=auth_headers(token), json={"reason": "x"}
    ).status_code == 403


def test_section_cannot_modify_or_delete_other_section_activity(client, section_user_nda, section_user_stmarc):
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")

    created = _create(client, nda_token, title="Activité NDA").json()

    assert client.put(
        f"/api/v1/programme/{created['id']}", headers=auth_headers(stmarc_token), json={"title": "x"}
    ).status_code == 404
    assert client.delete(f"/api/v1/programme/{created['id']}", headers=auth_headers(stmarc_token)).status_code == 404


def test_admin_can_create_vicariat_wide_activity(client, admin_user):
    admin_token = _login(client, "admin", "AdminPass1")
    resp = _create(client, admin_token, title="Grand rassemblement du Vicariat")
    assert resp.status_code == 201
    assert resp.json()["section_id"] is None
