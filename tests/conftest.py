import os
import sys

# Ensure project root directory is in sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
try:
    from fastapi.testclient import TestClient
except ImportError:
    from starlette.testclient import TestClient

from app.database.session import Base, get_db
from app.main import app
from app.models.user import User, UserRole
from app.security.password import get_password_hash
from app.security.jwt import create_access_token

TEST_DB_FILE = "./test_secure_sharing.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass

@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def user_a(db):
    user = User(
        name="Alice Johnson",
        email="alice_test@secure.local",
        username="alice_test",
        hashed_password=get_password_hash("ValidPass123!"),
        role=UserRole.USER,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def user_b(db):
    user = User(
        name="Bob Smith",
        email="bob_test@secure.local",
        username="bob_test",
        hashed_password=get_password_hash("ValidPass123!"),
        role=UserRole.USER,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def admin_user(db):
    user = User(
        name="Admin Test",
        email="admin_test@secure.local",
        username="admin_test",
        hashed_password=get_password_hash("AdminPass123!"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def token_user_a(user_a):
    return create_access_token({"sub": str(user_a.id), "email": user_a.email, "role": user_a.role.value})

@pytest.fixture
def token_user_b(user_b):
    return create_access_token({"sub": str(user_b.id), "email": user_b.email, "role": user_b.role.value})

@pytest.fixture
def token_admin(admin_user):
    return create_access_token({"sub": str(admin_user.id), "email": admin_user.email, "role": admin_user.role.value})
