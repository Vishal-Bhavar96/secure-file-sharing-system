import io
import pytest

def test_delete_twice_handling(client, token_user_a):
    # Upload file
    res_up = client.post(
        "/api/v1/files/upload",
        files={"file": ("double_delete.txt", io.BytesIO(b"data"), "text/plain")},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    file_id = res_up.json()["id"]

    # First delete -> 204
    del1 = client.delete(f"/api/v1/files/{file_id}", headers={"Authorization": f"Bearer {token_user_a}"})
    assert del1.status_code == 204

    # Second delete -> 404
    del2 = client.delete(f"/api/v1/files/{file_id}", headers={"Authorization": f"Bearer {token_user_a}"})
    assert del2.status_code == 404

def test_share_twice_idempotency(client, user_a, user_b, token_user_a):
    # Upload file
    res_up = client.post(
        "/api/v1/files/upload",
        files={"file": ("share_twice.txt", io.BytesIO(b"data"), "text/plain")},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    file_id = res_up.json()["id"]

    # Share 1
    s1 = client.post(
        "/api/v1/shares",
        json={"file_id": file_id, "target_user_identifier": user_b.email, "permission": "VIEW"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert s1.status_code == 201

    # Share 2 (Updates permission seamlessly to DOWNLOAD)
    s2 = client.post(
        "/api/v1/shares",
        json={"file_id": file_id, "target_user_identifier": user_b.email, "permission": "DOWNLOAD"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert s2.status_code == 201
    assert s2.json()["permission"] == "DOWNLOAD"
