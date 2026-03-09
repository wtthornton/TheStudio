"""PostgreSQL-backed Settings persistence.

Story 12.1: Settings Data Model & Encrypted Storage.
Provides the SettingRow ORM model for key-value settings storage
with Fernet encryption for sensitive values.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class SettingCategory(StrEnum):
    """Categories for grouping settings in the UI."""

    API_KEYS = "api_keys"
    INFRASTRUCTURE = "infrastructure"
    FEATURE_FLAGS = "feature_flags"
    AGENT_CONFIG = "agent_config"
    SECRETS = "secrets"


class SettingRow(Base):
    """SQLAlchemy ORM model for the settings table."""

    __tablename__ = "settings"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    key: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    category: Mapped[SettingCategory] = mapped_column(
        Enum(SettingCategory, name="setting_category", create_constraint=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = ({"comment": "Platform settings with encrypted sensitive values"},)
