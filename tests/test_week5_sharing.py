import io
import pytest
from datetime import datetime, timedelta

def test_file_sharing_flow_permissions_and_limits(client, user_a, user_b, token_user_a, token_user_b):
    # 1. User A uploads file
    content = b"Shared document data 123"
    file = ("shared_doc.pdf", io.BytesIO(content), "application/pdf")
    res_up = client.post(
        "/api/v1/files/upload",
        files={"file": file},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    file_id = res_up.json()["id"]

    # 2. User A shares file with User B (max_downloads = 2)
    res_share = client.post(
        "/api/v1/shares",
        json={
            "file_id": file_id,
            "target_user_identifier": user_b.email,
            "permission": "DOWNLOAD",
            "max_downloads": 2
        },
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res_share.status_code == 201
    share_id = res_share.json()["id"]
    share_token = res_share.json()["share_token"]
    assert share_token is not None

    # 3. User B downloads 1st time -> ALLOWED
    dl1 = client.get(f"/api/v1/shares/{share_id}/download", headers={"Authorization": f"Bearer {token_user_b}"})
    assert dl1.status_code == 200
    assert dl1.content == content

    # 4. User B downloads 2nd time -> ALLOWED
    dl2 = client.get(f"/api/v1/shares/{share_id}/download", headers={"Authorization": f"Bearer {token_user_b}"})
    assert dl2.status_code == 200

    # 5. User B downloads 3rd time -> BLOCKED (download limit 2 reached)
    dl3 = client.get(f"/api/v1/shares/{share_id}/download", headers={"Authorization": f"Bearer {token_user_b}"})
    assert dl3.status_code == 403
    assert "limit" in dl3.json()["detail"].lower()

def test_share_revocation(client, user_a, user_b, token_user_a, token_user_b):
    # Upload & Share
    res_up = client.post(
        "/api/v1/files/upload",
        files={"file": ("to_revoke.txt", io.BytesIO(b"revocable content"), "text/plain")},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    file_id = res_up.json()["id"]

    res_share = client.post(
        "/api/v1/shares",
        json={"file_id": file_id, "target_user_identifier": user_b.email, "permission": "DOWNLOAD"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    share_id = res_share.json()["id"]

    # User A revokes share
    res_revoke = client.delete(f"/api/v1/shares/{share_id}/revoke", headers={"Authorization": f"Bearer {token_user_a}"})
    assert res_revoke.status_code == 200

    # User B attempts download -> BLOCKED
    res_dl = client.get(f"/api/v1/shares/{share_id}/download", headers={"Authorization": f"Bearer {token_user_b}"})
    assert res_dl.status_code == 403
    assert "revoked" in res_dl.json()["detail"].lower()

def test_wrong_recipient_access_blocked(client, user_a, user_b, token_user_a, token_user_b):
    # User A uploads file
    res_up = client.post(
        "/api/v1/files/upload",
        files={"file": ("private.pdf", io.BytesIO(b"private content"), "application/pdf")},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    file_id = res_up.json()["id"]

    # User A shares with user_a's secondary email, NOT user_b
    res_share = client.post(
        "/api/v1/shares",
        json={"file_id": file_id, "target_user_identifier": "usera_other@secure.local", "permission": "DOWNLOAD"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    share_id = res_share.json()["id"]

    # User B attempts to access share meant for usera_other -> BLOCKED
    res_dl = client.get(f"/api/v1/shares/{share_id}/download", headers={"Authorization": f"Bearer {token_user_b}"})
    assert res_dl.status_code == 403
    assert "not the authorized recipient" in res_dl.json()["detail"].lower()

def test_expired_share_blocked(client, user_a, user_b, token_user_a, token_user_b):
    # User A uploads file
    res_up = client.post(
        "/api/v1/files/upload",
        files={"file": ("expire_doc.txt", io.BytesIO(b"expiring content"), "text/plain")},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    file_id = res_up.json()["id"]

    # Share with past expiry date
    past_date = (datetime.utcnow() - timedelta(hours=2)).isoformat()
    res_share = client.post(
        "/api/v1/shares",
        json={"file_id": file_id, "target_user_identifier": user_b.email, "permission": "DOWNLOAD", "expiry_date": past_date},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    share_id = res_share.json()["id"]

    # Access attempts -> BLOCKED (expired)
    res_dl = client.get(f"/api/v1/shares/{share_id}/download", headers={"Authorization": f"Bearer {token_user_b}"})
    assert res_dl.status_code == 403
    assert "expired" in res_dl.json()["detail"].lower()

def test_password_protected_share(client, user_a, token_user_a, token_user_b):
    # Upload file
    res_up = client.post(
        "/api/v1/files/upload",
        files={"file": ("pwd_protected.txt", io.BytesIO(b"secret payload"), "text/plain")},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    file_id = res_up.json()["id"]

    # Create password-protected share link
    res_share = client.post(
        "/api/v1/shares",
        json={"file_id": file_id, "permission": "DOWNLOAD", "password": "SecretPassword123!"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    share_token = res_share.json()["share_token"]

    # Token lookup without password -> 401
    res_info = client.get(f"/api/v1/shares/token/{share_token}")
    assert res_info.status_code == 401

    # Token lookup with wrong password -> 401
    res_wrong = client.get(f"/api/v1/shares/token/{share_token}?password=WrongPassword")
    assert res_wrong.status_code == 401

    # Token lookup with correct password -> 200
    res_correct = client.get(f"/api/v1/shares/token/{share_token}?password=SecretPassword123!")
    assert res_correct.status_code == 200

def test_invalid_token_handling(client):
    res = client.get("/api/v1/shares/token/non_existent_invalid_token_123")
    assert res.status_code == 404

def test_deleted_file_share(client, user_a, user_b, token_user_a, token_user_b):
    # Upload file
    res_up = client.post(
        "/api/v1/files/upload",
        files={"file": ("delete_me.txt", io.BytesIO(b"temp data"), "text/plain")},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    file_id = res_up.json()["id"]

    # Share file
    res_share = client.post(
        "/api/v1/shares",
        json={"file_id": file_id, "target_user_identifier": user_b.email, "permission": "DOWNLOAD"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    share_id = res_share.json()["id"]

    # Owner deletes file
    client.delete(f"/api/v1/files/{file_id}", headers={"Authorization": f"Bearer {token_user_a}"})

    # Recipient attempts download -> 404 deleted
    res_dl = client.get(f"/api/v1/shares/{share_id}/download", headers={"Authorization": f"Bearer {token_user_b}"})
    assert res_dl.status_code == 404
    assert "deleted" in res_dl.json()["detail"].lower()

def test_share_update_controls(client, user_a, user_b, token_user_a, token_user_b):
    # Upload & share with VIEW permission
    res_up = client.post(
        "/api/v1/files/upload",
        files={"file": ("update_test.txt", io.BytesIO(b"data to update"), "text/plain")},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    file_id = res_up.json()["id"]

    res_share = client.post(
        "/api/v1/shares",
        json={"file_id": file_id, "target_user_identifier": user_b.email, "permission": "VIEW"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    share_id = res_share.json()["id"]

    # Download blocked with VIEW permission
    res_dl1 = client.get(f"/api/v1/shares/{share_id}/download", headers={"Authorization": f"Bearer {token_user_b}"})
    assert res_dl1.status_code == 403

    # Owner updates permission to DOWNLOAD
    res_upd = client.put(
        f"/api/v1/shares/{share_id}",
        json={"permission": "DOWNLOAD", "max_downloads": 5},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res_upd.status_code == 200
    assert res_upd.json()["permission"] == "DOWNLOAD"

    # Download now ALLOWED
    res_dl2 = client.get(f"/api/v1/shares/{share_id}/download", headers={"Authorization": f"Bearer {token_user_b}"})
    assert res_dl2.status_code == 200
