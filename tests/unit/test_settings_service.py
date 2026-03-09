"""Unit tests for Settings Service and crypto helpers.

Story 12.1: Settings Data Model & Encrypted Storage.
Tests encryption round-trip, layered config, masking, and CRUD.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.admin.persistence.pg_settings import SettingCategory, SettingRow
from src.admin.settings_crypto import decrypt_value, encrypt_value, generate_fernet_key
from src.admin.settings_service import (
    SENSITIVE_KEYS,
    SettingsService,
    mask_value,
    validate_setting,
)


# --- Crypto tests ---


class TestCrypto:
    def test_encrypt_decrypt_roundtrip(self):
        """Fernet encrypt then decrypt returns original value."""
        with patch("src.admin.settings_crypto.settings") as mock_settings:
            from cryptography.fernet import Fernet

            key = Fernet.generate_key().decode()
            mock_settings.encryption_key = key
            original = "sk-ant-api03-test-key-12345"
            encrypted = encrypt_value(original)
            assert encrypted != original
            decrypted = decrypt_value(encrypted)
            assert decrypted == original

    def test_encrypt_uses_configured_key(self):
        """Encryption uses THESTUDIO_ENCRYPTION_KEY, not a hardcoded key."""
        from cryptography.fernet import Fernet

        key1 = Fernet.generate_key().decode()
        key2 = Fernet.generate_key().decode()

        with patch("src.admin.settings_crypto.settings") as mock_settings:
            mock_settings.encryption_key = key1
            encrypted1 = encrypt_value("test")

        with patch("src.admin.settings_crypto.settings") as mock_settings:
            mock_settings.encryption_key = key2
            # Should fail to decrypt with wrong key
            with pytest.raises(Exception):
                decrypt_value(encrypted1)

    def test_generate_fernet_key(self):
        """Generated key is a valid Fernet key."""
        from cryptography.fernet import Fernet

        key = generate_fernet_key()
        # Should not raise
        Fernet(key.encode())


# --- Mask tests ---


class TestMaskValue:
    def test_mask_shows_last_four(self):
        val = "sk-ant-api03-test-key-12345"
        result = mask_value(val)
        assert result.endswith("2345")
        assert len(result) == len(val)

    def test_mask_short_value(self):
        assert mask_value("abc") == "****"

    def test_mask_empty_value(self):
        assert mask_value("") == ""

    def test_mask_exactly_four(self):
        assert mask_value("abcd") == "****"


# --- Validation tests ---


class TestValidation:
    def test_valid_url(self):
        assert validate_setting("database_url", "postgresql+asyncpg://user:pass@host/db") is None

    def test_invalid_url(self):
        err = validate_setting("database_url", "not-a-url")
        assert err is not None
        assert "Invalid URL" in err

    def test_valid_host_port(self):
        assert validate_setting("temporal_host", "localhost:7233") is None

    def test_invalid_host_port(self):
        err = validate_setting("temporal_host", "localhost")
        assert err is not None
        assert "host:port" in err

    def test_valid_int(self):
        assert validate_setting("agent_max_turns", "30") is None

    def test_int_too_low(self):
        err = validate_setting("agent_max_turns", "0")
        assert err is not None

    def test_int_too_high(self):
        err = validate_setting("agent_max_turns", "101")
        assert err is not None

    def test_valid_float(self):
        assert validate_setting("agent_max_budget_usd", "5.0") is None

    def test_float_negative(self):
        err = validate_setting("agent_max_budget_usd", "-1")
        assert err is not None

    def test_valid_enum(self):
        assert validate_setting("llm_provider", "anthropic") is None

    def test_invalid_enum(self):
        err = validate_setting("llm_provider", "openai")
        assert err is not None

    def test_unknown_key_passes(self):
        assert validate_setting("unknown_key", "anything") is None


# --- SettingsService tests ---


class TestSettingsService:
    @pytest.fixture
    def service(self):
        return SettingsService()

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_get_returns_db_override(self, service, mock_session):
        """DB value takes precedence over env default."""
        row = MagicMock(spec=SettingRow)
        row.key = "agent_model"
        row.value = "claude-opus-4-6"
        row.encrypted = False
        row.updated_at = None
        row.updated_by = "admin"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = row
        mock_session.execute.return_value = mock_result

        result = await service.get(mock_session, "agent_model")
        assert result is not None
        assert result.value == "claude-opus-4-6"
        assert result.source == "db"

    @pytest.mark.asyncio
    async def test_get_falls_back_to_env_default(self, service, mock_session):
        """No DB value → falls back to env var."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await service.get(mock_session, "agent_model")
        assert result is not None
        assert result.source == "env"

    @pytest.mark.asyncio
    async def test_get_nonexistent_key_returns_none(self, service, mock_session):
        """Unknown key returns None."""
        result = await service.get(mock_session, "nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_validates_input(self, service, mock_session):
        """Invalid value raises ValueError."""
        with pytest.raises(ValueError, match="must be"):
            await service.set(mock_session, "agent_max_turns", "0", "admin")

    @pytest.mark.asyncio
    async def test_set_unknown_key_raises(self, service, mock_session):
        """Unknown setting key raises ValueError."""
        with pytest.raises(ValueError, match="Unknown setting key"):
            await service.set(mock_session, "nonexistent", "value", "admin")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self, service, mock_session):
        """Delete when no DB row returns False."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await service.delete(mock_session, "agent_model")
        assert result is False

    def test_sensitive_keys_registry(self):
        """SENSITIVE_KEYS includes expected keys."""
        assert "anthropic_api_key" in SENSITIVE_KEYS
        assert "database_url" in SENSITIVE_KEYS
        assert "encryption_key" in SENSITIVE_KEYS
        assert "webhook_secret" in SENSITIVE_KEYS
        assert "agent_model" not in SENSITIVE_KEYS

    def test_reload_signal(self, service):
        """Reload signal fires and increments generation."""
        received = []
        service.subscribe_reload(lambda key: received.append(key))

        service._notify_reload("test_key")
        assert received == ["test_key"]
        assert service.generation == 1

    def test_multiple_subscribers(self, service):
        """All subscribers notified on reload."""
        received_a = []
        received_b = []
        service.subscribe_reload(lambda key: received_a.append(key))
        service.subscribe_reload(lambda key: received_b.append(key))

        service._notify_reload("test_key")
        assert received_a == ["test_key"]
        assert received_b == ["test_key"]
