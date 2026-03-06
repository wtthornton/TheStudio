"""Webhook secret encryption/decryption using Fernet symmetric encryption.

Secrets are encrypted at rest. The encryption key is loaded from environment.
"""

from cryptography.fernet import Fernet

from src.settings import settings

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(settings.encryption_key.encode())
    return _fernet


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a webhook secret for storage."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a stored webhook secret."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()
