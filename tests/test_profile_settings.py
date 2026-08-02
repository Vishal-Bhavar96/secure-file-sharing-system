import io
import pytest
from app.models.audit_log import AuditLog, AuditAction

def test_get_profile(client, token_user_a):
    res = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token_user_a}"})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "alice_test@secure.local"
    assert data["has_avatar"] is False
    assert data["theme_preference"] == "dark"

def test_update_profile_name(client, token_user_a):
    res = client.put(
        "/api/v1/users/me/profile",
        json={"name": "Alice Smith"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Alice Smith"

def test_upload_and_remove_avatar(client, token_user_a):
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01Haf\x01\x00\x00\x00\x00IEND\xaeB`\x82"
    file = ("avatar.png", io.BytesIO(png_bytes), "image/png")

    res_upload = client.post(
        "/api/v1/users/me/avatar",
        files={"file": file},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res_upload.status_code == 200
    assert res_upload.json()["has_avatar"] is True

    res_get = client.get("/api/v1/users/me/avatar", headers={"Authorization": f"Bearer {token_user_a}"})
    assert res_get.status_code == 200
    assert len(res_get.content) > 0

    res_del = client.delete("/api/v1/users/me/avatar", headers={"Authorization": f"Bearer {token_user_a}"})
    assert res_del.status_code == 200
    assert res_del.json()["has_avatar"] is False

def test_upload_avatar_invalid_format(client, token_user_a):
    file = ("script.sh", io.BytesIO(b"echo hello"), "text/plain")
    res = client.post(
        "/api/v1/users/me/avatar",
        files={"file": file},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res.status_code == 400
    assert "Allowed formats" in res.json()["detail"]

def test_change_email(client, token_user_a):
    res_err = client.post(
        "/api/v1/users/me/email",
        json={"current_password": "WrongPassword!", "new_email": "alice_new@secure.local", "confirm_new_email": "alice_new@secure.local"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res_err.status_code == 400
    assert "Incorrect current password" in res_err.json()["detail"]

    res_ok = client.post(
        "/api/v1/users/me/email",
        json={"current_password": "ValidPass123!", "new_email": "alice_new@secure.local", "confirm_new_email": "alice_new@secure.local"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["email"] == "alice_new@secure.local"

def test_change_password(client, token_user_a):
    res_weak = client.post(
        "/api/v1/users/me/password",
        json={"current_password": "ValidPass123!", "new_password": "weak", "confirm_new_password": "weak"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res_weak.status_code in (400, 422)

    res_ok = client.post(
        "/api/v1/users/me/password",
        json={"current_password": "ValidPass123!", "new_password": "NewSecretPass123!", "confirm_new_password": "NewSecretPass123!"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["last_password_change_at"] is not None

def test_update_preferences(client, token_user_a):
    res = client.put(
        "/api/v1/users/me/preferences",
        json={"theme_preference": "light", "default_file_sort": "name_asc", "items_per_page": 25},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["theme_preference"] == "light"
    assert data["default_file_sort"] == "name_asc"
    assert data["items_per_page"] == 25

def test_sessions_and_revocation(client, user_a):
    # Log in to create a session record
    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": user_a.email, "password": "ValidPass123!"}
    )
    token = res_login.json()["access_token"]

    res_sessions = client.get("/api/v1/users/me/sessions", headers={"Authorization": f"Bearer {token}"})
    assert res_sessions.status_code == 200
    assert len(res_sessions.json()) > 0

    res_revoke = client.post("/api/v1/users/me/sessions/revoke-others", headers={"Authorization": f"Bearer {token}"})
    assert res_revoke.status_code == 200
    assert "count" in res_revoke.json()

def test_audit_logs_for_profile_actions(client, token_user_a, db):
    client.put(
        "/api/v1/users/me/profile",
        json={"name": "Alice Audit Test"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    audit = db.query(AuditLog).filter(AuditLog.action == AuditAction.PROFILE_UPDATED).first()
    assert audit is not None
    assert "Alice Audit Test" in audit.details
