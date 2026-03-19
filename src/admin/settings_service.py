"""Settings Service — layered config with DB overrides and encryption.

Story 12.1: Settings Data Model & Encrypted Storage.
Story 12.5: Validation for connection strings.
Story 12.6: Encryption key rotation, webhook secret regeneration.
Story 12.7: Hot Reload & Settings Propagation.

Layered config pattern: DB values > env vars > defaults.
"""

from __future__ import annotations

import logging
import secrets
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.persistence.pg_settings import SettingCategory, SettingRow
from src.admin.settings_crypto import decrypt_value, encrypt_value
from src.settings import settings as env_settings

logger = logging.getLogger(__name__)


# --- Registry constants ---

SETTING_DEFINITIONS: dict[str, dict[str, Any]] = {
    # API Keys
    "anthropic_api_key": {"category": SettingCategory.API_KEYS, "sensitive": True},
    "anthropic_auth_mode": {"category": SettingCategory.API_KEYS, "sensitive": False},
    "anthropic_refresh_token": {"category": SettingCategory.API_KEYS, "sensitive": True},
    "anthropic_oauth_client_id": {"category": SettingCategory.API_KEYS, "sensitive": False},
    "github_app_id": {"category": SettingCategory.API_KEYS, "sensitive": False},
    "github_private_key_path": {"category": SettingCategory.API_KEYS, "sensitive": False},
    # Infrastructure
    "database_url": {"category": SettingCategory.INFRASTRUCTURE, "sensitive": True},
    "temporal_host": {"category": SettingCategory.INFRASTRUCTURE, "sensitive": False},
    "temporal_namespace": {"category": SettingCategory.INFRASTRUCTURE, "sensitive": False},
    "temporal_task_queue": {"category": SettingCategory.INFRASTRUCTURE, "sensitive": False},
    "nats_url": {"category": SettingCategory.INFRASTRUCTURE, "sensitive": False},
    "otel_service_name": {"category": SettingCategory.INFRASTRUCTURE, "sensitive": False},
    "otel_exporter": {"category": SettingCategory.INFRASTRUCTURE, "sensitive": False},
    "otel_otlp_endpoint": {"category": SettingCategory.INFRASTRUCTURE, "sensitive": False},
    # Feature Flags
    "intake_poll_enabled": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    "intake_poll_interval_minutes": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    "intake_poll_token": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": True},
    "llm_provider": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    "github_provider": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    "store_backend": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    "agent_llm_enabled": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    # Agent Config
    "agent_model": {"category": SettingCategory.AGENT_CONFIG, "sensitive": False},
    "agent_max_turns": {"category": SettingCategory.AGENT_CONFIG, "sensitive": False},
    "agent_max_budget_usd": {"category": SettingCategory.AGENT_CONFIG, "sensitive": False},
    "agent_max_loopbacks": {"category": SettingCategory.AGENT_CONFIG, "sensitive": False},
    # Container Isolation (Epic 25)
    "agent_isolation": {"category": SettingCategory.AGENT_CONFIG, "sensitive": False},
    "agent_isolation_fallback": {"category": SettingCategory.AGENT_CONFIG, "sensitive": False},
    "agent_container_cpu_limit": {"category": SettingCategory.AGENT_CONFIG, "sensitive": False},
    "agent_container_memory_mb": {"category": SettingCategory.AGENT_CONFIG, "sensitive": False},
    "agent_container_timeout_seconds": {"category": SettingCategory.AGENT_CONFIG, "sensitive": False},
    # Preflight (Epic 28)
    "preflight_enabled": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    "preflight_tiers": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    # GitHub Projects v2 (Epic 29)
    "projects_v2_enabled": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    "projects_v2_owner": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    "projects_v2_number": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    "projects_v2_token": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": True},
    # Meridian Portfolio (Epic 29 Sprint 2)
    "meridian_portfolio_enabled": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    "meridian_portfolio_github_issue": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    "meridian_portfolio_repo": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    "meridian_thresholds": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    # Approval auto-bypass (Story 30.14)
    "approval_auto_bypass": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    # Approval Channels (Epic 24)
    "slack_approval_webhook_url": {"category": SettingCategory.INFRASTRUCTURE, "sensitive": True},
    # Cost Optimization (Epic 32)
    "cost_optimization_routing_enabled": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    "cost_optimization_caching_enabled": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    "cost_optimization_batch_enabled": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    "cost_optimization_budget_tiers": {"category": SettingCategory.FEATURE_FLAGS, "sensitive": False},
    # Secrets
    "encryption_key": {"category": SettingCategory.SECRETS, "sensitive": True},
    "webhook_secret": {"category": SettingCategory.SECRETS, "sensitive": True},
}

SENSITIVE_KEYS: frozenset[str] = frozenset(
    k for k, v in SETTING_DEFINITIONS.items() if v["sensitive"]
)

