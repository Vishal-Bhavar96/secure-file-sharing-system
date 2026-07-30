import os
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, status, UploadFile
from app.config.settings import settings
from app.models.file import File
from app.models.user import User, UserRole
from app.models.audit_log import AuditAction
from app.services.encryption_service import encryption_service
from app.services.audit_service import log_activity
from app.utils.path_security import sanitize_filename
from app.utils.validators import validate_file_metadata

def upload_file(
    db: Session,
    owner: User,
    file: UploadFile,
    folder: str = "/",
    ip_address: str = None
) -> File:

    # 1. Sanitize Filename (protect against path traversal like ../../private_file)
    safe_original_name = sanitize_filename(file.filename)
    
    # Read content & Validate Size
    content = file.file.read()
    file_size = len(content)
    
    validate_file_metadata(safe_original_name, file_size, file.content_type)
    
    # Generate unique encrypted disk filename
    file_uuid = uuid.uuid4().hex
    disk_filename = f"enc_{file_uuid}.dat"
    file_disk_path = os.path.join(settings.STORAGE_DIR, disk_filename)

    # 2. Encrypt Payload
    encrypted_payload = encryption_service.encrypt_data(content)

    # 3. Store securely on disk
    try:
        with open(file_disk_path, "wb") as f:
            f.write(encrypted_payload)
    except Exception as e:
        log_activity(db, AuditAction.FILE_UPLOADED, user_id=owner.id, user_email=owner.email, resource=safe_original_name, details=f"Disk save failure: {str(e)}", success=False, ip_address=ip_address)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Storage failure while saving encrypted file"
        )

    # 4. Save metadata in DB
    db_file = File(
        owner_id=owner.id,
        filename=disk_filename,
        original_name=safe_original_name,
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
        encrypted_path=file_disk_path,
        folder=folder if folder.startswith("/") else "/" + folder
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    log_activity(
        db,
        action=AuditAction.FILE_UPLOADED,
        user_id=owner.id,
        user_email=owner.email,
        resource=f"File:{db_file.id}:{safe_original_name}",
        details=f"Uploaded {file_size} bytes in folder {folder}",
        success=True,
        ip_address=ip_address
    )

    return db_file

def list_user_files(
    db: Session,
    user: User,
    folder: Optional[str] = None,
    search_query: Optional[str] = None,
    mime_filter: Optional[str] = None,
    sort_by: str = "date_desc"
) -> List[File]:

    query = db.query(File).filter(File.owner_id == user.id, File.is_deleted == False)

    if folder:
        query = query.filter(File.folder == folder)
    if search_query:
        query = query.filter(File.original_name.ilike(f"%{search_query}%"))
    if mime_filter:
        query = query.filter(File.mime_type.ilike(f"%{mime_filter}%"))

    if sort_by == "name_asc":
        query = query.order_by(File.original_name.asc())
    elif sort_by == "name_desc":
        query = query.order_by(File.original_name.desc())
    elif sort_by == "size_asc":
        query = query.order_by(File.file_size.asc())
    elif sort_by == "size_desc":
        query = query.order_by(File.file_size.desc())
    elif sort_by == "date_asc":
        query = query.order_by(File.created_at.asc())
    else:  # date_desc
        query = query.order_by(File.created_at.desc())

    return query.all()

def get_file_for_owner(db: Session, file_id: int, user: User, ip_address: str = None) -> File:

    db_file = db.query(File).filter(File.id == file_id, File.is_deleted == False).first()
    if not db_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if db_file.owner_id != user.id and user.role != UserRole.ADMIN:
        log_activity(
            db,
            action=AuditAction.UNAUTHORIZED_ACCESS,
            user_id=user.id,
            user_email=user.email,
            resource=f"File:{file_id}",
            details="User attempted to access unowned file without permission",
            success=False,
            ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not own this file"
        )

    return db_file

def download_and_decrypt_file(db: Session, db_file: File, requesting_user: User, ip_address: str = None) -> tuple[bytes, str, str]:

    if not os.path.exists(db_file.encrypted_path):
        log_activity(
            db,
            action=AuditAction.FILE_DOWNLOADED,
            user_id=requesting_user.id,
            user_email=requesting_user.email,
            resource=f"File:{db_file.id}:{db_file.original_name}",
            details="Encrypted file payload missing on disk",
            success=False,
            ip_address=ip_address
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File storage payload missing or removed"
        )

    try:
        with open(db_file.encrypted_path, "rb") as f:
            encrypted_content = f.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage read error: {str(e)}"
        )

    # Decrypt
    decrypted_content = encryption_service.decrypt_data(encrypted_content)

    log_activity(
        db,
        action=AuditAction.FILE_DOWNLOADED,
        user_id=requesting_user.id,
        user_email=requesting_user.email,
        resource=f"File:{db_file.id}:{db_file.original_name}",
        details=f"Downloaded {db_file.file_size} bytes",
        success=True,
        ip_address=ip_address
    )

    return decrypted_content, db_file.original_name, db_file.mime_type

def rename_file(db: Session, file_id: int, new_name: str, user: User, ip_address: str = None) -> File:

    db_file = get_file_for_owner(db, file_id, user, ip_address)
    safe_name = sanitize_filename(new_name)
    
    old_name = db_file.original_name
    db_file.original_name = safe_name
    db.commit()
    db.refresh(db_file)

    log_activity(
        db,
        action=AuditAction.PERMISSION_CHANGED,
        user_id=user.id,
        user_email=user.email,
        resource=f"File:{db_file.id}",
        details=f"Renamed file from '{old_name}' to '{safe_name}'",
        success=True,
        ip_address=ip_address
    )
    return db_file

def delete_file(db: Session, file_id: int, user: User, ip_address: str = None) -> bool:

    db_file = get_file_for_owner(db, file_id, user, ip_address)
    
    # Soft delete record
    db_file.is_deleted = True
    db.commit()

    # Clean up disk storage payload if exists
    if os.path.exists(db_file.encrypted_path):
        try:
            os.remove(db_file.encrypted_path)
        except Exception:
            pass

    log_activity(
        db,
        action=AuditAction.FILE_DELETED,
        user_id=user.id,
        user_email=user.email,
        resource=f"File:{file_id}:{db_file.original_name}",
        details="File deleted successfully",
        success=True,
        ip_address=ip_address
    )
    return True
