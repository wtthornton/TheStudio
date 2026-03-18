"""ORM models for persistence tables.

Tables: tool_suites, tool_entries, tool_profiles, model_call_audit, portfolio_reviews
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class ToolSuiteRow(Base):
    """Persistence row for a tool suite registration."""

    __tablename__ = "tool_suites"

    name: Mapped[str] = mapped_column(String(255), primary_key=True)
    description: Mapped[str] = mapped_column(Text, default="")
    approval_status: Mapped[str] = mapped_column(String(20), default="observe")
    version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ToolEntryRow(Base):
    """Persistence row for a single tool within a suite."""

    __tablename__ = "tool_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    suite_name: Mapped[str] = mapped_column(
        String(255), ForeignKey("tool_suites.name", ondelete="CASCADE"),
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    capability: Mapped[str] = mapped_column(String(50))
    read_only: Mapped[bool] = mapped_column(Boolean, default=True)


class ToolProfileRow(Base):
    """Persistence row for a repo-to-suite mapping profile."""

    __tablename__ = "tool_profiles"

    profile_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    repo_id: Mapped[str] = mapped_column(String(255))
    enabled_suites: Mapped[list] = mapped_column(JSON, default=list)
    tier_scope: Mapped[str] = mapped_column(String(20), default="observe")


class ModelCallAuditRow(Base):
    """Persistence row for a model call audit record."""

    __tablename__ = "model_call_audit"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    correlation_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    task_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    step: Mapped[str] = mapped_column(String(100), default="")
    role: Mapped[str] = mapped_column(String(100), default="")
    overlays: Mapped[list] = mapped_column(JSON, default=list)
    provider: Mapped[str] = mapped_column(String(100), default="")
    model: Mapped[str] = mapped_column(String(100), default="")
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    error_class: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fallback_chain: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PortfolioReviewRow(Base):
    """Persistence row for Meridian portfolio health reviews (Epic 29 AC 15)."""

    __tablename__ = "portfolio_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    overall_health: Mapped[str] = mapped_column(String(20))
    flags: Mapped[list] = mapped_column(JSON, default=list)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    recommendations: Mapped[list] = mapped_column(JSON, default=list)
