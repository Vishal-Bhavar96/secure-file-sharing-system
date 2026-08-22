import io
import pytest

def test_student_to_student_password_protected_share_flow(client, user_a, user_b, token_user_a, token_user_b):
    # 1. Student A uploads a secure file
    file_content = b"Confidential assignment notes for Vicky from Vishal"
    files = {"file": ("Assignment_Notes.txt", io.BytesIO(file_content), "text/plain")}
    res_upload = client.post(
        "/api/v1/files/upload",
        files=files,
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res_upload.status_code == 201
    file_id = res_upload.json()["id"]

    # 2. Student A shares the file with Vicky using email and password
    share_pwd = "VickySecretPass123!"
    res_share = client.post(
        "/api/v1/shares",
        headers={"Authorization": f"Bearer {token_user_a}"},
        json={
            "file_id": file_id,
            "target_user_identifier": user_b.email,
            "permission": "DOWNLOAD",
            "requires_password": True,
            "password": share_pwd,
            "max_downloads": 5
        }
    )
    assert res_share.status_code == 201
    share_data = res_share.json()
    share_id = share_data["id"]
    share_token = share_data["share_token"]
    assert share_data["requires_password"] is True
    assert share_data["has_password"] is True

    # 3. Student B logs in and checks "Shared With Me" inbox (/api/v1/shares/received)
    res_received = client.get(
        "/api/v1/shares/received",
        headers={"Authorization": f"Bearer {token_user_b}"}
    )
    assert res_received.status_code == 200
    received_shares = res_received.json()
    assert len(received_shares) >= 1
    rec_share = next(s for s in received_shares if s["id"] == share_id)
    assert rec_share["filename"] == "Assignment_Notes.txt"
    assert rec_share["requires_password"] is True
    assert rec_share["has_password"] is True

    # 4. Student B tries to download without password -> should be 401 Unauthorized
    res_dl_no_pwd = client.get(
        f"/api/v1/shares/{share_id}/download",
        headers={"Authorization": f"Bearer {token_user_b}"}
    )
    assert res_dl_no_pwd.status_code == 401
    assert "password" in res_dl_no_pwd.json()["detail"].lower()

    # 5. Student B tries to download with incorrect password -> should be 401 Unauthorized
    res_dl_wrong_pwd = client.get(
        f"/api/v1/shares/{share_id}/download?password=WrongPassword",
        headers={"Authorization": f"Bearer {token_user_b}"}
    )
    assert res_dl_wrong_pwd.status_code == 401

    # 6. Student B downloads with correct password -> should succeed with decrypted file bytes
    res_dl_ok = client.get(
        f"/api/v1/shares/{share_id}/download?password={share_pwd}",
        headers={"Authorization": f"Bearer {token_user_b}"}
    )
    assert res_dl_ok.status_code == 200
    assert res_dl_ok.content == file_content

    # 7. Student B views / previews with correct password
    res_preview_ok = client.get(
        f"/api/v1/shares/{share_id}/preview?password={share_pwd}",
        headers={"Authorization": f"Bearer {token_user_b}"}
    )
    assert res_preview_ok.status_code == 200
    preview_json = res_preview_ok.json()
    assert preview_json["preview_type"] == "text"
    assert "Confidential assignment notes" in preview_json["text_content"]

    # 8. Direct link access by share token with password
    res_token_dl = client.get(f"/api/v1/shares/token/{share_token}/download?password={share_pwd}")
    assert res_token_dl.status_code == 200
    assert res_token_dl.content == file_content
