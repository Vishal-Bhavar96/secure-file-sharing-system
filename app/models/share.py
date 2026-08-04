import enum
import secrets
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship, synonym
from datetime import datetime
from app.database.session import Base

class SharePermission(str, enum.Enum):
    VIEW = "VIEW"
    DOWNLOAD = "DOWNLOAD"
    EDIT = "EDIT"

def generate_share_token():
    return secrets.token_hex(16)

class FileShare(Base):
    __tablename__ = "file_shares"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    shared_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    shared_with_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    permission = Column(Enum(SharePermission), default=SharePermission.DOWNLOAD, nullable=False)
    share_token = Column(String(100), unique=True, index=True, nullable=True, default=generate_share_token)
    password_hash = Column(String(255), nullable=True)
    expiry_at = Column(DateTime, nullable=True)
    max_downloads = Column(Integer, nullable=True)  # Null means unlimited
    download_count = Column(Integer, default=0, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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

# Class alias for Table/Model specification
SharedFiles = FileShare

