from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.share import SharePermission

class ShareCreateRequest(BaseModel):
    file_id: int
    target_user_identifier: str = Field(..., description="Email or Username of target recipient")
    permission: SharePermission = SharePermission.DOWNLOAD
    expiry_hours: Optional[int] = Field(None, ge=1, le=8760, description="Expiration in hours from now")
    max_downloads: Optional[int] = Field(None, ge=1, description="Maximum download count allowed")

class ShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_id: int
    filename: str
    shared_by_id: int
    shared_by_email: str
    shared_with_id: int
    shared_with_email: str
    permission: SharePermission
    expiry_at: Optional[datetime]
    max_downloads: Optional[int]
    download_count: int
    is_revoked: bool
    is_expired: bool
    created_at: datetime
