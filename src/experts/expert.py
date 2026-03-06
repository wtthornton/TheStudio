"""Expert model — the registry record for domain experts.

Architecture reference: thestudioarc/10-expert-library.md
Experts are persisted with identity, versioning, class, capability tags,
scope, tool policy, trust tier, and lifecycle state.
"""

import enum
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Enum, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class ExpertClass(enum.StrEnum):
    """Expert class taxonomy (thestudioarc/02-expert-taxonomy.md)."""

    TECHNICAL = "technical"
    BUSINESS = "business"
    PARTNER = "partner"
    QA_VALIDATION = "qa_validation"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    SERVICE = "service"
    PROCESS_QUALITY = "process_quality"


class TrustTier(enum.StrEnum):
    """Trust tier for experts. New experts start in shadow or probation."""

    SHADOW = "shadow"
    PROBATION = "probation"
    TRUSTED = "trusted"


class LifecycleState(enum.StrEnum):
    """Expert lifecycle state."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


# Trust tier ordering for search ranking (higher = better)
TRUST_TIER_ORDER = {TrustTier.TRUSTED: 3, TrustTier.PROBATION: 2, TrustTier.SHADOW: 1}


class ExpertRow(Base):
    """SQLAlchemy ORM model for the experts table."""

    __tablename__ = "experts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expert_class: Mapped[ExpertClass] = mapped_column(
        Enum(ExpertClass, name="expert_class", create_constraint=True),
        nullable=False,
    )
    capability_tags: Mapped[list[str]] = mapped_column(
        ARRAY(String(100)), nullable=False
    )
    scope_description: Mapped[str] = mapped_column(String(2000), nullable=False)
    tool_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    trust_tier: Mapped[TrustTier] = mapped_column(
        Enum(TrustTier, name="trust_tier", create_constraint=True),
        nullable=False,
        default=TrustTier.SHADOW,
    )
    lifecycle_state: Mapped[LifecycleState] = mapped_column(
        Enum(LifecycleState, name="lifecycle_state", create_constraint=True),
        nullable=False,
        default=LifecycleState.ACTIVE,
    )
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = ({"comment": "Expert Library — registry of domain experts"},)


class ExpertVersionRow(Base):
    """SQLAlchemy ORM model for the expert_versions table."""

    __tablename__ = "expert_versions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    expert_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    definition: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = ({"comment": "Expert version history"},)


class ExpertCreate(BaseModel):
    """Input for creating an expert."""

    name: str
    expert_class: ExpertClass
    capability_tags: list[str]
    scope_description: str
    tool_policy: dict[str, Any] = Field(default_factory=dict)
    trust_tier: TrustTier = TrustTier.SHADOW
    definition: dict[str, Any] = Field(default_factory=dict)


class ExpertRead(BaseModel):
    """Output for reading an expert."""

    model_config = {"from_attributes": True}

    id: UUID
    name: str
    expert_class: ExpertClass
    capability_tags: list[str]
    scope_description: str
    tool_policy: dict[str, Any]
    trust_tier: TrustTier
    lifecycle_state: LifecycleState
    current_version: int
    created_at: datetime
    updated_at: datetime


class ExpertVersionRead(BaseModel):
    """Output for reading an expert version."""

    model_config = {"from_attributes": True}

    id: UUID
    expert_id: UUID
    version: int
    definition: dict[str, Any]
    created_at: datetime
