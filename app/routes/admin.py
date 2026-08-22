import os
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, String, cast
from app.database.session import get_db
from app.models.user import User, UserRole, PasswordResetOTP
from app.models.file import File
from app.models.folder import Folder
from app.models.share import FileShare
from app.models.session import UserSession
from app.models.audit_log import AuditLog, AuditAction
from app.schemas.user import UserOut, AdminUserDetailOut, UserStatusUpdate, AdminUserEdit
from app.schemas.audit import SystemStatsOut
from app.security.rbac import require_admin
from app.security.password import get_password_hash, validate_password_strength
from app.services.audit_service import log_activity
from app.routes.users import is_user_online, compute_last_seen_text

router = APIRouter(prefix="/admin", tags=["Admin Portal"])

def build_admin_user_detail(u: User, db: Session) -> AdminUserDetailOut:
    files_count = db.query(func.count(File.id)).filter(File.owner_id == u.id, File.is_deleted == False).scalar() or 0
    storage_bytes = db.query(func.sum(File.file_size)).filter(File.owner_id == u.id, File.is_deleted == False).scalar() or 0
    has_avatar = bool(u.avatar_path and os.path.exists(u.avatar_path))

    return AdminUserDetailOut(
        id=u.id,
        name=u.name,
        email=u.email,
        username=u.username,
        role=u.role,
        is_active=u.is_active,
        created_at=u.created_at,
        has_avatar=has_avatar,
        files_count=files_count,
        storage_used_bytes=storage_bytes,
        is_online=is_user_online(u),
        last_seen_text=compute_last_seen_text(u),
        last_login_at=u.last_login_at
    )

@router.get("/stats", response_model=SystemStatsOut)
def get_system_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    all_users = db.query(User).all()
    total_users = len(all_users)
    total_students = sum(1 for u in all_users if u.role == UserRole.USER)
    total_admins = sum(1 for u in all_users if u.role == UserRole.ADMIN)
    online_users_count = sum(1 for u in all_users if is_user_online(u))

    total_files = db.query(func.count(File.id)).filter(File.is_deleted == False).scalar() or 0
    storage_used = db.query(func.sum(File.file_size)).filter(File.is_deleted == False).scalar() or 0
    
    now = datetime.utcnow()
    active_shares = db.query(func.count(FileShare.id)).filter(
        FileShare.is_revoked == False,
        (FileShare.expiry_at == None) | (FileShare.expiry_at > now)
    ).scalar() or 0

    expired_shares = db.query(func.count(FileShare.id)).filter(
        FileShare.is_revoked == False,
        FileShare.expiry_at != None,
        FileShare.expiry_at <= now
    ).scalar() or 0

    failed_logins = db.query(func.count(AuditLog.id)).filter(
        AuditLog.action == AuditAction.LOGIN_FAILED
    ).scalar() or 0

    security_events = db.query(func.count(AuditLog.id)).filter(
        AuditLog.action.in_([
            AuditAction.UNAUTHORIZED_ACCESS,
            AuditAction.LOGIN_FAILED,
            AuditAction.INVALID_SHARE_TOKEN,
            AuditAction.INVALID_SHARE_PASSWORD,
            AuditAction.SHARE_ACCESS_DENIED,
            AuditAction.OTP_FAILED
        ])
    ).scalar() or 0

    # Most downloaded files query
    most_downloaded = db.query(
        File.original_name,
        func.count(AuditLog.id).label("download_count")
    ).join(AuditLog, AuditLog.resource.like("File:" + cast(File.id, String) + "%"))\
     .filter(AuditLog.action == AuditAction.FILE_DOWNLOADED)\
     .group_by(File.id)\
     .order_by(func.count(AuditLog.id).desc())\
     .limit(5).all()

    most_downloaded_list = [
        {"filename": item[0], "downloads": item[1]} for item in most_downloaded
    ]

    return SystemStatsOut(
        total_users=total_users,
        total_students=total_students,
        total_admins=total_admins,
        online_users_count=online_users_count,
        total_files=total_files,
        storage_used_bytes=storage_used,
        active_shares=active_shares,
        expired_shares=expired_shares,
        failed_login_attempts=failed_logins,
        security_events=security_events,
        most_downloaded_files=most_downloaded_list
    )

