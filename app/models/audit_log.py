import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.session import Base

class AuditAction(str, enum.Enum):
    USER_REGISTERED = "USER_REGISTERED"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    FILE_UPLOADED = "FILE_UPLOADED"
    FILE_DOWNLOADED = "FILE_DOWNLOADED"
    FILE_DELETED = "FILE_DELETED"
    FILE_SHARED = "FILE_SHARED"
    LINK_OPENED = "LINK_OPENED"
    DOWNLOAD_SUCCESS = "DOWNLOAD_SUCCESS"
    DOWNLOAD_BLOCKED = "DOWNLOAD_BLOCKED"
    SHARE_REVOKED = "SHARE_REVOKED"
    PERMISSION_UPDATED = "PERMISSION_UPDATED"
    PERMISSION_CHANGED = "PERMISSION_CHANGED"
    SHARE_EXPIRED = "SHARE_EXPIRED"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    FOLDER_CREATED = "FOLDER_CREATED"
    FILE_MOVED = "FILE_MOVED"
    PROFILE_UPDATED = "PROFILE_UPDATED"
    PROFILE_PHOTO_UPDATED = "PROFILE_PHOTO_UPDATED"
    PROFILE_PHOTO_REMOVED = "PROFILE_PHOTO_REMOVED"
    EMAIL_CHANGED = "EMAIL_CHANGED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    ACCOUNT_SETTINGS_UPDATED = "ACCOUNT_SETTINGS_UPDATED"
    SESSION_REVOKED = "SESSION_REVOKED"

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user_email = Column(String(150), nullable=True)
    action = Column(Enum(AuditAction), nullable=False, index=True)
    resource = Column(String(255), nullable=True)
    details = Column(Text, nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="audit_logs")
