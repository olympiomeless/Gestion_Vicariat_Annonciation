def _login(client, username, password):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_create_and_list_bureau_member(client, admin_user):
    token = _login(client, "admin", "AdminPass1")
    resp = client.post(
        "/api/v1/bureau", headers=auth_headers(token),
        json={"full_name": "AP Test Président", "role_title": "Président du Vicariat", "rang": "AP"},
    )
    assert resp.status_code == 201, resp.text

    listing = client.get("/api/v1/bureau", headers=auth_headers(token))
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_section_cannot_create_bureau_member(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    resp = client.post(
        "/api/v1/bureau", headers=auth_headers(token), json={"full_name": "Intrus", "role_title": "Hacker"}
    )
    assert resp.status_code == 403


def test_section_can_read_bureau_but_not_write(client, admin_user, section_user_nda):
    admin_token = _login(client, "admin", "AdminPass1")
    client.post(
        "/api/v1/bureau", headers=auth_headers(admin_token), json={"full_name": "AC Untel", "role_title": "Secrétaire"}
    )
    section_token = _login(client, "nda", "SectionPass1")
    resp = client.get("/api/v1/bureau", headers=auth_headers(section_token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_admin_can_manage_effectifs(client, admin_user):
    token = _login(client, "admin", "AdminPass1")
    create = client.post("/api/v1/effectifs", headers=auth_headers(token), json={"categorie": "Benjamins", "effectif": 57})
    assert create.status_code == 201
    cat_id = create.json()["id"]

    update = client.put(f"/api/v1/effectifs/{cat_id}", headers=auth_headers(token), json={"effectif": 60})
    assert update.status_code == 200
    assert update.json()["effectif"] == 60

    duplicate = client.post("/api/v1/effectifs", headers=auth_headers(token), json={"categorie": "Benjamins", "effectif": 1})
    assert duplicate.status_code == 400


def test_section_cannot_modify_effectifs(client, admin_user, section_user_nda):
    admin_token = _login(client, "admin", "AdminPass1")
    created = client.post(
        "/api/v1/effectifs", headers=auth_headers(admin_token), json={"categorie": "Cadets", "effectif": 124}
    ).json()

    section_token = _login(client, "nda", "SectionPass1")
    resp = client.put(
        f"/api/v1/effectifs/{created['id']}", headers=auth_headers(section_token), json={"effectif": 999}
    )
    assert resp.status_code == 403
