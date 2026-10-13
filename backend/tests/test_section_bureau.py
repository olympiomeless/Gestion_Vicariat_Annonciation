def _login(client, username, password):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _create(client, token, *, full_name="Marie Koné", role_title="Présidente de section", section_id=None):
    payload = {"full_name": full_name, "role_title": role_title}
    if section_id is not None:
        payload["section_id"] = str(section_id)
    return client.post("/api/v1/section-bureau", headers=auth_headers(token), json=payload)


def test_section_creates_member_en_attente(client, section_user_nda):
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


def test_section_without_section_cannot_create(client, admin_user):
    # Un ADMIN qui ne précise pas de section doit être explicitement rejeté
    # (pas de membre de bureau de section "orphelin").
    token = _login(client, "admin", "AdminPass1")
    resp = _create(client, token)
    assert resp.status_code == 400


def test_pending_member_not_visible_to_other_sections(client, section_user_nda, section_user_stmarc):
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")

    created = _create(client, nda_token, full_name="Jean Privé").json()

    listing = client.get("/api/v1/section-bureau", headers=auth_headers(stmarc_token))
    assert all(item["id"] != created["id"] for item in listing.json())

    direct = client.get(f"/api/v1/section-bureau/{created['id']}", headers=auth_headers(stmarc_token))
    assert direct.status_code == 404


def test_admin_approve_workflow_makes_member_public(client, admin_user, section_user_nda, section_user_stmarc):
    admin_token = _login(client, "admin", "AdminPass1")
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")

    created = _create(client, nda_token, full_name="Responsable Catéchèse").json()

    approve = client.post(f"/api/v1/section-bureau/{created['id']}/approve", headers=auth_headers(admin_token))
    assert approve.status_code == 200
    assert approve.json()["status"] == "PUBLIE"

    visible = client.get(f"/api/v1/section-bureau/{created['id']}", headers=auth_headers(stmarc_token))
    assert visible.status_code == 200

    cannot_edit = client.put(
        f"/api/v1/section-bureau/{created['id']}", headers=auth_headers(stmarc_token), json={"full_name": "x"}
    )
    assert cannot_edit.status_code == 404

    cannot_self_edit = client.put(
        f"/api/v1/section-bureau/{created['id']}", headers=auth_headers(nda_token), json={"full_name": "x"}
    )
    assert cannot_self_edit.status_code == 400


def test_reject_with_reason_and_resubmission_on_edit(client, admin_user, section_user_nda):
    admin_token = _login(client, "admin", "AdminPass1")
    nda_token = _login(client, "nda", "SectionPass1")

    created = _create(client, nda_token, full_name="Candidat Incomplet").json()

    reject = client.post(
        f"/api/v1/section-bureau/{created['id']}/reject",
        headers=auth_headers(admin_token),
        json={"reason": "Merci de préciser la fonction exacte."},
    )
    assert reject.status_code == 200
    assert reject.json()["status"] == "REFUSE"

    fixed = client.put(
        f"/api/v1/section-bureau/{created['id']}", headers=auth_headers(nda_token), json={"role_title": "Secrétaire"}
    )
    assert fixed.status_code == 200
    assert fixed.json()["status"] == "EN_ATTENTE"
    assert fixed.json()["rejection_reason"] is None


def test_section_cannot_approve_or_reject(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    created = _create(client, token).json()
    assert client.post(f"/api/v1/section-bureau/{created['id']}/approve", headers=auth_headers(token)).status_code == 403
    assert client.post(
        f"/api/v1/section-bureau/{created['id']}/reject", headers=auth_headers(token), json={"reason": "x"}
    ).status_code == 403


def test_section_cannot_modify_or_delete_other_section_member(client, section_user_nda, section_user_stmarc):
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")

    created = _create(client, nda_token, full_name="Membre NDA").json()

    assert client.put(
        f"/api/v1/section-bureau/{created['id']}", headers=auth_headers(stmarc_token), json={"full_name": "x"}
    ).status_code == 404
    assert client.delete(f"/api/v1/section-bureau/{created['id']}", headers=auth_headers(stmarc_token)).status_code == 404


def test_admin_can_create_member_for_a_specific_section(client, admin_user, section_nda):
    admin_token = _login(client, "admin", "AdminPass1")
    resp = _create(client, admin_token, full_name="Nommé par l'admin", section_id=section_nda.id)
    assert resp.status_code == 201
    body = resp.json()
    assert body["section_id"] == str(section_nda.id)
    assert body["status"] == "EN_ATTENTE"
