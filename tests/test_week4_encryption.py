import pytest
from app.services.encryption_service import EncryptionService, encryption_service

def test_aes_encryption_and_decryption_integrity():

    payload = b"Top secret binary & text data \x00\x01\x02 payload 12345"
    encrypted = encryption_service.encrypt_data(payload)
    
    # Encrypted payload must differ from plain text
    assert encrypted != payload
    assert len(encrypted) > len(payload)
    
    # Decryption must restore identical data
    decrypted = encryption_service.decrypt_data(encrypted)
    assert decrypted == payload

def test_corrupted_encrypted_data_handling():

    payload = b"Test secret payload"
    encrypted = bytearray(encryption_service.encrypt_data(payload))
    
    # Corrupt several bytes in ciphertext
    encrypted[15] ^= 0xFF
    encrypted[20] ^= 0xFF

    with pytest.raises(Exception) as excinfo:
        encryption_service.decrypt_data(bytes(encrypted))
    assert "Decryption failed" in str(excinfo.value)
