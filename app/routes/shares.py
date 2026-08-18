import io
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Request, Response, status, Query, HTTPException
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
import qrcode
import qrcode.image.svg

from app.config.settings import settings
from app.database.session import get_db
from app.models.user import User
from app.models.share import FileShare, SharePermission
from app.models.audit_log import AuditAction
from app.schemas.share import ShareCreateRequest, ShareUpdateRequest, ShareOut, ShareTokenVerifyRequest
from app.security.jwt import get_current_user
from app.services.share_service import (
    create_file_share, get_share_access_and_validate, get_share_by_token,
    increment_share_download, update_file_share, revoke_file_share
)
from app.services.file_service import download_and_decrypt_file
from app.services.audit_service import log_activity
from app.routes.users import is_user_online, compute_last_seen_text

router = APIRouter(prefix="/shares", tags=["File Sharing"])

def build_share_out(s: FileShare, request: Optional[Request] = None) -> ShareOut:
    now = datetime.utcnow()
    is_expired = s.expiry_at is not None and now > s.expiry_at
    filename = s.file.original_name if s.file else ""
    shared_by_email = s.shared_by.email if s.shared_by else ""
    shared_with_email = s.shared_with.email if s.shared_with else ""
    
    shared_by_online = is_user_online(s.shared_by) if s.shared_by else False
    shared_by_last_seen = compute_last_seen_text(s.shared_by) if s.shared_by else "Offline"
    shared_with_online = is_user_online(s.shared_with) if s.shared_with else False
    shared_with_last_seen = compute_last_seen_text(s.shared_with) if s.shared_with else "Offline"

    # Construct public share URL using PUBLIC_APP_URL configuration
    base_url = settings.PUBLIC_APP_URL.rstrip('/') if getattr(settings, 'PUBLIC_APP_URL', None) else (str(request.base_url).rstrip('/') if request else "http://localhost:8000")
    share_url = f"{base_url}/#share/{s.share_token}" if s.share_token else None

    recipient_email = s.recipient_email or shared_with_email

    return ShareOut(
        id=s.id,
        file_id=s.file_id,
        filename=filename,
        owner_id=s.shared_by_id,
        shared_by_id=s.shared_by_id,
        shared_by_email=shared_by_email,
        shared_by_online=shared_by_online,
        shared_by_last_seen=shared_by_last_seen,
        shared_user_id=s.shared_with_id,
        shared_with_id=s.shared_with_id,
        shared_with_email=shared_with_email,
        shared_with_online=shared_with_online,
        shared_with_last_seen=shared_with_last_seen,
        recipient_email=recipient_email,
        permission=s.permission,
        share_token=s.share_token,
        share_url=share_url,
        has_password=bool(s.password_hash),
        expiry_at=s.expiry_at,
        expiry_date=s.expiry_at,
        max_downloads=s.max_downloads,
        download_limit=s.max_downloads,
        download_count=s.download_count,
        downloads_used=s.download_count,
        is_revoked=s.is_revoked,
        is_active=s.is_active and not s.is_revoked,
        is_expired=is_expired,
        last_accessed_at=s.last_accessed_at,
        created_at=s.created_at,
        updated_at=s.updated_at
    )

