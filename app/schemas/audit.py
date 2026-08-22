from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.audit_log import AuditAction

class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int]
    user_email: Optional[str]
    action: AuditAction
    resource: Optional[str]
    details: Optional[str]
    success: bool
    ip_address: Optional[str]
    created_at: datetime

class SystemStatsOut(BaseModel):
    total_users: int
    total_students: int = 0
    total_admins: int = 0
    online_users_count: int = 0
    total_files: int
    storage_used_bytes: int
    active_shares: int
    expired_shares: int
    failed_login_attempts: int
    security_events: int
    most_downloaded_files: List[Dict[str, Any]]