RESTART_REQUIRED_KEYS: frozenset[str] = frozenset({
    "database_url", "temporal_host", "nats_url",
})

# Validation rules for specific settings
VALIDATION_RULES: dict[str, dict[str, Any]] = {
    "database_url": {"type": "url"},
    "nats_url": {"type": "url"},
    "otel_otlp_endpoint": {"type": "url"},
    "temporal_host": {"type": "host_port"},
    "agent_max_turns": {"type": "int", "min": 1, "max": 100},
    "agent_max_budget_usd": {"type": "float", "min": 0.01, "max": 100.0},
    "agent_max_loopbacks": {"type": "int", "min": 0, "max": 10},
    "llm_provider": {"type": "enum", "values": ["mock", "anthropic"]},
    "github_provider": {"type": "enum", "values": ["mock", "real"]},
    "store_backend": {"type": "enum", "values": ["memory", "postgres"]},
}


def mask_value(value: str) -> str:
    """Mask a sensitive value, showing only the last 4 characters."""
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return "*" * (len(value) - 4) + value[-4:]


def validate_setting(key: str, value: str) -> str | None:
    """Validate a setting value. Returns error message or None if valid."""
    rules = VALIDATION_RULES.get(key)
    if not rules:
        return None

    vtype = rules["type"]

    if vtype == "url":
        try:
            parsed = urlparse(value)
            if not parsed.scheme or not parsed.netloc:
                return f"Invalid URL format for {key}"
        except Exception:
            return f"Invalid URL format for {key}"

    elif vtype == "host_port":
        parts = value.split(":")
        if len(parts) != 2 or not parts[1].isdigit():
            return f"Invalid host:port format for {key}"

    elif vtype == "int":
        try:
            v = int(value)
            if "min" in rules and v < rules["min"]:
                return f"{key} must be >= {rules['min']}"
            if "max" in rules and v > rules["max"]:
                return f"{key} must be <= {rules['max']}"
        except ValueError:
            return f"{key} must be an integer"

    elif vtype == "float":
        try:
            v = float(value)
            if "min" in rules and v < rules["min"]:
                return f"{key} must be >= {rules['min']}"
            if "max" in rules and v > rules["max"]:
                return f"{key} must be <= {rules['max']}"
        except ValueError:
            return f"{key} must be a number"

    elif vtype == "enum":
        if value not in rules["values"]:
            return f"{key} must be one of: {', '.join(rules['values'])}"

    return None


class SettingValue:
    """Represents a resolved setting with source info."""

    def __init__(
        self,
        key: str,
        value: str,
        source: str,
        category: SettingCategory,
        sensitive: bool,
        updated_at: Any = None,
        updated_by: str | None = None,
    ) -> None:
        self.key = key
        self.value = value
        self.source = source  # "db" or "env"
        self.category = category
        self.sensitive = sensitive
        self.updated_at = updated_at
        self.updated_by = updated_by

    @property
    def display_value(self) -> str:
        """Return masked value if sensitive, full value otherwise."""
        if self.sensitive:
            return mask_value(self.value)
        return self.value

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.display_value,
            "source": self.source,
            "category": self.category.value,
            "sensitive": self.sensitive,
            "updated_at": str(self.updated_at) if self.updated_at else None,
            "updated_by": self.updated_by,
        }


