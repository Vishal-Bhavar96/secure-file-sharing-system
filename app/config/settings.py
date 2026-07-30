import os
import base64
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "Secure File-Sharing System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str = Field(default="dev_secret_key_change_in_production_1234567890!")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Master Encryption key for AES-256 (32-byte key derived or base64)
    ENCRYPTION_KEY: str = Field(default="c3VwZXJfc2VjcmV0X2Flc18yNTZfbWFzdGVyX2tleV8xMjM0NQ==")
    
    # Storage settings
    STORAGE_DIR: str = "storage/uploads"
    MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    
    # Database
    DATABASE_URL: str = "sqlite:///./secure_sharing.db"

    class Config:
        env_file = ".env"
        extra = "ignore"

    def get_raw_encryption_key(self) -> bytes:
        """Returns 32 bytes binary key for AES-256"""
        try:
            decoded = base64.b64decode(self.ENCRYPTION_KEY)
            if len(decoded) >= 32:
                return decoded[:32]
            return decoded.ljust(32, b'\0')
        except Exception:
            return self.ENCRYPTION_KEY.encode('utf-8').ljust(32, b'\0')[:32]

settings = Settings()

# Ensure storage directory exists
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
