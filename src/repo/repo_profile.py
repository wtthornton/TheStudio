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
    OBSERVE = "observe"
    SUGGEST = "suggest"
    EXECUTE = "execute"


class RepoStatus(enum.StrEnum):
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
    tier: Mapped[RepoTier] = mapped_column(
        Enum(RepoTier, name="repo_tier", create_constraint=True),
        nullable=False,
        default=RepoTier.OBSERVE,
    )
    required_checks: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    tool_allowlist: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    webhook_secret_encrypted: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[RepoStatus] = mapped_column(
        Enum(RepoStatus, name="repo_status", create_constraint=True),
        nullable=False,
        default=RepoStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        {"comment": "Repo Profile — configuration record for a registered repository"},
    )


class RepoProfileCreate(BaseModel):
    """Input for registering a repo."""

    owner: str
    repo_name: str
    installation_id: int
    webhook_secret: str
    tier: RepoTier = RepoTier.OBSERVE
    required_checks: list[str] = Field(default_factory=list)
    tool_allowlist: list[str] = Field(default_factory=list)


class RepoProfileRead(BaseModel):
    """Output for reading a repo profile (secret excluded)."""

    model_config = {"from_attributes": True}

    id: UUID
    owner: str
    repo_name: str
    installation_id: int
    tier: RepoTier
    required_checks: list[str]
    tool_allowlist: list[str]
    status: RepoStatus
    created_at: datetime
    updated_at: datetime