@router.get("/users", response_model=List[AdminUserDetailOut])
def list_all_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    users = db.query(User).order_by(User.id.asc()).all()
    return [build_admin_user_detail(u, db) for u in users]

@router.get("/users/{user_id}", response_model=AdminUserDetailOut)
def get_user_detail(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return build_admin_user_detail(target_user, db)

@router.put("/users/{user_id}", response_model=AdminUserDetailOut)
def edit_user(
    user_id: int,
    user_edit: AdminUserEdit,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    ip = request.client.host if request.client else None

    # Protect against admin demoting or deactivating self
    if target_user.id == admin.id:
        if user_edit.is_active is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Administrator cannot deactivate own account")
        if user_edit.role is not None and user_edit.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Administrator cannot remove admin role from self")

    # Update Name
    if user_edit.name is not None and user_edit.name.strip():
        target_user.name = user_edit.name.strip()

    # Update Email
    if user_edit.email is not None and user_edit.email.strip():
        new_email = user_edit.email.strip().lower()
        if new_email != target_user.email.lower():
            dup = db.query(User).filter(User.email.ilike(new_email), User.id != target_user.id).first()
            if dup:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already in use by another user")
            target_user.email = new_email

    # Update Username
    if user_edit.username is not None and user_edit.username.strip():
        new_username = user_edit.username.strip()
        if new_username != target_user.username:
            dup_u = db.query(User).filter(User.username == new_username, User.id != target_user.id).first()
            if dup_u:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is already taken")
            target_user.username = new_username

    # Update Role
    if user_edit.role is not None:
        target_user.role = user_edit.role

    # Update Status
    if user_edit.is_active is not None:
        target_user.is_active = user_edit.is_active

    # Update Password if provided
    if user_edit.new_password is not None and user_edit.new_password.strip():
        pwd = user_edit.new_password.strip()
        is_strong, pwd_err = validate_password_strength(pwd)
        if not is_strong:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Weak password: {pwd_err}")
        target_user.hashed_password = get_password_hash(pwd)
        target_user.last_password_change_at = datetime.utcnow()

    db.commit()
    db.refresh(target_user)

    log_activity(
        db,
        action=AuditAction.PROFILE_UPDATED,
        user_id=admin.id,
        user_email=admin.email,
        resource=f"User:{target_user.id}",
        details=f"Admin {admin.email} updated profile/role for user {target_user.email}",
        success=True,
        ip_address=ip
    )

    return build_admin_user_detail(target_user, db)

@router.put("/users/{user_id}/status", response_model=AdminUserDetailOut)
def update_user_status(
    user_id: int,
    status_in: UserStatusUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if target_user.id == admin.id and status_in.is_active is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin cannot deactivate their own account")

    if status_in.is_active is not None:
        target_user.is_active = status_in.is_active
    if status_in.role is not None:
        target_user.role = status_in.role

    db.commit()
    db.refresh(target_user)

    ip = request.client.host if request.client else None
    log_activity(
        db,
        action=AuditAction.PROFILE_UPDATED,
        user_id=admin.id,
        user_email=admin.email,
        resource=f"User:{target_user.id}",
        details=f"Admin {admin.email} changed status/role for user {target_user.email}",
        success=True,
        ip_address=ip
    )

    return build_admin_user_detail(target_user, db)

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if target_user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin cannot delete their own active account")

    user_name = target_user.name
    user_email = target_user.email
    ip = request.client.host if request.client else None

    # Delete all physical files owned by user on disk
    user_files = db.query(File).filter(File.owner_id == target_user.id).all()
    deleted_files_count = len(user_files)
    for f in user_files:
        if f.encrypted_path and os.path.exists(f.encrypted_path):
            try:
                os.remove(f.encrypted_path)
            except Exception:
                pass

    # Delete avatar from disk
    if target_user.avatar_path and os.path.exists(target_user.avatar_path):
        try:
            os.remove(target_user.avatar_path)
        except Exception:
            pass

    # Delete dependent relations
    file_ids = [f.id for f in user_files]
    if file_ids:
        db.query(FileShare).filter(FileShare.file_id.in_(file_ids)).delete(synchronize_session=False)

    db.query(FileShare).filter(
        (FileShare.shared_by_id == target_user.id) | (FileShare.shared_with_id == target_user.id)
    ).delete(synchronize_session=False)

    db.query(File).filter(File.owner_id == target_user.id).delete(synchronize_session=False)
    db.query(Folder).filter(Folder.owner_id == target_user.id).delete(synchronize_session=False)
    db.query(PasswordResetOTP).filter(PasswordResetOTP.user_id == target_user.id).delete(synchronize_session=False)
    db.query(UserSession).filter(UserSession.user_id == target_user.id).delete(synchronize_session=False)
    
    # Nullify or keep audit logs for compliance
    db.query(AuditLog).filter(AuditLog.user_id == target_user.id).update({"user_id": None}, synchronize_session=False)

    db.delete(target_user)
    db.commit()

    log_activity(
        db,
        action=AuditAction.FILE_DELETED,
        user_id=admin.id,
        user_email=admin.email,
        resource=f"User:{user_id}",
        details=f"Admin {admin.email} deleted user '{user_name}' ({user_email}) and {deleted_files_count} associated file(s)",
        success=True,
        ip_address=ip
    )

    return {
        "message": f"User '{user_name}' ({user_email}) and all associated files/data successfully deleted",
        "deleted_user_id": user_id,
        "deleted_files_count": deleted_files_count
    }

@router.get("/files")
def list_all_system_files(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    files = db.query(File).filter(File.is_deleted == False).order_by(File.created_at.desc()).all()
    res = []
    for f in files:
        owner = f.owner
        res.append({
            "id": f.id,
            "filename": f.original_name,
            "file_size": f.file_size,
            "mime_type": f.mime_type,
            "folder": f.folder,
            "owner_id": f.owner_id,
            "owner_name": owner.name if owner else "Unknown",
            "owner_email": owner.email if owner else "Unknown",
            "created_at": f.created_at
        })
    return res

@router.delete("/files/{file_id}")
def delete_system_file(
    file_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    filename = file.original_name
    owner_email = file.owner.email if file.owner else "Unknown"
    ip = request.client.host if request.client else None

    # Delete encrypted binary file on disk
    if file.encrypted_path and os.path.exists(file.encrypted_path):
        try:
            os.remove(file.encrypted_path)
        except Exception:
            pass

    # Delete associated file shares
    db.query(FileShare).filter(FileShare.file_id == file.id).delete(synchronize_session=False)

    db.delete(file)
    db.commit()

    log_activity(
        db,
        action=AuditAction.FILE_DELETED,
        user_id=admin.id,
        user_email=admin.email,
        resource=f"File:{file_id}:{filename}",
        details=f"Admin {admin.email} permanently deleted file '{filename}' owned by {owner_email}",
        success=True,
        ip_address=ip
    )

    return {
        "message": f"File '{filename}' successfully deleted",
        "file_id": file_id
    }

@router.get("/active-clients")
def list_active_clients(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    cutoff = datetime.utcnow() - timedelta(minutes=15)
    recent_users = db.query(User).filter(User.last_seen_at >= cutoff).order_by(User.last_seen_at.desc()).all()
    
    clients = []
    for u in recent_users:
        clients.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "is_online": is_user_online(u),
            "last_seen_text": compute_last_seen_text(u),
            "last_seen_at": u.last_seen_at
        })
    return clients

