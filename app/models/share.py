import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.session import Base

class SharePermission(str, enum.Enum):
    VIEW = "VIEW"
    DOWNLOAD = "DOWNLOAD"
    EDIT = "EDIT"

class FileShare(Base):
    __tablename__ = "file_shares"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    shared_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    shared_with_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    permission = Column(Enum(SharePermission), default=SharePermission.DOWNLOAD, nullable=False)
    expiry_at = Column(DateTime, nullable=True)
    max_downloads = Column(Integer, nullable=True)  # Null means unlimited
    download_count = Column(Integer, default=0, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    file = relationship("File", back_populates="shares")
    shared_by = relationship("User", foreign_keys=[shared_by_id], back_populates="shares_created")
    shared_with = relationship("User", foreign_keys=[shared_with_id], back_populates="shares_received")
