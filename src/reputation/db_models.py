"""SQLAlchemy ORM model for expert reputation persistence."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class ExpertReputationRow(Base):
    """ORM model mapped to expert_reputation table."""

    __tablename__ = "expert_reputation"

    expert_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    context_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    expert_version: Mapped[int] = mapped_column(Integer, default=1)
    weight: Mapped[float] = mapped_column(Float, default=0.5)
    raw_weight_sum: Mapped[float] = mapped_column(Float, default=0.0)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.1)
    trust_tier: Mapped[str] = mapped_column(
        Enum(
            "shadow",
            "probation",
            "trusted",
            name="trust_tier",
            create_type=False,
        ),
        default="shadow",
    )
    tier_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Column alias: code uses last_indicator_at, DB column is last_outcome_at
    last_indicator_at: Mapped[datetime | None] = mapped_column(
        "last_outcome_at", DateTime(timezone=True), nullable=True
    )
    # Column alias: code uses drift_signal, DB column is drift_direction
    drift_signal: Mapped[str] = mapped_column(
        "drift_direction",
        Enum(
            "improving",
            "stable",
            "declining",
            name="drift_direction",
            create_type=False,
        ),
        default="stable",
    )
    drift_score: Mapped[float] = mapped_column(Float, default=0.0)
    weight_history: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
