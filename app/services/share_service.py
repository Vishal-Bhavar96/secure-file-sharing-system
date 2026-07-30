from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.file import File
from app.models.user import User
from app.models.share import FileShare, SharePermission
from app.models.audit_log import AuditAction
from app.schemas.share import ShareCreateRequest
from app.services.audit_service import log_activity

def create_file_share(
    db: Session,
    owner: User,
    share_in: ShareCreateRequest,
    ip_address: str = None
) -> FileShare:

    # 1. Verify file ownership
    db_file = db.query(File).filter(File.id == share_in.file_id, File.is_deleted == False).first()
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if db_file.owner_id != owner.id:
        log_activity(
            db,
            action=AuditAction.UNAUTHORIZED_ACCESS,
            user_id=owner.id,
            user_email=owner.email,
            resource=f"File:{share_in.file_id}",
            details="User attempted to share a file they do not own",
            success=False,
            ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the file owner can share this file"
        )

    # 2. Find target user
    target_user = db.query(User).filter(
        (User.email == share_in.target_user_identifier) | 
        (User.username == share_in.target_user_identifier)
    ).first()

    if not target_user:
        log_activity(
            db,
            action=AuditAction.FILE_SHARED,
            user_id=owner.id,
            user_email=owner.email,
            resource=f"File:{db_file.id}",
            details=f"Target recipient '{share_in.target_user_identifier}' not found",
            success=False,
            ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target recipient '{share_in.target_user_identifier}' not found"
        )

    if target_user.id == owner.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot share a file with yourself"
        )

    # 3. Calculate Expiry
    expiry_at = None
    if share_in.expiry_hours:
        expiry_at = datetime.utcnow() + timedelta(hours=share_in.expiry_hours)

    # 4. Check for existing active share
    existing_share = db.query(FileShare).filter(
        FileShare.file_id == db_file.id,
        FileShare.shared_with_id == target_user.id,
        FileShare.is_revoked == False
    ).first()

    if existing_share:
        # Update existing share
        existing_share.permission = share_in.permission
        existing_share.expiry_at = expiry_at
        existing_share.max_downloads = share_in.max_downloads
        db.commit()
        db.refresh(existing_share)
        share_obj = existing_share
    else:
        share_obj = FileShare(
            file_id=db_file.id,
            shared_by_id=owner.id,
            shared_with_id=target_user.id,
            permission=share_in.permission,
            expiry_at=expiry_at,
            max_downloads=share_in.max_downloads,
            download_count=0,
            is_revoked=False
        )
        db.add(share_obj)
        db.commit()
        db.refresh(share_obj)

    log_activity(
        db,
        action=AuditAction.FILE_SHARED,
        user_id=owner.id,
        user_email=owner.email,
        resource=f"Share:{share_obj.id}:File:{db_file.id}",
        details=f"Shared '{db_file.original_name}' with {target_user.email} (Perm: {share_in.permission})",
        success=True,
        ip_address=ip_address
    )

    return share_obj

def get_share_access_and_validate(
    db: Session,
    share_id: int,
    requesting_user: User,
    required_permission: SharePermission = SharePermission.VIEW,
    ip_address: str = None
) -> tuple[FileShare, File]:

    share = db.query(FileShare).filter(FileShare.id == share_id).first()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share record not found")

    # Check recipient identity
    if share.shared_with_id != requesting_user.id and share.shared_by_id != requesting_user.id:
        log_activity(
            db,
            action=AuditAction.UNAUTHORIZED_ACCESS,
            user_id=requesting_user.id,
            user_email=requesting_user.email,
            resource=f"Share:{share_id}",
            details="Unauthorized recipient attempted share access",
            success=False,
            ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You are not the authorized recipient of this share"
        )

    # Check revocation
    if share.is_revoked:
        log_activity(
            db,
            action=AuditAction.UNAUTHORIZED_ACCESS,
            user_id=requesting_user.id,
            user_email=requesting_user.email,
            resource=f"Share:{share_id}",
            details="Attempted access to revoked share",
            success=False,
            ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This file share has been revoked by the owner"
        )

    # Check expiration
    if share.expiry_at and datetime.utcnow() > share.expiry_at:
        log_activity(
            db,
            action=AuditAction.UNAUTHORIZED_ACCESS,
            user_id=requesting_user.id,
            user_email=requesting_user.email,
            resource=f"Share:{share_id}",
            details="Attempted access to expired share",
            success=False,
            ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This file share link has expired"
        )

    # Check file deletion
    db_file = db.query(File).filter(File.id == share.file_id, File.is_deleted == False).first()
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The shared file has been deleted by its owner"
        )

    # Check permissions
    if required_permission == SharePermission.DOWNLOAD:
        if share.permission not in (SharePermission.DOWNLOAD, SharePermission.EDIT):
            log_activity(
                db,
                action=AuditAction.UNAUTHORIZED_ACCESS,
                user_id=requesting_user.id,
                user_email=requesting_user.email,
                resource=f"Share:{share_id}",
                details=f"User attempted DOWNLOAD action with VIEW-only share permission",
                success=False,
                ip_address=ip_address
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Download forbidden: You have VIEW-only permission"
            )

        # Check download limit
        if share.max_downloads is not None and share.download_count >= share.max_downloads:
            log_activity(
                db,
                action=AuditAction.UNAUTHORIZED_ACCESS,
                user_id=requesting_user.id,
                user_email=requesting_user.email,
                resource=f"Share:{share_id}",
                details=f"Download limit ({share.max_downloads}) reached",
                success=False,
                ip_address=ip_address
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Download limit for this share link has been exceeded"
            )

    return share, db_file

def increment_share_download(db: Session, share: FileShare):
    share.download_count += 1
    db.commit()

def revoke_file_share(db: Session, share_id: int, owner: User, ip_address: str = None) -> FileShare:

    share = db.query(FileShare).filter(FileShare.id == share_id).first()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share record not found")

    if share.shared_by_id != owner.id:
        log_activity(
            db,
            action=AuditAction.UNAUTHORIZED_ACCESS,
            user_id=owner.id,
            user_email=owner.email,
            resource=f"Share:{share_id}",
            details="Non-owner attempted share revocation",
            success=False,
            ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the file owner can revoke this share"
        )

    share.is_revoked = True
    db.commit()
    db.refresh(share)

    log_activity(
        db,
        action=AuditAction.SHARE_REVOKED,
        user_id=owner.id,
        user_email=owner.email,
        resource=f"Share:{share_id}",
        details=f"Revoked share with user_id {share.shared_with_id}",
        success=True,
        ip_address=ip_address
    )

    return share
