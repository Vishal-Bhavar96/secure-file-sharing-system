from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, String, cast
from app.database.session import get_db
from app.models.user import User, UserRole
from app.models.file import File
from app.models.share import FileShare
from app.models.audit_log import AuditLog, AuditAction
from app.schemas.user import UserOut
from app.schemas.audit import SystemStatsOut
from app.security.rbac import require_admin

router = APIRouter(prefix="/admin", tags=["Admin Portal"])

@router.get("/stats", response_model=SystemStatsOut)
def get_system_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    total_users = db.query(func.count(User.id)).scalar() or 0
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
            AuditAction.LOGIN_FAILED
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
        total_files=total_files,
        storage_used_bytes=storage_used,
        active_shares=active_shares,
        expired_shares=expired_shares,
        failed_login_attempts=failed_logins,
        security_events=security_events,
        most_downloaded_files=most_downloaded_list
    )

@router.get("/users", response_model=List[UserOut])
def list_all_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    users = db.query(User).order_by(User.id.asc()).all()
    return users
