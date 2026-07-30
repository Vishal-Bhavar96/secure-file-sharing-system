from typing import List, Optional
from fastapi import APIRouter, Depends, Request, UploadFile, File as FastAPIFile, Form, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
from app.database.session import get_db
from app.models.user import User
from app.schemas.file import FileOut, FileRenameRequest
from app.security.jwt import get_current_user
from app.services.file_service import (
    upload_file, list_user_files, get_file_for_owner, 
    download_and_decrypt_file, rename_file, delete_file
)

router = APIRouter(prefix="/files", tags=["Files"])

@router.post("/upload", response_model=FileOut, status_code=status.HTTP_201_CREATED)
def upload(
    request: Request,
    file: UploadFile = FastAPIFile(...),
    folder: str = Form("/"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    return upload_file(db, owner=current_user, file=file, folder=folder, ip_address=ip)

@router.get("", response_model=List[FileOut])
def list_files(
    folder: Optional[str] = None,
    search: Optional[str] = None,
    mime_type: Optional[str] = None,
    sort_by: str = "date_desc",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return list_user_files(
        db, user=current_user, folder=folder, 
        search_query=search, mime_filter=mime_type, sort_by=sort_by
    )

@router.get("/{file_id}", response_model=FileOut)
def get_file_details(
    file_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    return get_file_for_owner(db, file_id=file_id, user=current_user, ip_address=ip)

@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    db_file = get_file_for_owner(db, file_id=file_id, user=current_user, ip_address=ip)
    decrypted_bytes, filename, mime_type = download_and_decrypt_file(db, db_file=db_file, requesting_user=current_user, ip_address=ip)
    
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(io.BytesIO(decrypted_bytes), media_type=mime_type, headers=headers)

@router.put("/{file_id}/rename", response_model=FileOut)
def rename(
    file_id: int,
    rename_in: FileRenameRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    return rename_file(db, file_id=file_id, new_name=rename_in.new_name, user=current_user, ip_address=ip)

@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_file(
    file_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    delete_file(db, file_id=file_id, user=current_user, ip_address=ip)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
