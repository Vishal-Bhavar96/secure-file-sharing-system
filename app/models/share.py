import enum
import secrets
import hashlib
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship, synonym
from datetime import datetime
from app.database.session import Base

class SharePermission(str, enum.Enum):
    VIEW = "VIEW"
    DOWNLOAD = "DOWNLOAD"
    EDIT = "EDIT"

def generate_share_token():
    return secrets.token_urlsafe(32)

def generate_share_code(length: int = 6) -> str:
    alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def hash_token(raw_token: str) -> str:
    if not raw_token:
        return ""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

class FileShare(Base):
    __tablename__ = "file_shares"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    shared_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    shared_with_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    recipient_email = Column(String(255), nullable=True)
    permission = Column(Enum(SharePermission), default=SharePermission.DOWNLOAD, nullable=False)
    share_token = Column(String(100), unique=True, index=True, nullable=True, default=generate_share_token)
    share_code = Column(String(20), unique=True, index=True, nullable=True, default=generate_share_code)
    token_hash = Column(String(255), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    requires_otp = Column(Boolean, default=False, nullable=False)
    otp_code_hash = Column(String(255), nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    otp_attempts = Column(Integer, default=0, nullable=False)
    otp_last_sent_at = Column(DateTime, nullable=True)
    requires_password = Column(Boolean, default=False, nullable=False)
    one_time_access = Column(Boolean, default=False, nullable=False)
    expiry_at = Column(DateTime, nullable=True)
    max_downloads = Column(Integer, nullable=True)  # Null means unlimited
    download_count = Column(Integer, default=0, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_accessed_at = Column(DateTime, nullable=True)
    last_downloaded_at = Column(DateTime, nullable=True)

    file = relationship("File", back_populates="shares")
    shared_by = relationship("User", foreign_keys=[shared_by_id], back_populates="shares_created")
    shared_with = relationship("User", foreign_keys=[shared_with_id], back_populates="shares_received")

    # Property Aliases for full spec compatibility
    @property
    def owner_id(self):
        return self.shared_by_id

    @owner_id.setter
    def owner_id(self, value):
        self.shared_by_id = value

    @property
    def shared_user_id(self):
        return self.shared_with_id

    @shared_user_id.setter
    def shared_user_id(self, value):
        self.shared_with_id = value

    @property
    def expiry_date(self):
        return self.expiry_at

    @expiry_date.setter
    def expiry_date(self, value):
        self.expiry_at = value

    @property
    def download_limit(self):
        return self.max_downloads

    @download_limit.setter
    def download_limit(self, value):
        self.max_downloads = value

    @property
    def downloads_used(self):
        return self.download_count

    @downloads_used.setter
    def downloads_used(self, value):
        self.download_count = value

    @property
    def is_expired(self) -> bool:
        if not self.expiry_at:
            return False
        return datetime.utcnow() > self.expiry_at

# Class alias for Table/Model specification
SharedFiles = FileShare

