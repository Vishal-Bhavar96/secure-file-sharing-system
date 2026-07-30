import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException, status
from app.config.settings import settings

class EncryptionService:
    def __init__(self, master_key: bytes = None):
        if master_key is None:
            self.master_key = settings.get_raw_encryption_key()
        else:
            self.master_key = master_key
            
        if len(self.master_key) < 32:
            self.master_key = self.master_key.ljust(32, b'\0')[:32]
        else:
            self.master_key = self.master_key[:32]

    def encrypt_data(self, data: bytes) -> bytes:

        try:
            aesgcm = AESGCM(self.master_key)
            nonce = os.urandom(12)  # 96-bit nonce
            ciphertext = aesgcm.encrypt(nonce, data, None)
            return nonce + ciphertext
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Encryption failure: {str(e)}"
            )

    def decrypt_data(self, encrypted_payload: bytes) -> bytes:

        if not encrypted_payload or len(encrypted_payload) < 28:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Encrypted data payload is corrupted or too short"
            )
            
        try:
            aesgcm = AESGCM(self.master_key)
            nonce = encrypted_payload[:12]
            ciphertext = encrypted_payload[12:]
            return aesgcm.decrypt(nonce, ciphertext, None)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Decryption failed: File data is corrupted or encryption key is invalid"
            )

encryption_service = EncryptionService()
