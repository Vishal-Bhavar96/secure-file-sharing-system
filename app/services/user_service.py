import os
import uuid
import re
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile
from app.config.settings import settings
from app.models.user import User
from app.models.session import UserSession
from app.models.audit_log import AuditAction
from app.security.password import verify_password, get_password_hash
from app.services.audit_service import log_activity

AVATAR_DIR = os.path.join(settings.STORAGE_DIR, "avatars")

def ensure_avatar_dir():
    if not os.path.exists(AVATAR_DIR):
        os.makedirs(AVATAR_DIR, exist_ok=True)

def update_profile_name(db: Session, user: User, name: str, ip_address: str = None) -> User:
    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Name cannot be empty")

    old_name = user.name
    user.name = clean_name
    db.commit()
    db.refresh(user)

    log_activity(
        db,
        action=AuditAction.PROFILE_UPDATED,
        user_id=user.id,
        user_email=user.email,
        resource=f"User:{user.id}",
        details=f"Updated name from '{old_name}' to '{clean_name}'",
        success=True,
        ip_address=ip_address
    )
    return user

def upload_avatar(db: Session, user: User, file: UploadFile, ip_address: str = None) -> User:
    ensure_avatar_dir()
    
    filename = file.filename.lower()
    ext = filename.split('.')[-1] if '.' in filename else ''
    allowed_exts = {'jpg', 'jpeg', 'png', 'webp'}
    allowed_mimes = {'image/jpeg', 'image/jpg', 'image/png', 'image/webp'}

    content_type = file.content_type.lower() if file.content_type else ''
    if ext not in allowed_exts and content_type not in allowed_mimes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image format. Allowed formats: JPG, JPEG, PNG, WEBP"
        )

    content = file.file.read()
    max_size = 5 * 1024 * 1024  # 5MB
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image size exceeds maximum limit of 5MB"
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty image file uploaded"
        )

    # Remove previous avatar disk file if exists
    if user.avatar_path and os.path.exists(user.avatar_path):
        try:
            os.remove(user.avatar_path)
        except Exception:
            pass

    avatar_filename = f"avatar_{user.id}_{uuid.uuid4().hex}.{ext if ext in allowed_exts else 'png'}"
    avatar_disk_path = os.path.join(AVATAR_DIR, avatar_filename)

    try:
        with open(avatar_disk_path, "wb") as f:
            f.write(content)
    except Exception as e:
        log_activity(
            db, action=AuditAction.PROFILE_PHOTO_UPDATED, user_id=user.id, user_email=user.email,
            resource=f"User:{user.id}", details=f"Avatar save failure: {str(e)}", success=False, ip_address=ip_address
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save avatar image")

    user.avatar_path = avatar_disk_path
    db.commit()
    db.refresh(user)

    log_activity(
        db,
        action=AuditAction.PROFILE_PHOTO_UPDATED,
        user_id=user.id,
        user_email=user.email,
        resource=f"User:{user.id}",
        details="Updated profile avatar photo",
        success=True,
        ip_address=ip_address
    )
    return user

def remove_avatar(db: Session, user: User, ip_address: str = None) -> User:
    if user.avatar_path and os.path.exists(user.avatar_path):
        try:
            os.remove(user.avatar_path)
        except Exception:
            pass

    user.avatar_path = None
    db.commit()
    db.refresh(user)

    log_activity(
        db,
        action=AuditAction.PROFILE_PHOTO_REMOVED,
        user_id=user.id,
        user_email=user.email,
        resource=f"User:{user.id}",
        details="Removed profile avatar photo",
        success=True,
        ip_address=ip_address
    )
    return user

def change_email(db: Session, user: User, current_password: str, new_email: str, confirm_new_email: str, ip_address: str = None) -> User:
    if not verify_password(current_password, user.hashed_password):
        log_activity(
            db, action=AuditAction.EMAIL_CHANGED, user_id=user.id, user_email=user.email,
            resource=f"User:{user.id}", details="Incorrect current password provided for email change",
            success=False, ip_address=ip_address
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password")

    new_email = new_email.strip().lower()
    confirm_new_email = confirm_new_email.strip().lower()

    if new_email != confirm_new_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New email and confirm email do not match")

    if new_email == user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New email cannot be identical to current email")

    # Check uniqueness
    existing = db.query(User).filter(User.email == new_email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email address is already registered to another account")

    old_email = user.email
    user.email = new_email
    db.commit()
    db.refresh(user)

    log_activity(
        db,
        action=AuditAction.EMAIL_CHANGED,
        user_id=user.id,
        user_email=user.email,
        resource=f"User:{user.id}",
        details=f"Changed email address from '{old_email}' to '{new_email}'",
        success=True,
        ip_address=ip_address
    )
    return user

def change_password(db: Session, user: User, current_password: str, new_password: str, confirm_new_password: str, ip_address: str = None) -> User:
    if not verify_password(current_password, user.hashed_password):
        log_activity(
            db, action=AuditAction.PASSWORD_CHANGED, user_id=user.id, user_email=user.email,
            resource=f"User:{user.id}", details="Incorrect current password provided for password change",
            success=False, ip_address=ip_address
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect current password")

    if new_password != confirm_new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password and confirm password do not match")

    if len(new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", new_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", new_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain at least one lowercase letter")
    if not re.search(r"[0-9]", new_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", new_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must contain at least one special character")

    user.hashed_password = get_password_hash(new_password)
    user.last_password_change_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    log_activity(
        db,
        action=AuditAction.PASSWORD_CHANGED,
        user_id=user.id,
        user_email=user.email,
        resource=f"User:{user.id}",
        details="Password changed successfully",
        success=True,
        ip_address=ip_address
    )
    return user

def update_preferences(db: Session, user: User, theme: str = "dark", sort: str = "date_desc", items_per_page: int = 10, ip_address: str = None) -> User:
    allowed_themes = {"dark", "light", "system"}
    allowed_sorts = {"date_desc", "date_asc", "name_asc", "name_desc", "size_desc"}
    allowed_items = {10, 25, 50}

    if theme and theme in allowed_themes:
        user.theme_preference = theme
    if sort and sort in allowed_sorts:
        user.default_file_sort = sort
    if items_per_page and items_per_page in allowed_items:
        user.items_per_page = items_per_page

    db.commit()
    db.refresh(user)

    log_activity(
        db,
        action=AuditAction.ACCOUNT_SETTINGS_UPDATED,
        user_id=user.id,
        user_email=user.email,
        resource=f"User:{user.id}",
        details=f"Updated preferences: theme={user.theme_preference}, sort={user.default_file_sort}, items={user.items_per_page}",
        success=True,
        ip_address=ip_address
    )
    return user

def get_active_sessions(db: Session, user: User, current_token: str = None) -> List[dict]:
    sessions = db.query(UserSession).filter(UserSession.user_id == user.id, UserSession.is_active == True).all()
    results = []
    for s in sessions:
        results.append({
            "id": s.id,
            "user_agent": s.user_agent or "Unknown Device / Browser",
            "ip_address": s.ip_address or "127.0.0.1",
            "is_active": s.is_active,
            "created_at": s.created_at,
            "last_activity_at": s.last_activity_at,
            "is_current": (s.session_token == current_token) if current_token else False
        })
    return results

def revoke_other_sessions(db: Session, user: User, current_token: str = None, ip_address: str = None) -> int:
    query = db.query(UserSession).filter(UserSession.user_id == user.id, UserSession.is_active == True)
    if current_token:
        query = query.filter(UserSession.session_token != current_token)

    other_sessions = query.all()
    count = len(other_sessions)
    for s in other_sessions:
        s.is_active = False

    db.commit()

    log_activity(
        db,
        action=AuditAction.SESSION_REVOKED,
        user_id=user.id,
        user_email=user.email,
        resource=f"User:{user.id}",
        details=f"Revoked {count} other active session(s)",
        success=True,
        ip_address=ip_address
    )
    return count
