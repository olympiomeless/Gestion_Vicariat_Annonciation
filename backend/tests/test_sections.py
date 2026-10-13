def _login(client, username, password):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_admin_creates_section_without_account(client, admin_user, roles):
    token = _login(client, "admin", "AdminPass1")
    resp = client.post(
        "/api/v1/sections", headers=auth_headers(token), json={"slug": "ste-therese", "name": "Sainte-Thérèse"}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["slug"] == "ste-therese"
    assert body.get("generated_username") is None
    assert body.get("generated_password") is None


def test_admin_creates_section_with_combined_account(client, admin_user, roles):
    token = _login(client, "admin", "AdminPass1")
    resp = client.post(
        "/api/v1/sections",
        headers=auth_headers(token),
        json={"slug": "ste-rita", "name": "Sainte-Rita", "username": "sainte-rita"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["generated_username"] == "sainte-rita"
    assert body["generated_password"]
    assert len(body["generated_password"]) >= 8

    # Le compte généré permet réellement de se connecter, rattaché à la
    # bonne section et avec le mot de passe donné une seule fois.
    login = client.post(
        "/api/v1/auth/login", json={"username": "sainte-rita", "password": body["generated_password"]}
    )
    assert login.status_code == 200, login.text

    section_token = login.json()["access_token"]
    me = client.get("/api/v1/sections/" + body["id"], headers=auth_headers(section_token))
    assert me.status_code == 200


def test_combined_creation_rejects_duplicate_username(client, admin_user, roles, section_user_nda):
    token = _login(client, "admin", "AdminPass1")
    resp = client.post(
        "/api/v1/sections",
        headers=auth_headers(token),
        json={"slug": "doublon", "name": "Section Doublon", "username": "nda"},
    )
    assert resp.status_code == 409

    # La section elle-même ne doit pas avoir été créée non plus (opération
    # atomique : pas de section "orpheline" sans son compte).
    listing = client.get("/api/v1/sections", headers=auth_headers(token))
    assert all(s["slug"] != "doublon" for s in listing.json())


def test_combined_creation_rejects_duplicate_slug(client, admin_user, roles, section_nda):
    token = _login(client, "admin", "AdminPass1")
    resp = client.post(
        "/api/v1/sections",
        headers=auth_headers(token),
        json={"slug": "nda", "name": "Autre nom", "username": "autre-compte"},
    )
    assert resp.status_code == 409


def test_section_account_cannot_create_sections(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    resp = client.post(
        "/api/v1/sections", headers=auth_headers(token), json={"slug": "interdit", "name": "Interdit"}
    )
    assert resp.status_code == 403
