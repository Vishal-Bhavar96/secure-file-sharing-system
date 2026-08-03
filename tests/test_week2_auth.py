import pytest

def test_register_empty_name(client):
    res = client.post("/api/v1/auth/register", json={
        "name": "  ",
        "email": "empty_name@test.com",
        "password": "ValidPassword123!"
    })
    assert res.status_code == 422 or res.status_code == 400

def test_register_empty_email(client):
    res = client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "not-an-email",
        "password": "ValidPassword123!"
    })
    assert res.status_code == 422 or res.status_code == 400

def test_register_duplicate_email(client, user_a):
    res = client.post("/api/v1/auth/register", json={
        "name": "Another User",
        "email": user_a.email,
        "password": "ValidPassword123!"
    })
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]

def test_register_duplicate_username(client, user_a):
    res = client.post("/api/v1/auth/register", json={
        "name": "Another User",
        "email": "unique_email@test.com",
        "username": user_a.username,
        "password": "ValidPassword123!"
    })
    assert res.status_code == 400
    assert "taken" in res.json()["detail"]

def test_register_weak_password(client):
    res = client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "weak_pwd@test.com",
        "password": "123"
    })
    assert res.status_code == 400
    assert "Weak password" in res.json()["detail"]

def test_register_password_mismatch(client):
    res = client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "mismatch@test.com",
        "password": "ValidPassword123!",
        "confirm_password": "DifferentPassword123!"
    })
    assert res.status_code == 400
    assert "match" in res.json()["detail"]

def test_login_correct_credentials(client, user_a):
    res = client.post("/api/v1/auth/login", json={
        "email": user_a.email,
        "password": "ValidPass123!"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == user_a.email

def test_login_incorrect_password(client, user_a):
    res = client.post("/api/v1/auth/login", json={
        "email": user_a.email,
        "password": "WrongPassword123!"
    })
    assert res.status_code == 401

def test_login_unknown_email(client):
    res = client.post("/api/v1/auth/login", json={
        "email": "nobody@secure.local",
        "password": "ValidPass123!"
    })
    assert res.status_code == 401

def test_authorization_matrix(client, token_user_a, token_admin):
    # User -> Admin feature BLOCKED
    res = client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {token_user_a}"})
    assert res.status_code == 403

    # Admin -> Admin feature ALLOWED
    res_admin = client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {token_admin}"})
    assert res_admin.status_code == 200

def test_password_requirements_endpoint(client):
    res = client.get("/api/v1/auth/password-requirements")
    assert res.status_code == 200
    data = res.json()
    assert data["min_length"] == 8
    assert data["require_uppercase"] is True
    assert "rules" in data

