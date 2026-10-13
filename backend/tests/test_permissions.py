def _login(client, username, password):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_list_and_create_sections(client, admin_user):
    token = _login(client, "admin", "AdminPass1")
    resp = client.post(
        "/api/v1/sections",
        headers=auth_headers(token),
        json={"slug": "stsauveur", "name": "Saint-Sauveur-Miséricordieux"},
    )
    assert resp.status_code == 201, resp.text

    listing = client.get("/api/v1/sections", headers=auth_headers(token))
    assert listing.status_code == 200
    assert any(s["slug"] == "stsauveur" for s in listing.json())


def test_section_user_cannot_create_section(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    resp = client.post(
        "/api/v1/sections",
        headers=auth_headers(token),
        json={"slug": "hack", "name": "Section pirate"},
    )
    assert resp.status_code == 403


def test_section_user_can_read_sections(client, section_user_nda, section_stmarc):
    token = _login(client, "nda", "SectionPass1")
    resp = client.get("/api/v1/sections", headers=auth_headers(token))
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_section_user_cannot_list_users(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    resp = client.get("/api/v1/users", headers=auth_headers(token))
    assert resp.status_code == 403


def test_section_user_cannot_create_user(client, section_user_nda, section_stmarc):
    token = _login(client, "nda", "SectionPass1")
    resp = client.post(
        "/api/v1/users",
        headers=auth_headers(token),
        json={
            "username": "evil",
            "email": "evil@vicariat-annonciation.ci",
            "full_name": "Evil User",
            "password": "Whatever123",
            "role": "ADMIN",
        },
    )
    assert resp.status_code == 403


def test_admin_can_create_section_user_bound_to_a_section(client, admin_user, section_nda):
    token = _login(client, "admin", "AdminPass1")
    resp = client.post(
        "/api/v1/users",
        headers=auth_headers(token),
        json={
            "username": "resp.nda",
            "email": "resp.nda@vicariat-annonciation.ci",
            "full_name": "Responsable NDA",
            "password": "Passw0rd123",
            "role": "SECTION",
            "section_id": str(section_nda.id),
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["role"] == "SECTION"
    assert body["section_id"] == str(section_nda.id)


def test_section_role_requires_a_section_id(client, admin_user):
    token = _login(client, "admin", "AdminPass1")
    resp = client.post(
        "/api/v1/users",
        headers=auth_headers(token),
        json={
            "username": "orphan",
            "email": "orphan@vicariat-annonciation.ci",
            "full_name": "Orphan",
            "password": "Passw0rd123",
            "role": "SECTION",
        },
    )
    assert resp.status_code == 400


def test_admin_cannot_deactivate_own_account(client, admin_user):
    token = _login(client, "admin", "AdminPass1")
    resp = client.post(f"/api/v1/users/{admin_user.id}/deactivate", headers=auth_headers(token))
    assert resp.status_code == 400


def test_deactivated_user_loses_access_immediately(client, admin_user, section_user_nda):
    admin_token = _login(client, "admin", "AdminPass1")
    section_token = _login(client, "nda", "SectionPass1")

    # Le compte peut lire les sections tant qu'il est actif.
    ok = client.get("/api/v1/sections", headers=auth_headers(section_token))
    assert ok.status_code == 200

    deactivate = client.post(f"/api/v1/users/{section_user_nda.id}/deactivate", headers=auth_headers(admin_token))
    assert deactivate.status_code == 200

    # Le JWT déjà émis n'est pas expiré mais le compte est revérifié en base
    # à chaque requête (voir get_current_user) : l'accès doit être coupé
    # immédiatement, pas seulement à l'expiration du token.
    blocked = client.get("/api/v1/sections", headers=auth_headers(section_token))
    assert blocked.status_code == 401

    # Et il ne peut plus se reconnecter.
    relogin = client.post(
        "/api/v1/auth/login", json={"username": "nda", "password": "SectionPass1"}
    )
    assert relogin.status_code == 401


def test_unauthenticated_requests_rejected_on_every_protected_route(client):
    for method, path in [
        ("GET", "/api/v1/sections"),
        ("POST", "/api/v1/sections"),
        ("GET", "/api/v1/users"),
        ("POST", "/api/v1/users"),
    ]:
        resp = client.request(method, path, json={} if method == "POST" else None)
        assert resp.status_code == 401, f"{method} {path} devrait exiger une authentification"