@router.post("", response_model=ShareOut, status_code=status.HTTP_201_CREATED)
def share_file(
    share_in: ShareCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    share_obj = create_file_share(db, owner=current_user, share_in=share_in, ip_address=ip)
    share_out = build_share_out(share_obj, request)

    target_email = share_obj.recipient_email
    if not target_email and share_obj.shared_with:
        target_email = share_obj.shared_with.email
    elif not target_email and share_in.target_user_identifier and "@" in share_in.target_user_identifier:
        target_email = share_in.target_user_identifier.strip()

    email_sent = False
    if target_email:
        from app.services.email_service import send_file_share_email
        email_sent = send_file_share_email(
            to_email=target_email,
            sender_name=current_user.name,
            sender_email=current_user.email,
            filename=share_obj.file.original_name if share_obj.file else "Shared File",
            share_url=share_out.share_url,
            permission=share_obj.permission.value,
            expiry_at=share_obj.expiry_at,
            has_password=bool(share_obj.password_hash)
        )

        if email_sent:
            log_activity(
                db,
                action=AuditAction.SHARE_EMAIL_SENT,
                user_id=current_user.id,
                user_email=current_user.email,
                resource=f"Share:{share_obj.id}",
                details=f"File share notification email dispatched to {target_email}",
                success=True,
                ip_address=ip
            )

    share_out.email_sent = email_sent
    share_out.message = "File shared successfully" if email_sent else "File shared successfully (email notification delivery pending SMTP configuration)"
    return share_out

@router.post("/{share_id}/resend", response_model=dict)
@router.post("/{share_id}/resend-email", response_model=dict)
def resend_share_email(
    share_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    share = db.query(FileShare).filter(FileShare.id == share_id).first()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share record not found")

    if share.shared_by_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the file owner can resend share notifications")

    if share.is_revoked or not share.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot resend email for a revoked share link")

    if share.expiry_at and datetime.utcnow() > share.expiry_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot resend email for an expired share link")

    target_email = share.recipient_email or (share.shared_with.email if share.shared_with else None)
    if not target_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No recipient email address assigned to this share link")

    share_out = build_share_out(share, request)
    from app.services.email_service import send_file_share_email
    email_sent = send_file_share_email(
        to_email=target_email,
        sender_name=current_user.name,
        sender_email=current_user.email,
        filename=share.file.original_name if share.file else "Shared File",
        share_url=share_out.share_url,
        permission=share.permission.value,
        expiry_at=share.expiry_at,
        has_password=bool(share.password_hash)
    )

    ip = request.client.host if request.client else None
    if email_sent:
        log_activity(
            db,
            action=AuditAction.SHARE_EMAIL_SENT,
            user_id=current_user.id,
            user_email=current_user.email,
            resource=f"Share:{share.id}",
            details=f"Resent file share email notification to {target_email}",
            success=True,
            ip_address=ip
        )
        return {"success": True, "message": f"Share notification email successfully sent to {target_email}", "email_sent": True}
    else:
        return {"success": False, "message": f"Share notification logged for {target_email}. Configure SMTP in environment for real inbox delivery.", "email_sent": False}

@router.get("/created", response_model=List[ShareOut])
def get_shares_created_by_me(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    shares = db.query(FileShare).filter(FileShare.shared_by_id == current_user.id).order_by(FileShare.created_at.desc()).all()
    return [build_share_out(s, request) for s in shares]

@router.get("/received", response_model=List[ShareOut])
def get_shares_received_by_me(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    shares = db.query(FileShare).filter(
        FileShare.shared_with_id == current_user.id,
        FileShare.is_revoked == False,
        FileShare.is_active == True
    ).order_by(FileShare.created_at.desc()).all()
    return [build_share_out(s, request) for s in shares]

@router.get("/{share_id}", response_model=ShareOut)
def get_share_details(
    share_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    share = db.query(FileShare).filter(FileShare.id == share_id).first()
    if not share:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share record not found")
    if share.shared_by_id != current_user.id and share.shared_with_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return build_share_out(share, request)

@router.put("/{share_id}", response_model=ShareOut)
def update_share(
    share_id: int,
    update_in: ShareUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    share_obj = update_file_share(db, share_id=share_id, owner=current_user, update_in=update_in, ip_address=ip)
    return build_share_out(share_obj, request)

@router.delete("/{share_id}/revoke")
def revoke_share(
    share_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    revoke_file_share(db, share_id=share_id, owner=current_user, ip_address=ip)
    return {"message": "Share revoked successfully", "is_revoked": True}

@router.get("/token/{share_token}", response_model=ShareOut)
def get_token_share_info(
    share_token: str,
    request: Request,
    password: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    share, _ = get_share_by_token(db, token=share_token, password=password, ip_address=ip)
    return build_share_out(share, request)

@router.post("/token/{share_token}/verify", response_model=ShareOut)
def verify_token_share_password(
    share_token: str,
    verify_in: ShareTokenVerifyRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    share, _ = get_share_by_token(db, token=share_token, password=verify_in.password, ip_address=ip)
    return build_share_out(share, request)

@router.get("/token/{share_token}/download")
def download_by_token(
    share_token: str,
    request: Request,
    password: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    share, db_file = get_share_by_token(db, token=share_token, password=password, ip_address=ip)

    # Re-validate with required DOWNLOAD permission
    share, db_file = get_share_access_and_validate(
        db, share_id=share.id, required_permission=SharePermission.DOWNLOAD,
        password=password, ip_address=ip
    )

    decrypted_bytes, filename, mime_type = download_and_decrypt_file(
        db, db_file=db_file, requesting_user=share.file.owner if share.file else None, ip_address=ip
    )

    increment_share_download(db, share, ip_address=ip)

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(io.BytesIO(decrypted_bytes), media_type=mime_type, headers=headers)

@router.get("/{share_id}/download")
def download_shared_file(
    share_id: int,
    request: Request,
    password: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    
    # 1. Validate permissions, expiration, download limits, password
    share, db_file = get_share_access_and_validate(
        db, share_id=share_id, requesting_user=current_user,
        required_permission=SharePermission.DOWNLOAD, password=password, ip_address=ip
    )

    # 2. Decrypt & retrieve payload
    decrypted_bytes, filename, mime_type = download_and_decrypt_file(
        db, db_file=db_file, requesting_user=current_user, ip_address=ip
    )

    # 3. Increment download counter
    increment_share_download(db, share, user=current_user, ip_address=ip)

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(io.BytesIO(decrypted_bytes), media_type=mime_type, headers=headers)

@router.get("/{share_id}/qr")
def generate_share_qr_code(
    share_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    share = db.query(FileShare).filter(FileShare.id == share_id).first()
    if not share or not share.share_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share token not found")

    base_url = settings.PUBLIC_APP_URL.rstrip('/') if getattr(settings, 'PUBLIC_APP_URL', None) else str(request.base_url).rstrip('/')
    share_url = f"{base_url}/#share/{share.share_token}"

    img = qrcode.make(share_url, image_factory=qrcode.image.svg.SvgImage)
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    return Response(content=buf.getvalue(), media_type="image/svg+xml")
