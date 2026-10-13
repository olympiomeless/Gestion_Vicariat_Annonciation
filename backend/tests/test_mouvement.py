def _login(client, username, password):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_get_mouvement_creates_default_content_on_first_call(client, admin_user):
    token = _login(client, admin_user.username, "AdminPass1")
    resp = client.get("/api/v1/mouvement", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["intro_title"] == "Un vicariat, une identité, une mission"
    assert body["aumonier_name"] == "Abbé Kablan Georges"
    assert body["rang_diocese"] == "1/13"

    # Un deuxième appel doit renvoyer la même ligne (jamais en créer une seconde).
    again = client.get("/api/v1/mouvement", headers=auth_headers(token))
    assert again.json()["id"] == body["id"]


def test_public_mouvement_needs_no_authentication_and_matches_admin_view(client, admin_user):
    public_resp = client.get("/api/v1/public/mouvement")
    assert public_resp.status_code == 200, public_resp.text
    assert public_resp.json()["theme_annee_label"] == "Thème de l'année pastorale 2025-2026 — Diocèse de Yopougon"

    # Aucune fuite de champ interne (id, updated_at) sur l'API publique.
    assert "id" not in public_resp.json()
    assert "updated_at" not in public_resp.json()


def test_admin_can_update_mouvement_content_and_public_site_sees_it(client, admin_user):
    token = _login(client, admin_user.username, "AdminPass1")
    update = client.put(
        "/api/v1/mouvement",
        headers=auth_headers(token),
        json={"intro_title": "Nouveau titre du vicariat", "aumonier_name": "Abbé Nouveau Curé", "rang_diocese": "2/13"},
    )
    assert update.status_code == 200, update.text
    assert update.json()["intro_title"] == "Nouveau titre du vicariat"
    assert update.json()["aumonier_name"] == "Abbé Nouveau Curé"
    assert update.json()["rang_diocese"] == "2/13"
    # Les champs non envoyés ne doivent pas être écrasés.
    assert update.json()["tutelle"] == "Bureau Diocésain CV-AV Yopougon"

    public_resp = client.get("/api/v1/public/mouvement")
    assert public_resp.json()["intro_title"] == "Nouveau titre du vicariat"
    assert public_resp.json()["rang_diocese"] == "2/13"


def test_section_cannot_update_mouvement_content(client, section_user_nda):
    token = _login(client, section_user_nda.username, "SectionPass1")
    resp = client.put(
        "/api/v1/mouvement", headers=auth_headers(token), json={"intro_title": "Piratage"}
    )
    assert resp.status_code == 403

    # Mais la lecture (authentifiée) reste possible pour préparer un futur espace section.
    read = client.get("/api/v1/mouvement", headers=auth_headers(token))
    assert read.status_code == 200


def test_mouvement_requires_authentication_on_admin_endpoint(client):
    resp = client.get("/api/v1/mouvement")
    assert resp.status_code == 401