class SettingsService:
    """Service for managing platform settings with layered config resolution.

    DB overrides take precedence over environment variable defaults.
    Sensitive values are Fernet-encrypted at rest.
    """

    def __init__(self) -> None:
        self._generation: int = 0
        self._reload_subscribers: list[Callable[[str], None]] = []

    @property
    def generation(self) -> int:
        return self._generation

    def subscribe_reload(self, callback: Callable[[str], None]) -> None:
        """Register a callback to be notified when a setting changes."""
        self._reload_subscribers.append(callback)

    def _notify_reload(self, key: str) -> None:
        """Notify subscribers of a setting change."""
        self._generation += 1
        logger.info("Settings reload signal: key=%s generation=%d", key, self._generation)
        for cb in self._reload_subscribers:
            try:
                cb(key)
            except Exception:
                logger.exception("Error in reload subscriber for key=%s", key)

    def _get_env_default(self, key: str) -> str | None:
        """Get the env var default from pydantic settings."""
        if hasattr(env_settings, key):
            val = getattr(env_settings, key)
            return str(val) if val is not None else None
        return None

    async def get(
        self,
        session: AsyncSession,
        key: str,
        *,
        unmask: bool = False,
    ) -> SettingValue | None:
        """Get a setting by key with layered resolution.

        DB override > env var default.
        """
        defn = SETTING_DEFINITIONS.get(key)
        if defn is None:
            return None

        category = defn["category"]
        sensitive = defn["sensitive"]

        # Check DB first
        stmt = select(SettingRow).where(SettingRow.key == key)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is not None:
            value = decrypt_value(row.value) if row.encrypted else row.value
            return SettingValue(
                key=key,
                value=value,
                source="db",
                category=category,
                sensitive=sensitive,
                updated_at=row.updated_at,
                updated_by=row.updated_by,
            )

        # Fall back to env var
        env_val = self._get_env_default(key)
        if env_val is not None:
            return SettingValue(
                key=key,
                value=env_val,
                source="env",
                category=category,
                sensitive=sensitive,
            )

        return None

    async def set(
        self,
        session: AsyncSession,
        key: str,
        value: str,
        updated_by: str,
    ) -> SettingValue:
        """Set a setting value, persisting to DB.

        Encrypts the value if the key is in SENSITIVE_KEYS.
        """
        defn = SETTING_DEFINITIONS.get(key)
        if defn is None:
            msg = f"Unknown setting key: {key}"
            raise ValueError(msg)

        # Validate
        error = validate_setting(key, value)
        if error:
            raise ValueError(error)

        category = defn["category"]
        sensitive = defn["sensitive"]
        store_value = encrypt_value(value) if sensitive else value

        # Upsert
        stmt = select(SettingRow).where(SettingRow.key == key)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is not None:
            row.value = store_value
            row.encrypted = sensitive
            row.updated_by = updated_by
        else:
            row = SettingRow(
                key=key,
                value=store_value,
                encrypted=sensitive,
                category=category,
                updated_by=updated_by,
            )
            session.add(row)

        await session.flush()

        # Notify reload subscribers (for hot-reload)
        self._notify_reload(key)

        return SettingValue(
            key=key,
            value=value,
            source="db",
            category=category,
            sensitive=sensitive,
            updated_at=row.updated_at,
            updated_by=updated_by,
        )

    async def delete(
        self,
        session: AsyncSession,
        key: str,
    ) -> bool:
        """Delete a DB override, reverting to env var default.

        Returns True if a row was deleted, False if nothing to delete.
        """
        stmt = select(SettingRow).where(SettingRow.key == key)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None:
            return False

        await session.delete(row)
        await session.flush()

        self._notify_reload(key)
        return True

    async def list_by_category(
        self,
        session: AsyncSession,
        category: SettingCategory,
    ) -> list[SettingValue]:
        """List all settings in a category with layered resolution."""
        keys = [k for k, v in SETTING_DEFINITIONS.items() if v["category"] == category]

        # Fetch all DB overrides for this category
        stmt = select(SettingRow).where(SettingRow.category == category)
        result = await session.execute(stmt)
        db_rows = {row.key: row for row in result.scalars().all()}

        settings_list: list[SettingValue] = []
        for key in keys:
            defn = SETTING_DEFINITIONS[key]
            sensitive = defn["sensitive"]

            if key in db_rows:
                row = db_rows[key]
                value = decrypt_value(row.value) if row.encrypted else row.value
                settings_list.append(SettingValue(
                    key=key,
                    value=value,
                    source="db",
                    category=category,
                    sensitive=sensitive,
                    updated_at=row.updated_at,
                    updated_by=row.updated_by,
                ))
            else:
                env_val = self._get_env_default(key)
                if env_val is not None:
                    settings_list.append(SettingValue(
                        key=key,
                        value=env_val,
                        source="env",
                        category=category,
                        sensitive=sensitive,
                    ))

        return settings_list

    async def rotate_encryption_key(
        self,
        session: AsyncSession,
        new_key: str,
        updated_by: str,
    ) -> int:
        """Rotate the encryption key, re-encrypting all encrypted settings.

        This is done atomically in a single transaction.
        Returns the number of settings re-encrypted.
        """
        # Fetch all encrypted settings
        stmt = select(SettingRow).where(SettingRow.encrypted.is_(True))
        result = await session.execute(stmt)
        rows = list(result.scalars().all())

        # Decrypt with old key, re-encrypt with new key
        new_fernet = Fernet(new_key.encode() if isinstance(new_key, str) else new_key)

        for row in rows:
            plaintext = decrypt_value(row.value)
            row.value = new_fernet.encrypt(plaintext.encode()).decode()
            row.updated_by = updated_by

        await session.flush()

        logger.info(
            "Encryption key rotated: %d settings re-encrypted by %s",
            len(rows),
            updated_by,
        )
        return len(rows)

    async def regenerate_webhook_secret(
        self,
        session: AsyncSession,
        updated_by: str,
    ) -> str:
        """Generate a new webhook secret and persist it.

        Returns the new plaintext secret (shown once to the user).
        """
        new_secret = secrets.token_urlsafe(32)
        await self.set(session, "webhook_secret", new_secret, updated_by)
        return new_secret


# Singleton
_settings_service: SettingsService | None = None


def get_settings_service() -> SettingsService:
    """Get or create settings service instance."""
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService()
    return _settings_service


def set_settings_service(service: SettingsService | None) -> None:
    """Set settings service (for testing)."""
    global _settings_service
    _settings_service = service
