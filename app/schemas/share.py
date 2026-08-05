from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.share import SharePermission

class ShareCreateRequest(BaseModel):
    file_id: int
    target_user_identifier: Optional[str] = Field(None, description="Email or Username of target recipient")
    permission: SharePermission = SharePermission.DOWNLOAD
    expiry_hours: Optional[int] = Field(None, ge=1, le=8760, description="Expiration in hours from now")
    expiry_date: Optional[datetime] = Field(None, description="Custom expiration datetime")
    max_downloads: Optional[int] = Field(None, ge=1, description="Maximum download count allowed")
    download_limit: Optional[int] = Field(None, ge=1, description="Maximum download count allowed (alias)")
    password: Optional[str] = Field(None, description="Optional password protection")

class ShareUpdateRequest(BaseModel):
    permission: Optional[SharePermission] = None
    expiry_hours: Optional[int] = Field(None, ge=1, le=8760)
    expiry_date: Optional[datetime] = None
    max_downloads: Optional[int] = Field(None, ge=1)
    download_limit: Optional[int] = Field(None, ge=1)
    password: Optional[str] = None
    is_active: Optional[bool] = None

class ShareTokenVerifyRequest(BaseModel):
    password: Optional[str] = None

class ShareUserSearchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    username: Optional[str] = None

class ShareOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_id: int
    filename: str
    owner_id: int
    shared_by_id: int
    shared_by_email: str
    shared_by_online: bool = False
    shared_by_last_seen: str = "Offline"
    shared_user_id: Optional[int] = None
    shared_with_id: Optional[int] = None
    shared_with_email: Optional[str] = ""
    shared_with_online: bool = False
    shared_with_last_seen: str = "Offline"
    permission: SharePermission
    share_token: Optional[str] = None
    share_url: Optional[str] = None
    has_password: bool = False
    expiry_at: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    max_downloads: Optional[int] = None
    download_limit: Optional[int] = None
    download_count: int = 0
    downloads_used: int = 0
    is_revoked: bool = False
    is_active: bool = True
    is_expired: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

