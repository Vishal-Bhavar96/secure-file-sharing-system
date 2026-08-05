import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.file import File
from app.models.user import User
from app.models.share import FileShare, SharePermission, generate_share_token
from app.models.audit_log import AuditAction
from app.schemas.share import ShareCreateRequest, ShareUpdateRequest
from app.services.audit_service import log_activity
from app.security.password import get_password_hash, verify_password

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

    # 2. Find target user if provided
    target_user = None
    target_identifier = (share_in.target_user_identifier or "").strip()
    if target_identifier:
        target_user = db.query(User).filter(
            (User.email.ilike(target_identifier)) | 
            (User.username.ilike(target_identifier))
        ).first()

        if not target_user:
            if "@" in target_identifier:
                from app.models.user import UserRole
                
                target_email = target_identifier.lower()
                base_username = target_email.split("@")[0]
                username = base_username
                counter = 1
                while db.query(User).filter(User.username == username).first():
                    username = f"{base_username}{counter}"
                    counter += 1

                target_user = User(
                    name=target_email.split("@")[0].capitalize(),
                    email=target_email,
                    username=username,
                    hashed_password=get_password_hash(secrets.token_urlsafe(16)),
                    role=UserRole.USER,
                    is_active=True
                )
                db.add(target_user)
                db.commit()
                db.refresh(target_user)
            else:
                log_activity(
                    db,
                    action=AuditAction.FILE_SHARED,
                    user_id=owner.id,
                    user_email=owner.email,
                    resource=f"File:{db_file.id}",
                    details=f"Target recipient '{target_identifier}' not found",
                    success=False,
                    ip_address=ip_address
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Target recipient '{target_identifier}' not found. Please enter a valid email address."
                )

        if target_user.id == owner.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot share a file with yourself"
            )

    # 3. Calculate Expiry
    expiry_at = share_in.expiry_date
    if not expiry_at and share_in.expiry_hours:
        expiry_at = datetime.utcnow() + timedelta(hours=share_in.expiry_hours)

    # 4. Determine Download Limit
    max_downloads = share_in.max_downloads if share_in.max_downloads is not None else share_in.download_limit

    # 5. Password Hash
    pwd_hash = get_password_hash(share_in.password) if share_in.password else None

    # 6. Check for existing active share with same recipient
    existing_share = None
    if target_user:
        existing_share = db.query(FileShare).filter(
            FileShare.file_id == db_file.id,
            FileShare.shared_with_id == target_user.id,
            FileShare.is_revoked == False
        ).first()

    token = generate_share_token()

    if existing_share:
        existing_share.permission = share_in.permission
        existing_share.expiry_at = expiry_at
        existing_share.max_downloads = max_downloads
        if pwd_hash:
            existing_share.password_hash = pwd_hash
        if not existing_share.share_token:
            existing_share.share_token = token
        existing_share.is_active = True
        db.commit()
        db.refresh(existing_share)
        share_obj = existing_share
    else:
        share_obj = FileShare(
            file_id=db_file.id,
            shared_by_id=owner.id,
            shared_with_id=target_user.id if target_user else None,
            permission=share_in.permission,
            share_token=token,
            password_hash=pwd_hash,
            expiry_at=expiry_at,
            max_downloads=max_downloads,
            download_count=0,
            is_revoked=False,
            is_active=True
        )
        db.add(share_obj)
        db.commit()
        db.refresh(share_obj)

    recipient_desc = target_user.email if target_user else "Public Link"
    log_activity(
        db,
        action=AuditAction.FILE_SHARED,
        user_id=owner.id,
        user_email=owner.email,
        resource=f"Share:{share_obj.id}:File:{db_file.id}",
        details=f"Shared '{db_file.original_name}' with {recipient_desc} (Perm: {share_in.permission})",
        success=True,
        ip_address=ip_address
    )

    return share_obj

