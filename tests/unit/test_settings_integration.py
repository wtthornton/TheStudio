"""Integration tests for Settings feature (Epic 12).

Story 12.8: Integration Tests & E2E Validation.
Tests the full settings stack: service, crypto, validation, hot reload, UI routes.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from src.admin.persistence.pg_settings import SettingCategory, SettingRow
from src.admin.settings_crypto import decrypt_value, encrypt_value
from src.admin.settings_service import (
    RESTART_REQUIRED_KEYS,
    SENSITIVE_KEYS,
    SettingsService,
    mask_value,
    validate_setting,
)


# --- Encryption round-trip tests ---


class TestEncryptionRoundtrip:
    """Test that encryption and decryption work end-to-end."""

    def test_roundtrip_api_key(self):
        key = Fernet.generate_key().decode()
        with patch("src.admin.settings_crypto.settings") as mock_settings:
            mock_settings.encryption_key = key
            original = "sk-ant-api03-very-secret-key-1234567890"
            encrypted = encrypt_value(original)
            assert encrypted != original
            decrypted = decrypt_value(encrypted)
            assert decrypted == original

    def test_roundtrip_unicode(self):
        key = Fernet.generate_key().decode()
        with patch("src.admin.settings_crypto.settings") as mock_settings:
            mock_settings.encryption_key = key
            original = "postgresql+asyncpg://user:p@ss%C3%A9@host/db"
            decrypted = decrypt_value(encrypt_value(original))
            assert decrypted == original

    def test_different_keys_fail(self):
        key1 = Fernet.generate_key().decode()
        key2 = Fernet.generate_key().decode()

        with patch("src.admin.settings_crypto.settings") as mock_settings:
            mock_settings.encryption_key = key1
            encrypted = encrypt_value("secret")

        with patch("src.admin.settings_crypto.settings") as mock_settings:
            mock_settings.encryption_key = key2
            with pytest.raises(Exception):
                decrypt_value(encrypted)


# --- RBAC enforcement tests ---


class TestRBACEnforcement:
    """Verify settings are admin-only."""

    def test_manage_settings_only_in_admin_role(self):
        from src.admin.rbac import ROLE_PERMISSIONS, Permission, Role

        assert Permission.MANAGE_SETTINGS in ROLE_PERMISSIONS[Role.ADMIN]
        assert Permission.MANAGE_SETTINGS not in ROLE_PERMISSIONS[Role.OPERATOR]
        assert Permission.MANAGE_SETTINGS not in ROLE_PERMISSIONS[Role.VIEWER]


# --- Audit event type tests ---


class TestAuditEventType:
    """Verify SETTINGS_CHANGED is available."""

    def test_settings_changed_exists(self):
        from src.admin.audit import AuditEventType

        assert AuditEventType.SETTINGS_CHANGED == "settings_changed"


# --- Validation integration tests ---


class TestValidationIntegration:
    """Test validation rules for all setting types."""

    def test_bad_url_rejected(self):
        assert validate_setting("database_url", "not-a-url") is not None

    def test_good_url_accepted(self):
        assert validate_setting("database_url", "postgresql+asyncpg://u:p@h/d") is None

    def test_negative_budget_rejected(self):
        assert validate_setting("agent_max_budget_usd", "-1.0") is not None

    def test_zero_max_turns_rejected(self):
        assert validate_setting("agent_max_turns", "0") is not None

    def test_valid_max_turns_accepted(self):
        assert validate_setting("agent_max_turns", "30") is None

    def test_invalid_enum_rejected(self):
        assert validate_setting("llm_provider", "openai") is not None

    def test_valid_enum_accepted(self):
        assert validate_setting("llm_provider", "anthropic") is None

    def test_bad_host_port_rejected(self):
        assert validate_setting("temporal_host", "just-hostname") is not None

    def test_good_host_port_accepted(self):
        assert validate_setting("temporal_host", "localhost:7233") is None


# --- Hot reload tests ---


class TestHotReload:
    def test_reload_signal_fires_on_set(self):
        svc = SettingsService()
        received = []
        svc.subscribe_reload(lambda k: received.append(k))
        svc._notify_reload("agent_model")
        assert received == ["agent_model"]
        assert svc.generation == 1

    def test_generation_counter_increments(self):
        svc = SettingsService()
        assert svc.generation == 0
        svc._notify_reload("a")
        assert svc.generation == 1
        svc._notify_reload("b")
        assert svc.generation == 2

    def test_subscriber_receives_changed_key(self):
        svc = SettingsService()
        keys = []
        svc.subscribe_reload(lambda k: keys.append(k))
        svc._notify_reload("llm_provider")
        assert keys == ["llm_provider"]

    def test_multiple_subscribers_all_notified(self):
        svc = SettingsService()
        a, b, c = [], [], []
        svc.subscribe_reload(lambda k: a.append(k))
        svc.subscribe_reload(lambda k: b.append(k))
        svc.subscribe_reload(lambda k: c.append(k))
        svc._notify_reload("test")
        assert a == ["test"]
        assert b == ["test"]
        assert c == ["test"]

    def test_restart_required_keys_defined(self):
        assert "database_url" in RESTART_REQUIRED_KEYS
        assert "temporal_host" in RESTART_REQUIRED_KEYS
        assert "nats_url" in RESTART_REQUIRED_KEYS
        assert "agent_model" not in RESTART_REQUIRED_KEYS


# --- Masking tests ---


class TestMasking:
    def test_api_key_masked(self):
        result = mask_value("sk-ant-api03-test-key-12345")
        assert result.endswith("2345")
        assert "sk-ant" not in result

    def test_empty_string(self):
        assert mask_value("") == ""

    def test_short_string_fully_masked(self):
        assert mask_value("abc") == "****"


# --- Settings definition registry ---


class TestSettingDefinitions:
    def test_all_settings_have_categories(self):
        from src.admin.settings_service import SETTING_DEFINITIONS

        for key, defn in SETTING_DEFINITIONS.items():
            assert "category" in defn, f"{key} missing category"
            assert "sensitive" in defn, f"{key} missing sensitive flag"

    def test_sensitive_keys_match_definitions(self):
        from src.admin.settings_service import SETTING_DEFINITIONS

        for key in SENSITIVE_KEYS:
            assert key in SETTING_DEFINITIONS
            assert SETTING_DEFINITIONS[key]["sensitive"] is True

    def test_all_env_settings_covered(self):
        """Every field in Settings class should have a definition."""
        from src.admin.settings_service import SETTING_DEFINITIONS
        from src.settings import Settings

        for field_name in Settings.model_fields:
            assert field_name in SETTING_DEFINITIONS, (
                f"Settings.{field_name} is not in SETTING_DEFINITIONS"
            )


# --- Service CRUD tests with mocked session ---


class TestServiceCRUD:
    @pytest.fixture
    def service(self):
        return SettingsService()

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_get_unknown_key(self, service, mock_session):
        result = await service.get(mock_session, "totally_unknown")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_unknown_key_raises(self, service, mock_session):
        with pytest.raises(ValueError, match="Unknown"):
            await service.set(mock_session, "unknown_key", "value", "admin")

    @pytest.mark.asyncio
    async def test_set_invalid_value_raises(self, service, mock_session):
        with pytest.raises(ValueError):
            await service.set(mock_session, "agent_max_turns", "-5", "admin")
