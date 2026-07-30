from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
from app.database.session import get_db
from app.models.user import User
from app.models.share import FileShare, SharePermission
from app.schemas.share import ShareCreateRequest, ShareOut
from app.security.jwt import get_current_user
from app.services.share_service import (
    create_file_share, get_share_access_and_validate, 
    increment_share_download, revoke_file_share
)
from app.services.file_service import download_and_decrypt_file

router = APIRouter(prefix="/shares", tags=["File Sharing"])

@router.post("", response_model=ShareOut, status_code=status.HTTP_201_CREATED)
def share_file(
    share_in: ShareCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    share_obj = create_file_share(db, owner=current_user, share_in=share_in, ip_address=ip)
    
    is_expired = share_obj.expiry_at is not None and datetime.utcnow() > share_obj.expiry_at
    return ShareOut(
        id=share_obj.id,
        file_id=share_obj.file_id,
        filename=share_obj.file.original_name if share_obj.file else "",
        shared_by_id=share_obj.shared_by_id,
        shared_by_email=share_obj.shared_by.email if share_obj.shared_by else "",
        shared_with_id=share_obj.shared_with_id,
        shared_with_email=share_obj.shared_with.email if share_obj.shared_with else "",
        permission=share_obj.permission,
        expiry_at=share_obj.expiry_at,
        max_downloads=share_obj.max_downloads,
        download_count=share_obj.download_count,
        is_revoked=share_obj.is_revoked,
        is_expired=is_expired,
        created_at=share_obj.created_at
    )

@router.get("/created", response_model=List[ShareOut])
def get_shares_created_by_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    shares = db.query(FileShare).filter(FileShare.shared_by_id == current_user.id).order_by(FileShare.created_at.desc()).all()
    out = []
    now = datetime.utcnow()
    for s in shares:
        out.append(ShareOut(
            id=s.id,
            file_id=s.file_id,
            filename=s.file.original_name if s.file else "",
            shared_by_id=s.shared_by_id,
            shared_by_email=s.shared_by.email if s.shared_by else "",
            shared_with_id=s.shared_with_id,
            shared_with_email=s.shared_with.email if s.shared_with else "",
            permission=s.permission,
            expiry_at=s.expiry_at,
            max_downloads=s.max_downloads,
            download_count=s.download_count,
            is_revoked=s.is_revoked,
            is_expired=s.expiry_at is not None and now > s.expiry_at,
            created_at=s.created_at
        ))
    return out

@router.get("/received", response_model=List[ShareOut])
def get_shares_received_by_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    shares = db.query(FileShare).filter(FileShare.shared_with_id == current_user.id, FileShare.is_revoked == False).order_by(FileShare.created_at.desc()).all()
    out = []
    now = datetime.utcnow()
    for s in shares:
        is_expired = s.expiry_at is not None and now > s.expiry_at
        out.append(ShareOut(
            id=s.id,
            file_id=s.file_id,
            filename=s.file.original_name if s.file else "",
            shared_by_id=s.shared_by_id,
            shared_by_email=s.shared_by.email if s.shared_by else "",
            shared_with_id=s.shared_with_id,
            shared_with_email=s.shared_with.email if s.shared_with else "",
            permission=s.permission,
            expiry_at=s.expiry_at,
            max_downloads=s.max_downloads,
            download_count=s.download_count,
            is_revoked=s.is_revoked,
            is_expired=is_expired,
            created_at=s.created_at
        ))
    return out

@router.get("/{share_id}/download")
def download_shared_file(
    share_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    
    # 1. Validate permissions, expiration, download limits
    share, db_file = get_share_access_and_validate(
        db, share_id=share_id, requesting_user=current_user,
        required_permission=SharePermission.DOWNLOAD, ip_address=ip
    )

    # 2. Decrypt & retrieve payload
    decrypted_bytes, filename, mime_type = download_and_decrypt_file(
        db, db_file=db_file, requesting_user=current_user, ip_address=ip
    )

    # 3. Increment download counter
    increment_share_download(db, share)

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(io.BytesIO(decrypted_bytes), media_type=mime_type, headers=headers)

@router.delete("/{share_id}/revoke")
def revoke_share(
    share_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    revoke_file_share(db, share_id=share_id, owner=current_user, ip_address=ip)
    return {"message": "Share revoked successfully"}
