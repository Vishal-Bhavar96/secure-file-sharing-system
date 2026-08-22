import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.models.user import User, UserRole
from app.models.file import File
from app.security.jwt import create_access_token
from app.security.password import get_password_hash

client = TestClient(app)

@pytest.fixture
def admin_token():
    db = SessionLocal()
    admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
    db.close()
    assert admin is not None
    return create_access_token(data={"sub": str(admin.id), "email": admin.email, "role": admin.role.value})

@pytest.fixture
def student_user():
    db = SessionLocal()
    email = "test_student_manage@secure.local"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            name="Test Student",
            email=email,
            username="test_student_manage",
            hashed_password=get_password_hash("Password123!"),
            role=UserRole.USER,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    user_id = user.id
    db.close()
    return user_id, email

def test_admin_edit_student_data(admin_token, student_user):
    user_id, _ = student_user
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Edit user name and username
    res = client.put(
        f"/api/v1/admin/users/{user_id}",
        json={
            "name": "Updated Student Name",
            "username": "updated_student_user",
            "is_active": True,
            "role": "USER"
        },
        headers=headers
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["name"] == "Updated Student Name"
    assert data["username"] == "updated_student_user"

def test_admin_delete_student_data(admin_token, student_user):
    user_id, _ = student_user
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Delete user
    res = client.delete(f"/api/v1/admin/users/{user_id}", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "successfully deleted" in data["message"]

    # Verify user no longer exists
    get_res = client.get(f"/api/v1/admin/users/{user_id}", headers=headers)
    assert get_res.status_code == 404
