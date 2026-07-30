import io
import pytest

def test_file_upload_and_download(client, token_user_a):
    content = b"Confidential document content for Alice"
    file = ("secret.txt", io.BytesIO(content), "text/plain")

    # Upload
    res = client.post(
        "/api/v1/files/upload",
        files={"file": file},
        data={"folder": "/"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res.status_code == 201
    file_data = res.json()
    file_id = file_data["id"]
    assert file_data["original_name"] == "secret.txt"

    # Download
    res_dl = client.get(
        f"/api/v1/files/{file_id}/download",
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res_dl.status_code == 200
    assert res_dl.content == content

def test_path_traversal_defense(client, token_user_a):
    content = b"Path traversal payload test"
    file = ("../../private_file.txt", io.BytesIO(content), "text/plain")

    res = client.post(
        "/api/v1/files/upload",
        files={"file": file},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res.status_code == 201
    data = res.json()
    # File name must be sanitized
    assert ".." not in data["original_name"]
    assert data["original_name"] == "private_file.txt"

def test_empty_file_upload(client, token_user_a):
    file = ("empty.txt", io.BytesIO(b""), "text/plain")
    res = client.post(
        "/api/v1/files/upload",
        files={"file": file},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res.status_code == 400
    assert "Empty file" in res.json()["detail"]

def test_ownership_enforcement(client, token_user_a, token_user_b):
    # User A uploads a file
    content = b"Alice private file"
    file = ("alice_private.txt", io.BytesIO(content), "text/plain")
    res = client.post(
        "/api/v1/files/upload",
        files={"file": file},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    file_id = res.json()["id"]

    # User B tries to download User A's file
    res_b = client.get(
        f"/api/v1/files/{file_id}/download",
        headers={"Authorization": f"Bearer {token_user_b}"}
    )
    assert res_b.status_code == 403
    assert "forbidden" in res_b.json()["detail"].lower()
