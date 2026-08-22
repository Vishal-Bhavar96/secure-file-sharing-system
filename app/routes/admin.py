import os
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, String, cast
from app.database.session import get_db
from app.models.user import User, UserRole
from app.models.file import File
from app.models.share import FileShare
from app.models.audit_log import AuditLog, AuditAction
from app.schemas.user import UserOut, AdminUserDetailOut, UserStatusUpdate
from app.schemas.audit import SystemStatsOut
from app.security.rbac import require_admin
from app.routes.users import is_user_online, compute_last_seen_text

router = APIRouter(prefix="/admin", tags=["Admin Portal"])

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
    user_details = []

    for u in users:
        files_count = db.query(func.count(File.id)).filter(File.owner_id == u.id, File.is_deleted == False).scalar() or 0
        storage_bytes = db.query(func.sum(File.file_size)).filter(File.owner_id == u.id, File.is_deleted == False).scalar() or 0
        has_avatar = bool(u.avatar_path and os.path.exists(u.avatar_path))

        user_details.append(AdminUserDetailOut(
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
        ))

    return user_details

@router.put("/users/{user_id}/status", response_model=AdminUserDetailOut)
def update_user_status(
    user_id: int,
    status_in: UserStatusUpdate,
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

    files_count = db.query(func.count(File.id)).filter(File.owner_id == target_user.id, File.is_deleted == False).scalar() or 0
    storage_bytes = db.query(func.sum(File.file_size)).filter(File.owner_id == target_user.id, File.is_deleted == False).scalar() or 0
    has_avatar = bool(target_user.avatar_path and os.path.exists(target_user.avatar_path))

    return AdminUserDetailOut(
        id=target_user.id,
        name=target_user.name,
        email=target_user.email,
        username=target_user.username,
        role=target_user.role,
        is_active=target_user.is_active,
        created_at=target_user.created_at,
        has_avatar=has_avatar,
        files_count=files_count,
        storage_used_bytes=storage_bytes,
        is_online=is_user_online(target_user),
        last_seen_text=compute_last_seen_text(target_user),
        last_login_at=target_user.last_login_at
    )

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
