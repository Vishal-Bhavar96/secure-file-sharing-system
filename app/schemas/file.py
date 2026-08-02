from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    filename: str
    original_name: str
    file_size: int
    mime_type: Optional[str] = "application/octet-stream"
    folder: Optional[str] = "/"
    is_deleted: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

class FileRenameRequest(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=200)

class FileMoveRequest(BaseModel):
    target_folder: str = Field(..., min_length=1, max_length=255)

class FolderCreateRequest(BaseModel):
    folder_name: str = Field(..., min_length=1, max_length=100)
    parent_folder: Optional[str] = Field("/", max_length=255)

class FolderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    path: str
    parent_folder: str
    created_at: datetime

class FolderContentsOut(BaseModel):
    current_folder: str
    folders: List[FolderOut]
    files: List[FileOut]

