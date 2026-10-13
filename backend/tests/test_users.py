import io

from tests.conftest import MINIMAL_PDF_BYTES


def _login(client, username, password):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_create_section_user(client, admin_user, section_nda):
    token = _login(client, admin_user.username, "AdminPass1")
    resp = client.post(
        "/api/v1/users",
        headers=auth_headers(token),
        json={
            "username": "nouveau",
            "email": "nouveau@vicariat-annonciation.ci",
            "full_name": "Nouveau Responsable",
            "password": "NouveauPass1",
            "role": "SECTION",
            "section_id": str(section_nda.id),
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["role"] == "SECTION"
    assert body["section_id"] == str(section_nda.id)
    assert body["is_active"] is True

    # Le compte créé doit pouvoir se connecter immédiatement.
    login_resp = client.post("/api/v1/auth/login", json={"username": "nouveau", "password": "NouveauPass1"})
    assert login_resp.status_code == 200


def test_section_cannot_create_users(client, section_user_nda):
    token = _login(client, section_user_nda.username, "SectionPass1")
    resp = client.post(
        "/api/v1/users",
        headers=auth_headers(token),
        json={"username": "x", "email": "x@example.com", "full_name": "X", "password": "SomePass123", "role": "SECTION"},
    )
    assert resp.status_code == 403


def test_admin_deactivate_prevents_login_then_reactivate_restores_it(client, admin_user, section_user_nda):
    token = _login(client, admin_user.username, "AdminPass1")

    resp = client.post(f"/api/v1/users/{section_user_nda.id}/deactivate", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    blocked = client.post("/api/v1/auth/login", json={"username": section_user_nda.username, "password": "SectionPass1"})
    assert blocked.status_code in (400, 401)

    resp = client.post(f"/api/v1/users/{section_user_nda.id}/reactivate", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["is_active"] is True

    restored = client.post("/api/v1/auth/login", json={"username": section_user_nda.username, "password": "SectionPass1"})
    assert restored.status_code == 200


def test_admin_reset_password_lets_user_log_in_with_new_password(client, admin_user, section_user_nda):
    token = _login(client, admin_user.username, "AdminPass1")
    resp = client.post(
        f"/api/v1/users/{section_user_nda.id}/reset-password",
        headers=auth_headers(token),
        json={"new_password": "BrandNewPass1"},
    )
    assert resp.status_code == 204

    old = client.post("/api/v1/auth/login", json={"username": section_user_nda.username, "password": "SectionPass1"})
    assert old.status_code in (400, 401)
    new = client.post("/api/v1/auth/login", json={"username": section_user_nda.username, "password": "BrandNewPass1"})
    assert new.status_code == 200


def test_admin_can_delete_user_with_no_content_or_history(client, admin_user, section_user_nda):
    token = _login(client, admin_user.username, "AdminPass1")
    resp = client.delete(f"/api/v1/users/{section_user_nda.id}", headers=auth_headers(token))
    assert resp.status_code == 204


def test_admin_delete_user_who_has_logged_in_still_works(client, admin_user, section_user_nda):
    """
    Se connecter crée un refresh token (session). La suppression du compte ne
    doit pas échouer à cause de cette ligne d'historique de session : elle
    doit disparaître avec le compte (ON DELETE CASCADE).
    """
    token = _login(client, admin_user.username, "AdminPass1")
    _login(client, section_user_nda.username, "SectionPass1")  # crée un refresh_token pour section_user_nda

    resp = client.delete(f"/api/v1/users/{section_user_nda.id}", headers=auth_headers(token))
    assert resp.status_code == 204


def test_admin_cannot_hard_delete_user_who_authored_content_must_deactivate_instead(
    client, admin_user, section_user_nda, doc_category
):
    """
    Un compte auteur d'un document ne doit jamais pouvoir être supprimé
    définitivement : cela perdrait la propriété/l'historique du document. Le
    contenu et son auteur doivent survivre ; l'API doit refuser proprement
    (409) et orienter vers la désactivation, jamais planter avec une erreur
    d'intégrité de base de données.
    """
    section_token = _login(client, section_user_nda.username, "SectionPass1")
    upload = client.post(
        "/api/v1/documents",
        headers=auth_headers(section_token),
        data={"name": "Rapport NDA", "category_id": str(doc_category.id)},
        files={"file": ("rapport.pdf", io.BytesIO(MINIMAL_PDF_BYTES), "application/pdf")},
    )
    assert upload.status_code == 201, upload.text

    admin_token = _login(client, admin_user.username, "AdminPass1")
    resp = client.delete(f"/api/v1/users/{section_user_nda.id}", headers=auth_headers(admin_token))
    assert resp.status_code == 409
    assert "désactiv" in resp.json()["detail"].lower()

    # Le document et son auteur doivent être restés intacts.
    still_there = client.get("/api/v1/documents", headers=auth_headers(admin_token))
    assert still_there.json()["total"] == 1

    # La désactivation, elle, doit fonctionner sans problème pour ce même compte.
    deactivate = client.post(f"/api/v1/users/{section_user_nda.id}/deactivate", headers=auth_headers(admin_token))
    assert deactivate.status_code == 200


def test_admin_cannot_delete_own_account(client, admin_user):
    token = _login(client, admin_user.username, "AdminPass1")
    resp = client.delete(f"/api/v1/users/{admin_user.id}", headers=auth_headers(token))
    assert resp.status_code == 400


def test_list_users_is_admin_only(client, section_user_nda):
    token = _login(client, section_user_nda.username, "SectionPass1")
    resp = client.get("/api/v1/users", headers=auth_headers(token))
    assert resp.status_code == 403
