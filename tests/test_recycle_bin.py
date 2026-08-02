import pytest
import io

def test_soft_delete_and_recycle_bin(client, token_user_a):
    auth_headers = {"Authorization": f"Bearer {token_user_a}"}

    # 1. Upload file
    upload_res = client.post(
        "/api/v1/files/upload",
        files={"file": ("recycle_test.txt", io.BytesIO(b"Recycle Bin Test Content"), "text/plain")},
        headers=auth_headers
    )
    assert upload_res.status_code == 201
    file_data = upload_res.json()
    file_id = file_data["id"]

    # 2. Verify file is in active files list
    list_res = client.get("/api/v1/files", headers=auth_headers)
    assert list_res.status_code == 200
    active_ids = [f["id"] for f in list_res.json()]
    assert file_id in active_ids

    # 3. Soft Delete file (Move to Recycle Bin)
    del_res = client.delete(f"/api/v1/files/{file_id}", headers=auth_headers)
    assert del_res.status_code == 204

    # 4. Verify file disappeared from active list
    list_after_res = client.get("/api/v1/files", headers=auth_headers)
    assert file_id not in [f["id"] for f in list_after_res.json()]

    # 5. Verify file appears in Recycle Bin (/files/trash)
    trash_res = client.get("/api/v1/files/trash", headers=auth_headers)
    assert trash_res.status_code == 200
    trash_ids = [f["id"] for f in trash_res.json()]
    assert file_id in trash_ids

    # 6. Restore File
    restore_res = client.post(f"/api/v1/files/{file_id}/restore", headers=auth_headers)
    assert restore_res.status_code == 200
    assert restore_res.json()["is_deleted"] is False

    # 7. Verify file is back in active list and gone from trash
    list_restored_res = client.get("/api/v1/files", headers=auth_headers)
    assert file_id in [f["id"] for f in list_restored_res.json()]

    trash_after_restore = client.get("/api/v1/files/trash", headers=auth_headers)
    assert file_id not in [f["id"] for f in trash_after_restore.json()]

    # 8. Move to trash again and test permanent deletion
    client.delete(f"/api/v1/files/{file_id}", headers=auth_headers)
    purge_res = client.delete(f"/api/v1/files/{file_id}/permanent", headers=auth_headers)
    assert purge_res.status_code == 204

    # 9. Verify gone from everywhere
    trash_final = client.get("/api/v1/files/trash", headers=auth_headers)
    assert file_id not in [f["id"] for f in trash_final.json()]

def test_empty_recycle_bin(client, token_user_a):
    auth_headers = {"Authorization": f"Bearer {token_user_a}"}

    # Upload 2 files and soft delete both
    f1 = client.post("/api/v1/files/upload", files={"file": ("f1.txt", io.BytesIO(b"Data 1"), "text/plain")}, headers=auth_headers).json()["id"]
    f2 = client.post("/api/v1/files/upload", files={"file": ("f2.txt", io.BytesIO(b"Data 2"), "text/plain")}, headers=auth_headers).json()["id"]

    client.delete(f"/api/v1/files/{f1}", headers=auth_headers)
    client.delete(f"/api/v1/files/{f2}", headers=auth_headers)

    trash_before = client.get("/api/v1/files/trash", headers=auth_headers).json()
    assert len(trash_before) >= 2

    # Empty trash
    empty_res = client.delete("/api/v1/files/trash/empty", headers=auth_headers)
    assert empty_res.status_code == 200
    assert empty_res.json()["count"] >= 2

    # Verify trash is empty
    trash_after = client.get("/api/v1/files/trash", headers=auth_headers).json()
    assert len(trash_after) == 0
