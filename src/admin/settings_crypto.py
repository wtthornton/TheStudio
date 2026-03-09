"""Fernet encryption helpers for settings at-rest encryption.

Story 12.1: Settings Data Model & Encrypted Storage.
Uses THESTUDIO_ENCRYPTION_KEY from environment for symmetric encryption.
"""

from __future__ import annotations

import logging

from cryptography.fernet import Fernet

from src.settings import settings

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet:
    """Get Fernet instance using the configured encryption key."""
    key = settings.encryption_key
    if not key or key == "generate-a-real-fernet-key-for-production":
        logger.warning("Using default encryption key — generate a real Fernet key for production")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string and return base64-encoded ciphertext."""
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a base64-encoded ciphertext string.

    Raises:
        InvalidToken: If the ciphertext is invalid or the key is wrong.
    """
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()


def generate_fernet_key() -> str:
    """Generate a new Fernet key (for key rotation)."""
    return Fernet.generate_key().decode()
