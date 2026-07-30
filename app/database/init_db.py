from sqlalchemy.orm import Session
from app.database.session import Base, engine, SessionLocal
from app.models.user import User, UserRole
from app.security.password import get_password_hash

def init_db(db: Session = None):
    Base.metadata.create_all(bind=engine)

    close_after = False
    if db is None:
        db = SessionLocal()
        close_after = True

    try:
        # Seed default Admin account if not exists
        admin = db.query(User).filter(User.email == "admin@secure.local").first()
        if not admin:
            admin_user = User(
                name="System Admin",
                email="admin@secure.local",
                username="admin",
                hashed_password=get_password_hash("AdminSecret123!"),
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin_user)
        
        # Seed default Demo User A if not exists
        user_a = db.query(User).filter(User.email == "usera@secure.local").first()
        if not user_a:
            demo_a = User(
                name="Alice Johnson",
                email="usera@secure.local",
                username="alice",
                hashed_password=get_password_hash("UserSecret123!"),
                role=UserRole.USER,
                is_active=True
            )
            db.add(demo_a)

        # Seed default Demo User B if not exists
        user_b = db.query(User).filter(User.email == "userb@secure.local").first()
        if not user_b:
            demo_b = User(
                name="Bob Smith",
                email="userb@secure.local",
                username="bob",
                hashed_password=get_password_hash("UserSecret123!"),
                role=UserRole.USER,
                is_active=True
            )
            db.add(demo_b)

        db.commit()
    finally:
        if close_after:
            db.close()

if __name__ == "__main__":
    init_db()
    print("Database tables initialized and initial users seeded.")
