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
    mime_type: str
    folder: str
    created_at: datetime
    updated_at: datetime

class FileRenameRequest(BaseModel):
    new_name: str = Field(..., min_length=1, max_length=200)

class FolderCreateRequest(BaseModel):
    folder_name: str = Field(..., min_length=1, max_length=100)
