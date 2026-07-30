import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.session import Base

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    USER = "USER"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    files = relationship("File", back_populates="owner", cascade="all, delete-orphan")
    shares_created = relationship("FileShare", foreign_keys="FileShare.shared_by_id", back_populates="shared_by")
    shares_received = relationship("FileShare", foreign_keys="FileShare.shared_with_id", back_populates="shared_with")
    audit_logs = relationship("AuditLog", back_populates="user")
