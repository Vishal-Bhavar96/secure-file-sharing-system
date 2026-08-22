import secrets
import hashlib
import string
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.file import File
from app.models.user import User
from app.models.share import FileShare, SharePermission, generate_share_token, generate_share_code, hash_token
from app.models.audit_log import AuditAction
from app.schemas.share import ShareCreateRequest, ShareUpdateRequest
from app.services.audit_service import log_activity
from app.security.password import get_password_hash, verify_password
from app.services.email_service import send_file_share_email, send_share_otp_email

def generate_secure_share_password(length: int = 12) -> str:
    """Generates a cryptographically secure random password for file sharing."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%^&*" for c in password)):
            return password

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

    # 2. Process target recipient identifier
    target_user = None
    target_identifier = (share_in.target_user_identifier or share_in.recipient_email or "").strip()
    target_email = target_identifier.lower() if "@" in target_identifier else None

    if target_identifier:
        target_user = db.query(User).filter(
            (User.email.ilike(target_identifier)) | 
            (User.username.ilike(target_identifier))
        ).first()

        if not target_user and "@" in target_identifier:
            from app.models.user import UserRole
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
        elif not target_user and "@" not in target_identifier:
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

        if target_user and target_user.id == owner.id:
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

    # 5. Handle Share Password Generation / Hashing
    requires_password = bool(share_in.requires_password or share_in.password)
    raw_password = share_in.password
    if share_in.requires_password and not raw_password:
        raw_password = generate_secure_share_password(12)

    pwd_hash = get_password_hash(raw_password) if raw_password else None

    # 6. Check for existing active share with same recipient
    existing_share = None
    if target_user:
        existing_share = db.query(FileShare).filter(
            FileShare.file_id == db_file.id,
            FileShare.shared_with_id == target_user.id,
            FileShare.is_revoked == False
        ).first()

    raw_token = generate_share_token()
    raw_code = generate_share_code()
    token_h = hash_token(raw_token)

    requires_otp = share_in.requires_otp if share_in.requires_otp is not None else False
    one_time_access = share_in.one_time_access if share_in.one_time_access is not None else False

    if existing_share:
        existing_share.permission = share_in.permission
        existing_share.expiry_at = expiry_at
        existing_share.max_downloads = max_downloads
        if target_email:
            existing_share.recipient_email = target_email
        if pwd_hash:
            existing_share.password_hash = pwd_hash
            existing_share.requires_password = True
        existing_share.requires_otp = requires_otp
        existing_share.one_time_access = one_time_access
        if not existing_share.share_token:
            existing_share.share_token = raw_token
            existing_share.token_hash = token_h
        if not getattr(existing_share, 'share_code', None):
            existing_share.share_code = raw_code
        existing_share.is_active = True
        db.commit()
        db.refresh(existing_share)
        share_obj = existing_share
    else:
        share_obj = FileShare(
            file_id=db_file.id,
            shared_by_id=owner.id,
            shared_with_id=target_user.id if target_user else None,
            recipient_email=target_email or (target_user.email if target_user else None),
            permission=share_in.permission,
            share_token=raw_token,
            share_code=raw_code,
            token_hash=token_h,
            password_hash=pwd_hash,
            requires_otp=requires_otp,
            requires_password=requires_password,
            one_time_access=one_time_access,
            expiry_at=expiry_at,
            max_downloads=max_downloads,
            download_count=0,
            is_revoked=False,
            is_active=True
        )
        db.add(share_obj)
        db.commit()
        db.refresh(share_obj)

    share_obj._generated_password = raw_password if requires_password else None

    recipient_desc = target_user.email if target_user else (target_email or "Public Link")
    log_activity(
        db,
        action=AuditAction.FILE_SHARED,
        user_id=owner.id,
        user_email=owner.email,
        resource=f"Share:{share_obj.id}:File:{db_file.id}",
        details=f"Shared '{db_file.original_name}' with {recipient_desc} (Perm: {share_in.permission}, OTP: {requires_otp}, Password: {requires_password})",
        success=True,
        ip_address=ip_address
    )

    return share_obj

def request_share_otp(db: Session, share: FileShare, ip_address: str = None) -> bool:
    target_email = share.recipient_email or (share.shared_with.email if share.shared_with else None)
    if not target_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No recipient email address assigned to this share link."
        )

    # 45-second rate limit on OTP resends
    if share.otp_last_sent_at:
        seconds_since_last = (datetime.utcnow() - share.otp_last_sent_at).total_seconds()
        if seconds_since_last < 45:
            remaining = int(45 - seconds_since_last)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {remaining} seconds before requesting a new OTP verification code."
            )

    otp_code = f"{secrets.randbelow(900000) + 100000}"
    share.otp_code_hash = get_password_hash(otp_code)
    share.otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
    share.otp_attempts = 0
    share.otp_last_sent_at = datetime.utcnow()
    db.commit()

    filename = share.file.original_name if share.file else "Shared File"
    email_sent = send_share_otp_email(to_email=target_email, otp_code=otp_code, filename=filename)

    log_activity(
        db,
        action=AuditAction.OTP_SENT,
        user_id=share.shared_by_id,
        user_email=share.shared_by.email if share.shared_by else "System",
        resource=f"Share:{share.id}",
        details=f"Dispatched 6-digit OTP code to recipient: {target_email}",
        success=email_sent,
        ip_address=ip_address
    )

    return email_sent

def verify_share_otp(db: Session, share: FileShare, otp: str, ip_address: str = None) -> bool:
    if not share.requires_otp:
        return True

    target_email = share.recipient_email or (share.shared_with.email if share.shared_with else "Recipient")

    if share.otp_attempts >= 5:
        log_activity(
            db,
            action=AuditAction.OTP_FAILED,
            user_id=None,
            user_email=target_email,
            resource=f"Share:{share.id}",
            details="Maximum OTP verification attempts exceeded (5/5)",
            success=False,
            ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed OTP attempts. Please request a new OTP code."
        )

    if not share.otp_code_hash or not share.otp_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active OTP code requested. Please click 'Send OTP'."
        )

    if datetime.utcnow() > share.otp_expires_at:
        share.otp_attempts += 1
        db.commit()
        log_activity(
            db,
            action=AuditAction.OTP_FAILED,
            user_id=None,
            user_email=target_email,
            resource=f"Share:{share.id}",
            details="Entered expired OTP code",
            success=False,
            ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP code has expired. Please request a new OTP code."
        )

    if not verify_password(otp, share.otp_code_hash):
        share.otp_attempts += 1
        db.commit()
        log_activity(
            db,
            action=AuditAction.OTP_FAILED,
            user_id=None,
            user_email=target_email,
            resource=f"Share:{share.id}",
            details=f"Invalid OTP code attempt ({share.otp_attempts}/5)",
            success=False,
            ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP verification code. Please check and try again."
        )

    share.otp_attempts = 0
    db.commit()

    log_activity(
        db,
        action=AuditAction.OTP_VERIFIED,
        user_id=None,
        user_email=target_email,
        resource=f"Share:{share.id}",
        details="OTP successfully verified for shared file access",
        success=True,
        ip_address=ip_address
    )

    return True

def verify_share_password_action(db: Session, share: FileShare, password: str, ip_address: str = None) -> bool:
    target_email = share.recipient_email or (share.shared_with.email if share.shared_with else "Recipient")

    if not share.password_hash and not share.requires_password:
        return True

    if not password or not verify_password(password, share.password_hash):
        log_activity(
            db,
            action=AuditAction.PASSWORD_FAILED,
            user_id=None,
            user_email=target_email,
            resource=f"Share:{share.id}",
            details="Incorrect share password attempt",
            success=False,
            ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password for shared file"
        )

    log_activity(
        db,
        action=AuditAction.PASSWORD_VERIFIED,
        user_id=None,
        user_email=target_email,
        resource=f"Share:{share.id}",
        details="Share password successfully verified",
        success=True,
        ip_address=ip_address
    )

    return True

def get_share_access_and_validate(
    db: Session,
    share_id: int,
    requesting_user: Optional[User] = None,
    required_permission: SharePermission = SharePermission.VIEW,
    password: Optional[str] = None,
    otp_verified: bool = False,
    ip_address: str = None
) -> Tuple[FileShare, File]:

    share = db.query(FileShare).filter(FileShare.id == share_id).first()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share record not found")

    user_id = requesting_user.id if requesting_user else None
    user_email = requesting_user.email if requesting_user else (share.recipient_email or "Recipient")

    # 1. Check revocation / active status
    if share.is_revoked or not share.is_active:
        log_activity(
            db,
            action=AuditAction.SHARE_REVOKED,
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
            detail="This sharing link has expired. Please contact the sender and request a new sharing link."
        )

    # 3. Check recipient identity if recipient is specifically assigned
    is_owner = requesting_user and requesting_user.id == share.shared_by_id
    is_recipient = requesting_user and (
        requesting_user.id == share.shared_with_id or 
        (share.recipient_email and requesting_user.email and share.recipient_email.lower() == requesting_user.email.lower())
    )

    if share.shared_with_id is not None or share.recipient_email is not None:
        if requesting_user and not is_recipient and not is_owner:
            log_activity(
                db,
                action=AuditAction.SHARE_ACCESS_DENIED,
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

    # 4. Check OTP verification requirement (Bypassed if requesting_user is owner or recipient logged into their account)
    if share.requires_otp and not otp_verified and not is_owner and not is_recipient:
        log_activity(
            db,
            action=AuditAction.ACCESS_DENIED,
            user_id=user_id,
            user_email=user_email,
            resource=f"Share:{share_id}",
            details="Attempted access without OTP verification",
            success=False,
            ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="OTP verification required before accessing this shared file."
        )

    # 5. Check password protection (Bypassed if requesting_user is owner)
    if (share.password_hash or share.requires_password) and not is_owner:
        if not password or not verify_password(password, share.password_hash):
            log_activity(
                db,
                action=AuditAction.INVALID_SHARE_PASSWORD,
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

    # 6. Check file deletion
    db_file = db.query(File).filter(File.id == share.file_id, File.is_deleted == False).first()
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The shared file has been deleted by its owner"
        )

    # 7. Check permission level & download limits
    if required_permission == SharePermission.DOWNLOAD:
        if share.permission not in (SharePermission.DOWNLOAD, SharePermission.EDIT):
            log_activity(
                db,
                action=AuditAction.SHARE_ACCESS_DENIED,
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
                action=AuditAction.DOWNLOAD_LIMIT_REACHED,
                user_id=user_id,
                user_email=user_email,
                resource=f"Share:{share_id}",
                details=f"Download limit ({share.max_downloads}) reached",
                success=False,
                ip_address=ip_address
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Download limit reached."
            )

    share.last_accessed_at = datetime.utcnow()
    db.commit()

    log_activity(
        db,
        action=AuditAction.SHARE_ACCESS_GRANTED,
        user_id=user_id,
        user_email=user_email,
        resource=f"Share:{share_id}",
        details="Multi-factor security validation passed - Access Granted",
        success=True,
        ip_address=ip_address
    )

    return share, db_file

def get_share_by_token(
    db: Session,
    token: str,
    requesting_user: Optional[User] = None,
    password: Optional[str] = None,
    otp_verified: bool = False,
    ip_address: str = None
) -> Tuple[FileShare, File]:

    clean_token = token.strip() if token else ""
    th = hash_token(clean_token)
    share = db.query(FileShare).filter(
        (FileShare.token_hash == th) | 
        (FileShare.share_token == clean_token) |
        (FileShare.share_code == clean_token.upper())
    ).first()

    if not share:
        log_activity(
            db,
            action=AuditAction.INVALID_SHARE_TOKEN,
            user_id=requesting_user.id if requesting_user else None,
            user_email=requesting_user.email if requesting_user else "Anonymous",
            resource="ShareToken:Invalid",
            details="Recipient attempted access with an invalid share token",
            success=False,
            ip_address=ip_address
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid share token")

    user_id = requesting_user.id if requesting_user else None
    user_email = requesting_user.email if requesting_user else (share.recipient_email or "Anonymous")

    log_activity(
        db,
        action=AuditAction.SHARE_ACCESS_ATTEMPT,
        user_id=user_id,
        user_email=user_email,
        resource=f"Share:{share.id}",
        details=f"Recipient opened secure share link for File:{share.file_id}",
        success=True,
        ip_address=ip_address
    )

    return get_share_access_and_validate(
        db, share_id=share.id, requesting_user=requesting_user,
        required_permission=SharePermission.VIEW, password=password,
        otp_verified=otp_verified, ip_address=ip_address
    )

def increment_share_download(db: Session, share: FileShare, user: Optional[User] = None, ip_address: str = None):
    share.download_count += 1
    share.last_accessed_at = datetime.utcnow()
    share.last_downloaded_at = datetime.utcnow()

    if share.one_time_access:
        share.is_revoked = True
        share.is_active = False

    db.commit()

    user_id = user.id if user else None
    user_email = user.email if user else (share.recipient_email or "Anonymous")
    
    log_activity(
        db,
        action=AuditAction.FILE_DOWNLOADED,
        user_id=user_id,
        user_email=user_email,
        resource=f"Share:{share.id}:File:{share.file_id}",
        details=f"Downloaded file via secure share link (Total downloads: {share.download_count})",
        success=True,
        ip_address=ip_address
    )

    if share.one_time_access:
        log_activity(
            db,
            action=AuditAction.SHARE_REVOKED,
            user_id=user_id,
            user_email=user_email,
            resource=f"Share:{share.id}",
            details="One-time secure access completed - share link automatically revoked",
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
        share.requires_password = bool(update_in.password)

    if update_in.requires_otp is not None:
        share.requires_otp = update_in.requires_otp

    if update_in.requires_password is not None:
        share.requires_password = update_in.requires_password

    if update_in.one_time_access is not None:
        share.one_time_access = update_in.one_time_access

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
        details=f"Updated share configuration (Permission: {share.permission}, Limit: {share.max_downloads}, OTP: {share.requires_otp})",
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
        resource=f"Share:{share.id}",
        details=f"Revoked share ID {share.id}",
        success=True,
        ip_address=ip_address
    )

    return share
