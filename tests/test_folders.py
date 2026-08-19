import io

def test_create_folder(client, token_user_a):
    res = client.post(
        "/api/v1/files/folders",
        json={"folder_name": "Documents", "parent_folder": "/"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Documents"
    assert data["path"] == "/Documents"
    assert data["parent_folder"] == "/"

def test_create_subfolder(client, token_user_a):
    # Create parent folder
    client.post(
        "/api/v1/files/folders",
        json={"folder_name": "Projects", "parent_folder": "/"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    # Create subfolder inside /Projects
    res = client.post(
        "/api/v1/files/folders",
        json={"folder_name": "2026", "parent_folder": "/Projects"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "2026"
    assert data["path"] == "/Projects/2026"
    assert data["parent_folder"] == "/Projects"

def test_create_duplicate_folder_error(client, token_user_a):
    client.post(
        "/api/v1/files/folders",
        json={"folder_name": "Reports", "parent_folder": "/"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    # Try duplicate
    res = client.post(
        "/api/v1/files/folders",
        json={"folder_name": "Reports", "parent_folder": "/"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"].lower()

def test_list_folders(client, token_user_a):
    client.post(
        "/api/v1/files/folders",
        json={"folder_name": "Finance", "parent_folder": "/"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    res = client.get(
        "/api/v1/files/folders?parent_folder=/",
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res.status_code == 200
    folders = res.json()
    folder_names = [f["name"] for f in folders]
    assert "Finance" in folder_names

def test_move_file_between_folders(client, token_user_a):
    # Create target folder
    client.post(
        "/api/v1/files/folders",
        json={"folder_name": "Archive", "parent_folder": "/"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )

    # Upload file to root
    content = b"File content to be moved"
    file = ("move_me.txt", io.BytesIO(content), "text/plain")
    res_upload = client.post(
        "/api/v1/files/upload",
        files={"file": file},
        data={"folder": "/"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res_upload.status_code == 201
    file_id = res_upload.json()["id"]
    assert res_upload.json()["folder"] == "/"

    # Move file to /Archive
    res_move = client.post(
        f"/api/v1/files/{file_id}/move",
        json={"target_folder": "/Archive"},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    assert res_move.status_code == 200
    assert res_move.json()["folder"] == "/Archive"

    # Verify listing in / returns 0 matching this file
    res_root = client.get(
        "/api/v1/files?folder=/",
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    root_file_ids = [f["id"] for f in res_root.json()]
    assert file_id not in root_file_ids

    # Verify listing in /Archive includes this file
    res_archive = client.get(
        "/api/v1/files?folder=/Archive",
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    archive_file_ids = [f["id"] for f in res_archive.json()]
    assert file_id in archive_file_ids

def test_folder_ownership_isolation(client, token_user_a, token_user_b):
    # User A uploads a file
    file = ("secret_a.txt", io.BytesIO(b"Alice Secret"), "text/plain")
    res = client.post(
        "/api/v1/files/upload",
        files={"file": file},
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    file_id = res.json()["id"]

    # User B tries to move User A's file
    res_b = client.post(
        f"/api/v1/files/{file_id}/move",
        json={"target_folder": "/HackFolder"},
        headers={"Authorization": f"Bearer {token_user_b}"}
    )
    assert res_b.status_code == 403
    assert "forbidden" in res_b.json()["detail"].lower()