def get_share_access_and_validate(
    db: Session,
    share_id: int,
    requesting_user: Optional[User] = None,
    required_permission: SharePermission = SharePermission.VIEW,
    password: Optional[str] = None,
    ip_address: str = None
) -> Tuple[FileShare, File]:

    share = db.query(FileShare).filter(FileShare.id == share_id).first()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share record not found")

    user_id = requesting_user.id if requesting_user else None
    user_email = requesting_user.email if requesting_user else "Anonymous"

    # 1. Check revocation / active status
    if share.is_revoked or not share.is_active:
        log_activity(
            db,
            action=AuditAction.DOWNLOAD_BLOCKED if required_permission == SharePermission.DOWNLOAD else AuditAction.UNAUTHORIZED_ACCESS,
            user_id=user_id,
            user_email=user_email,
            resource=f"Share:{share_id}",
            details="Attempted access to revoked share link",
            success=False,
            ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This file share has been revoked by the owner"
        )

    # 2. Check expiration
    if share.expiry_at and datetime.utcnow() > share.expiry_at:
        log_activity(
            db,
            action=AuditAction.SHARE_EXPIRED,
            user_id=user_id,
            user_email=user_email,
            resource=f"Share:{share_id}",
            details="Attempted access to expired share link",
            success=False,
            ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This sharing link has expired."
        )

    # 3. Check recipient identity if recipient is specifically assigned
    if share.shared_with_id is not None:
        if not requesting_user or (requesting_user.id != share.shared_with_id and requesting_user.id != share.shared_by_id):
            log_activity(
                db,
                action=AuditAction.UNAUTHORIZED_ACCESS,
                user_id=user_id,
                user_email=user_email,
                resource=f"Share:{share_id}",
                details="Unauthorized recipient attempted share access",
                success=False,
                ip_address=ip_address
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You are not the authorized recipient of this share"
            )

    # 4. Check password protection
    if share.password_hash:
        if not password or not verify_password(password, share.password_hash):
            log_activity(
                db,
                action=AuditAction.DOWNLOAD_BLOCKED if required_permission == SharePermission.DOWNLOAD else AuditAction.UNAUTHORIZED_ACCESS,
                user_id=user_id,
                user_email=user_email,
                resource=f"Share:{share_id}",
                details="Password mismatch on password-protected share link",
                success=False,
                ip_address=ip_address
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password for shared file"
            )

    # 5. Check file deletion
    db_file = db.query(File).filter(File.id == share.file_id, File.is_deleted == False).first()
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The shared file has been deleted by its owner"
        )

    # 6. Check permission level & download limits
    if required_permission == SharePermission.DOWNLOAD:
        if share.permission not in (SharePermission.DOWNLOAD, SharePermission.EDIT):
            log_activity(
                db,
                action=AuditAction.DOWNLOAD_BLOCKED,
                user_id=user_id,
                user_email=user_email,
                resource=f"Share:{share_id}",
                details="User attempted DOWNLOAD action with VIEW-only share permission",
                success=False,
                ip_address=ip_address
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Download forbidden: You have VIEW-only permission"
            )

        if share.max_downloads is not None and share.download_count >= share.max_downloads:
            log_activity(
                db,
                action=AuditAction.DOWNLOAD_BLOCKED,
                user_id=user_id,
                user_email=user_email,
                resource=f"Share:{share_id}",
                details=f"Download limit ({share.max_downloads}) reached",
                success=False,
                ip_address=ip_address
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Download limit exceeded."
            )

    return share, db_file

def get_share_by_token(
    db: Session,
    token: str,
    requesting_user: Optional[User] = None,
    password: Optional[str] = None,
    ip_address: str = None
) -> Tuple[FileShare, File]:

    share = db.query(FileShare).filter(FileShare.share_token == token).first()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid token")

    user_id = requesting_user.id if requesting_user else None
    user_email = requesting_user.email if requesting_user else "Anonymous"

    # Log LINK_OPENED event
    log_activity(
        db,
        action=AuditAction.LINK_OPENED,
        user_id=user_id,
        user_email=user_email,
        resource=f"ShareToken:{token}",
        details=f"Recipient opened share link for File:{share.file_id}",
        success=True,
        ip_address=ip_address
    )

    return get_share_access_and_validate(
        db, share_id=share.id, requesting_user=requesting_user,
        required_permission=SharePermission.VIEW, password=password, ip_address=ip_address
    )

def increment_share_download(db: Session, share: FileShare, user: Optional[User] = None, ip_address: str = None):
    share.download_count += 1
    db.commit()

    user_id = user.id if user else None
    user_email = user.email if user else "Anonymous"
    log_activity(
        db,
        action=AuditAction.DOWNLOAD_SUCCESS,
        user_id=user_id,
        user_email=user_email,
        resource=f"Share:{share.id}:File:{share.file_id}",
        details=f"Download count incremented to {share.download_count}",
        success=True,
        ip_address=ip_address
    )

def update_file_share(
    db: Session,
    share_id: int,
    owner: User,
    update_in: ShareUpdateRequest,
    ip_address: str = None
) -> FileShare:

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
            details="Non-owner attempted to update share settings",
            success=False,
            ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the file owner can update this share"
        )

    if update_in.permission is not None:
        share.permission = update_in.permission

    if update_in.expiry_date is not None:
        share.expiry_at = update_in.expiry_date
    elif update_in.expiry_hours is not None:
        share.expiry_at = datetime.utcnow() + timedelta(hours=update_in.expiry_hours)

    if update_in.max_downloads is not None:
        share.max_downloads = update_in.max_downloads
    elif update_in.download_limit is not None:
        share.max_downloads = update_in.download_limit

    if update_in.password is not None:
        share.password_hash = get_password_hash(update_in.password) if update_in.password else None

    if update_in.is_active is not None:
        share.is_active = update_in.is_active
        if not update_in.is_active:
            share.is_revoked = True

    share.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(share)

    log_activity(
        db,
        action=AuditAction.PERMISSION_UPDATED,
        user_id=owner.id,
        user_email=owner.email,
        resource=f"Share:{share.id}",
        details=f"Updated share configuration (Permission: {share.permission}, Limit: {share.max_downloads})",
        success=True,
        ip_address=ip_address
    )

    return share

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
    share.is_active = False
    share.updated_at = datetime.utcnow()
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
