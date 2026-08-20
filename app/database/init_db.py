from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database.session import Base, engine, SessionLocal
from app.models.user import User, UserRole
from app.security.password import get_password_hash

def migrate_schema():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]
            if columns:
                if "avatar_path" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN avatar_path VARCHAR(500)"))
                if "theme_preference" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN theme_preference VARCHAR(20) DEFAULT 'dark'"))
                if "default_file_sort" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN default_file_sort VARCHAR(50) DEFAULT 'date_desc'"))
                if "items_per_page" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN items_per_page INTEGER DEFAULT 10"))
                if "last_login_at" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN last_login_at DATETIME"))
                if "last_seen_at" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN last_seen_at DATETIME"))
                if "last_password_change_at" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN last_password_change_at DATETIME"))
                conn.commit()

            res_shares = conn.execute(text("PRAGMA table_info(file_shares)"))
            share_cols = [row[1] for row in res_shares.fetchall()]
            if share_cols:
                if "share_token" not in share_cols:
                    conn.execute(text("ALTER TABLE file_shares ADD COLUMN share_token VARCHAR(100)"))
                if "share_code" not in share_cols:
                    conn.execute(text("ALTER TABLE file_shares ADD COLUMN share_code VARCHAR(20)"))
                if "password_hash" not in share_cols:
                    conn.execute(text("ALTER TABLE file_shares ADD COLUMN password_hash VARCHAR(255)"))
                if "is_active" not in share_cols:
                    conn.execute(text("ALTER TABLE file_shares ADD COLUMN is_active BOOLEAN DEFAULT 1"))
                if "updated_at" not in share_cols:
                    conn.execute(text("ALTER TABLE file_shares ADD COLUMN updated_at DATETIME"))
                if "recipient_email" not in share_cols:
                    conn.execute(text("ALTER TABLE file_shares ADD COLUMN recipient_email VARCHAR(255)"))
                if "requires_otp" not in share_cols:
                    conn.execute(text("ALTER TABLE file_shares ADD COLUMN requires_otp BOOLEAN DEFAULT 1"))
                if "otp_code_hash" not in share_cols:
                    conn.execute(text("ALTER TABLE file_shares ADD COLUMN otp_code_hash VARCHAR(255)"))
                if "otp_expires_at" not in share_cols:
                    conn.execute(text("ALTER TABLE file_shares ADD COLUMN otp_expires_at DATETIME"))
                if "otp_attempts" not in share_cols:
                    conn.execute(text("ALTER TABLE file_shares ADD COLUMN otp_attempts INTEGER DEFAULT 0"))
                if "otp_last_sent_at" not in share_cols:
                    conn.execute(text("ALTER TABLE file_shares ADD COLUMN otp_last_sent_at DATETIME"))
                if "requires_password" not in share_cols:
                    conn.execute(text("ALTER TABLE file_shares ADD COLUMN requires_password BOOLEAN DEFAULT 0"))
                if "one_time_access" not in share_cols:
                    conn.execute(text("ALTER TABLE file_shares ADD COLUMN one_time_access BOOLEAN DEFAULT 0"))
                if "last_downloaded_at" not in share_cols:
                    conn.execute(text("ALTER TABLE file_shares ADD COLUMN last_downloaded_at DATETIME"))
                conn.commit()
    except Exception:
        pass

def init_db(db: Session = None):
    Base.metadata.create_all(bind=engine)
    migrate_schema()

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
