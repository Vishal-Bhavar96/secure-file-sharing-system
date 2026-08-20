from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.share import SharePermission

class ShareCreateRequest(BaseModel):
    file_id: int
    target_user_identifier: Optional[str] = Field(None, description="Email or Username of target recipient")
    recipient_email: Optional[str] = Field(None, description="Recipient email address")
    permission: SharePermission = SharePermission.DOWNLOAD
    expiry_hours: Optional[int] = Field(None, ge=1, le=8760, description="Expiration in hours from now")
    expiry_date: Optional[datetime] = Field(None, description="Custom expiration datetime")
    max_downloads: Optional[int] = Field(None, ge=1, description="Maximum download count allowed")
    download_limit: Optional[int] = Field(None, ge=1, description="Maximum download count allowed (alias)")
    password: Optional[str] = Field(None, description="Optional separate share password")
    requires_otp: Optional[bool] = Field(False, description="Require 6-digit OTP verification")
    requires_password: Optional[bool] = Field(False, description="Require separate share password")
    one_time_access: Optional[bool] = Field(False, description="Auto-revoke share link after 1 successful download")

class ShareUpdateRequest(BaseModel):
    permission: Optional[SharePermission] = None
    expiry_hours: Optional[int] = Field(None, ge=1, le=8760)
    expiry_date: Optional[datetime] = None
    max_downloads: Optional[int] = Field(None, ge=1)
    download_limit: Optional[int] = Field(None, ge=1)
    password: Optional[str] = None
    requires_otp: Optional[bool] = None
    requires_password: Optional[bool] = None
    one_time_access: Optional[bool] = None
    is_active: Optional[bool] = None

class ShareTokenVerifyRequest(BaseModel):
    password: Optional[str] = None

class ShareOTPVerifyRequest(BaseModel):
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")

class SharePasswordVerifyRequest(BaseModel):
    password: str = Field(..., description="Separate share password")

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
    shared_by_name: Optional[str] = "Sender"
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
    requires_otp: bool = False
    requires_password: bool = False
    one_time_access: bool = False
    otp_verified: bool = False
    password_verified: bool = False
    expiry_at: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    max_downloads: Optional[int] = None
    download_limit: Optional[int] = None
    download_count: int = 0
    downloads_used: int = 0
    is_revoked: bool = False
    is_active: bool = True
    is_expired: bool = False
    recipient_email: Optional[str] = None
    email_sent: Optional[bool] = None
    last_accessed_at: Optional[datetime] = None
    last_downloaded_at: Optional[datetime] = None
    generated_password: Optional[str] = None
    message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

