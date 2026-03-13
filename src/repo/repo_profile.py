"""Repo Profile model — configuration record for a registered repository.

Defines tier, required checks, tool allowlist, webhook secret, and status.
Read by Ingress, Verification Gate, Primary Agent, and Publisher.
"""

import enum
from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class RepoTier(enum.StrEnum):
    """Enumeration of repository maturity tiers."""

    OBSERVE = "observe"
    SUGGEST = "suggest"
    EXECUTE = "execute"


class RepoStatus(enum.StrEnum):
    """Enumeration of repository lifecycle states."""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class RepoProfileRow(Base):
    """SQLAlchemy ORM model for the repo_profile table."""

    __tablename__ = "repo_profile"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_name: Mapped[str] = mapped_column(String(255), nullable=False)
    installation_id: Mapped[int] = mapped_column(nullable=False)
    default_branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main")
    tier: Mapped[RepoTier] = mapped_column(
        Enum(
            RepoTier,
            name="repo_tier",
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=RepoTier.OBSERVE,
    )
    required_checks: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    tool_allowlist: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    webhook_secret_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[RepoStatus] = mapped_column(
        Enum(
            RepoStatus,
            name="repo_status",
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=RepoStatus.ACTIVE,
    )
    writes_enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    poll_enabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    poll_interval_minutes: Mapped[int | None] = mapped_column(nullable=True, default=None)
    merge_method: Mapped[str] = mapped_column(
        String(20), nullable=False, default="squash",
        comment="Preferred merge method: squash, merge, or rebase",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    __table_args__ = (
        {"comment": "Repo Profile — configuration record for a registered repository"},
    )

    @property
    def full_name(self) -> str:
        """Return owner/repo_name format."""
        return f"{self.owner}/{self.repo_name}"

    @property
    def is_deleted(self) -> bool:
        """Check if repo is soft-deleted."""
        return self.deleted_at is not None


class RepoProfileCreate(BaseModel):
    """Input for registering a repo."""

    owner: str
    repo_name: str
    installation_id: int
    webhook_secret: str
    default_branch: str = "main"
    tier: RepoTier = RepoTier.OBSERVE
    required_checks: list[str] = Field(default_factory=lambda: ["ruff", "pytest"])
    tool_allowlist: list[str] = Field(default_factory=list)
    merge_method: str = "squash"


class RepoProfileRead(BaseModel):
    """Output for reading a repo profile (secret excluded)."""

    model_config = {"from_attributes": True}

    id: UUID
    owner: str
    repo_name: str
    installation_id: int
    default_branch: str
    tier: RepoTier
    required_checks: list[str]
    tool_allowlist: list[str]
    status: RepoStatus
    writes_enabled: bool
    poll_enabled: bool = False
    poll_interval_minutes: int | None = None
    merge_method: str = "squash"
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @property
    def full_name(self) -> str:
        """Return owner/repo_name format."""
        return f"{self.owner}/{self.repo_name}"


class RepoProfileUpdate(BaseModel):
    """Input for updating a repo profile."""

    default_branch: str | None = None
    required_checks: list[str] | None = None
    tool_allowlist: list[str] | None = None
    poll_enabled: bool | None = None
    poll_interval_minutes: int | None = None
    merge_method: str | None = None
