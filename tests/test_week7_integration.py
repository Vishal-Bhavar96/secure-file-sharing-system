import io
import pytest

def test_full_system_integration_flow(client):
    # Step 1: Register User X
    res_reg_x = client.post("/api/v1/auth/register", json={
        "name": "Integration User X",
        "email": "userx_integ@secure.local",
        "username": "userx_integ",
        "password": "ValidPassword123!"
    })
    assert res_reg_x.status_code == 201

    # Step 2: Register User Y
    res_reg_y = client.post("/api/v1/auth/register", json={
        "name": "Integration User Y",
        "email": "usery_integ@secure.local",
        "username": "usery_integ",
        "password": "ValidPassword123!"
    })
    assert res_reg_y.status_code == 201

    # Step 3: Login User X
    res_log_x = client.post("/api/v1/auth/login", json={
        "email": "userx_integ@secure.local",
        "password": "ValidPassword123!"
    })
    assert res_log_x.status_code == 200
    token_x = res_log_x.json()["access_token"]

    # Step 4: Login User Y
    res_log_y = client.post("/api/v1/auth/login", json={
        "email": "usery_integ@secure.local",
        "password": "ValidPassword123!"
    })
    assert res_log_y.status_code == 200
    token_y = res_log_y.json()["access_token"]

    # Step 5: User X Uploads File
    file_bytes = b"End to end integration test payload 2026"
    res_up = client.post(
        "/api/v1/files/upload",
        files={"file": ("integ_file.txt", io.BytesIO(file_bytes), "text/plain")},
        headers={"Authorization": f"Bearer {token_x}"}
    )
    assert res_up.status_code == 201
    file_id = res_up.json()["id"]

    # Step 6: User X Shares File with User Y
    res_share = client.post(
        "/api/v1/shares",
        json={
            "file_id": file_id,
            "target_user_identifier": "usery_integ@secure.local",
            "permission": "DOWNLOAD"
        },
        headers={"Authorization": f"Bearer {token_x}"}
    )
    assert res_share.status_code == 201
    share_id = res_share.json()["id"]

    # Step 7: User Y Downloads Shared File
    res_dl = client.get(
        f"/api/v1/shares/{share_id}/download",
        headers={"Authorization": f"Bearer {token_y}"}
    )
    assert res_dl.status_code == 200
    assert res_dl.content == file_bytes

    # Step 8: Check User Y's Audit Logs
    res_audit = client.get("/api/v1/audit/logs", headers={"Authorization": f"Bearer {token_y}"})
    assert res_audit.status_code == 200
    assert len(res_audit.json()) > 0
