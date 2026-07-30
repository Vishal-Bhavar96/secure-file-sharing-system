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
