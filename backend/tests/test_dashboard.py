import io

from tests.conftest import MINIMAL_PDF_BYTES


def _login(client, username, password):
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _upload(client, token, *, name, category_id, filename="rapport.pdf"):
    data = {"name": name, "category_id": str(category_id)}
    files = {"file": (filename, io.BytesIO(MINIMAL_PDF_BYTES), "application/pdf")}
    return client.post("/api/v1/documents", headers=auth_headers(token), data=data, files=files)


# ---------------------------------------------------------------------------
# Dashboard admin
# ---------------------------------------------------------------------------

def test_admin_dashboard_reflects_real_counts(
    client, admin_user, section_user_nda, section_user_stmarc, section_nda, section_stmarc, doc_category
):
    admin_token = _login(client, "admin", "AdminPass1")
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")

    doc1 = _upload(client, nda_token, name="Doc NDA 1", category_id=doc_category.id).json()
    _upload(client, stmarc_token, name="Doc Saint-Marc 1", category_id=doc_category.id)
    client.post(f"/api/v1/documents/{doc1['id']}/approve", headers=auth_headers(admin_token))

    resp = client.get("/api/v1/dashboard/admin", headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    stats = resp.json()

    assert stats["sections_count"] == 2
    assert stats["users_count"] == 3  # admin + 2 sections
    assert stats["documents_count"] == 2
    assert stats["documents_pending_count"] == 1
    assert stats["documents_published_count"] == 1
    assert len(stats["recent_documents"]) == 2
    assert len(stats["pending_documents"]) == 1

    breakdown = {b["section_name"]: b for b in stats["sections_breakdown"]}
    assert breakdown["Notre-Dame de l'Annonciation"]["documents_count"] == 1
    assert breakdown["Saint-Marc"]["documents_count"] == 1
    assert breakdown["Saint-Marc"]["documents_pending_count"] == 1


def test_section_user_cannot_access_admin_dashboard(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    resp = client.get("/api/v1/dashboard/admin", headers=auth_headers(token))
    assert resp.status_code == 403


def test_admin_dashboard_requires_authentication(client):
    resp = client.get("/api/v1/dashboard/admin")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Dashboard section — isolation
# ---------------------------------------------------------------------------

def test_section_dashboard_shows_only_own_data(
    client, section_user_nda, section_user_stmarc, doc_category
):
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")

    _upload(client, nda_token, name="Doc NDA", category_id=doc_category.id)
    _upload(client, stmarc_token, name="Doc Saint-Marc 1", category_id=doc_category.id)
    _upload(client, stmarc_token, name="Doc Saint-Marc 2", category_id=doc_category.id, filename="r2.pdf")

    resp = client.get("/api/v1/dashboard/section", headers=auth_headers(nda_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["documents_count"] == 1
    assert body["section_name"] == "Notre-Dame de l'Annonciation"


def test_section_dashboard_ignores_spoofed_section_id(
    client, section_user_nda, section_user_stmarc, doc_category
):
    """Saint-Marc ne doit jamais pouvoir lire les stats de NDA en trafiquant ?section_id=."""
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")

    _upload(client, nda_token, name="Doc privé NDA", category_id=doc_category.id)

    resp = client.get(
        f"/api/v1/dashboard/section?section_id={section_user_nda.section_id}",
        headers=auth_headers(stmarc_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    # Toujours les stats de Saint-Marc (sa propre section), jamais celles de NDA.
    assert body["section_name"] == "Saint-Marc"
    assert body["documents_count"] == 0


def test_admin_can_view_any_section_dashboard_with_explicit_id(client, admin_user, section_user_nda, doc_category):
    admin_token = _login(client, "admin", "AdminPass1")
    resp = client.get(
        f"/api/v1/dashboard/section?section_id={section_user_nda.section_id}",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["section_name"] == "Notre-Dame de l'Annonciation"


def test_admin_section_dashboard_requires_section_id(client, admin_user):
    admin_token = _login(client, "admin", "AdminPass1")
    resp = client.get("/api/v1/dashboard/section", headers=auth_headers(admin_token))
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def test_admin_receives_notification_on_document_submission(client, admin_user, section_user_nda, doc_category):
    admin_token = _login(client, "admin", "AdminPass1")
    nda_token = _login(client, "nda", "SectionPass1")

    _upload(client, nda_token, name="Nouveau document", category_id=doc_category.id)

    resp = client.get("/api/v1/notifications", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["unread_count"] == 1
    assert body["items"][0]["type"] == "DOCUMENT_SUBMITTED"


def test_section_user_does_not_see_admin_notifications(client, admin_user, section_user_nda, doc_category):
    nda_token = _login(client, "nda", "SectionPass1")
    _upload(client, nda_token, name="Doc", category_id=doc_category.id)

    resp = client.get("/api/v1/notifications", headers=auth_headers(nda_token))
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_user_can_mark_own_notification_read_but_not_others(
    client, admin_user, section_user_nda, section_user_stmarc, doc_category
):
    admin_token = _login(client, "admin", "AdminPass1")
    nda_token = _login(client, "nda", "SectionPass1")
    stmarc_token = _login(client, "stmarc", "SectionPass1")

    _upload(client, nda_token, name="Doc", category_id=doc_category.id)
    notif_id = client.get("/api/v1/notifications", headers=auth_headers(admin_token)).json()["items"][0]["id"]

    # Saint-Marc ne peut pas marquer comme lue une notification qui ne lui appartient pas.
    forbidden = client.put(f"/api/v1/notifications/{notif_id}/read", headers=auth_headers(stmarc_token))
    assert forbidden.status_code == 404

    ok = client.put(f"/api/v1/notifications/{notif_id}/read", headers=auth_headers(admin_token))
    assert ok.status_code == 200
    assert ok.json()["is_read"] is True


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------

def test_admin_can_view_audit_logs(client, admin_user, section_user_nda, doc_category):
    admin_token = _login(client, "admin", "AdminPass1")
    nda_token = _login(client, "nda", "SectionPass1")

    _upload(client, nda_token, name="Doc audité", category_id=doc_category.id)

    resp = client.get("/api/v1/audit-logs", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    actions = [item["action"] for item in body["items"]]
    assert "DOCUMENT_UPLOAD" in actions or any("DOCUMENT" in a for a in actions)


def test_section_user_cannot_view_audit_logs(client, section_user_nda):
    token = _login(client, "nda", "SectionPass1")
    resp = client.get("/api/v1/audit-logs", headers=auth_headers(token))
    assert resp.status_code == 403


def test_audit_logs_requires_authentication(client):
    resp = client.get("/api/v1/audit-logs")
    assert resp.status_code == 401
