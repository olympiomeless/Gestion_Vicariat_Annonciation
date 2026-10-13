def test_login_success(client, admin_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "AdminPass1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["role"] == "ADMIN"
    assert "access_token" in body
    assert "vicariat_refresh_token" in resp.cookies


def test_login_wrong_password(client, admin_user):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_login_unknown_email(client, roles):
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "whatever123"},
    )
    assert resp.status_code == 401


def test_login_inactive_account(client, db_session, roles):
    from tests.conftest import make_user

    make_user(db_session, email="inactive@vicariat-annonciation.ci", password="Passw0rd1", role=roles["ADMIN"], is_active=False)
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "inactive", "password": "Passw0rd1"},
    )
    assert resp.status_code == 401
    assert "désactivé" in resp.json()["detail"]


def test_me_requires_token(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_with_valid_token(client, admin_user):
    login = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "AdminPass1"}
    ).json()
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {login['access_token']}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@vicariat-annonciation.ci"


def test_me_with_garbage_token_rejected(client):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


def test_refresh_rotates_and_old_refresh_fails(client, admin_user):
    client.post("/api/v1/auth/login", json={"username": "admin", "password": "AdminPass1"})
    old_cookie = client.cookies.get("vicariat_refresh_token")

    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    new_cookie = client.cookies.get("vicariat_refresh_token")
    assert new_cookie != old_cookie

    # Rejouer l'ancien refresh token doit échouer (rotation + révocation)
    client.cookies.set("vicariat_refresh_token", old_cookie)
    replay = client.post("/api/v1/auth/refresh")
    assert replay.status_code == 401


def test_logout_revokes_session(client, admin_user):
    client.post("/api/v1/auth/login", json={"username": "admin", "password": "AdminPass1"})
    logout_resp = client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 204

    after_logout = client.post("/api/v1/auth/refresh")
    assert after_logout.status_code == 401


def test_rate_limit_on_login(client, admin_user):
    for _ in range(5):
        client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
    blocked = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert blocked.status_code == 429


def test_forgot_and_reset_password_flow(client, admin_user):
    forgot = client.post("/api/v1/auth/forgot-password", json={"email": "admin@vicariat-annonciation.ci"})
    assert forgot.status_code == 202
    token = forgot.json()["dev_reset_token"]

    weak = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "weak"})
    assert weak.status_code == 422

    ok = client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "NewPassw0rd"})
    assert ok.status_code == 204

    old_login = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "AdminPass1"}
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "NewPassw0rd"}
    )
    assert new_login.status_code == 200


def test_forgot_password_unknown_email_same_response(client, roles):
    resp = client.post("/api/v1/auth/forgot-password", json={"email": "ghost@vicariat-annonciation.ci"})
    assert resp.status_code == 202
    assert "dev_reset_token" not in resp.json()


def test_reset_password_with_invalid_token_rejected(client, admin_user):
    resp = client.post("/api/v1/auth/reset-password", json={"token": "not-a-real-token", "new_password": "NewPassw0rd"})
    assert resp.status_code == 400
