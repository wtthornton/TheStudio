"""Audit Log for Admin API.

Story 4.9: Audit Log — Schema, Logging, Query API.
Architecture reference: thestudioarc/23-admin-control-ui.md

Provides:
- Audit event type enumeration
- Audit log database model
- Audit service for logging and querying
- Query filters for audit log endpoint
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AuditEventType(StrEnum):
    """Types of auditable admin events.

    All admin actions from Stories 4.4-4.8 are logged.
    """

    # Repo management events (Stories 4.4-4.5)
    REPO_REGISTERED = "repo_registered"
    REPO_PROFILE_UPDATED = "repo_profile_updated"
    REPO_TIER_CHANGED = "repo_tier_changed"
    REPO_PAUSED = "repo_paused"
    REPO_RESUMED = "repo_resumed"
    REPO_WRITES_TOGGLED = "repo_writes_toggled"

    # Workflow console events (Story 4.7)
    WORKFLOW_VERIFICATION_RERUN = "workflow_verification_rerun"
    WORKFLOW_SENT_TO_AGENT = "workflow_sent_to_agent"
    WORKFLOW_ESCALATED = "workflow_escalated"


class AuditLogRow(Base):
    """SQLAlchemy ORM model for the audit_log table.

    Records all admin actions with timestamp, actor, event type,
    target identifier, and detailed event data.
    """

    __tablename__ = "audit_log"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    actor: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[AuditEventType] = mapped_column(
        Enum(AuditEventType, name="audit_event_type", create_constraint=True),
        nullable=False,
        index=True,
    )
    target_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = ({"comment": "Audit log for admin actions"},)


class AuditLogCreate(BaseModel):
    """Input for creating an audit log entry."""

    actor: str = Field(..., min_length=1, max_length=255)
    event_type: AuditEventType
    target_id: str = Field(..., min_length=1, max_length=255)
    details: dict[str, Any] = Field(default_factory=dict)


class AuditLogRead(BaseModel):
    """Output for reading an audit log entry."""

    model_config = {"from_attributes": True}

    id: UUID
    timestamp: datetime
    actor: str
    event_type: AuditEventType
    target_id: str
    details: dict[str, Any]


class AuditLogFilter(BaseModel):
    """Filters for querying audit log entries."""

    event_type: AuditEventType | None = None
    actor: str | None = None
    target_id: str | None = None
    hours: int | None = Field(default=None, ge=1, le=720)
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class AuditLogListResult(BaseModel):
    """Result from listing audit log entries."""

    entries: list[AuditLogRead]
    total: int
    filtered_by: dict[str, Any]


class AuditService:
    """Service for audit log operations.

    Usage:
        service = AuditService()
        await service.log_event(session, actor="admin@example.com", ...)
        entries = await service.query(session, filters)
    """

    async def log_event(
        self,
        session: AsyncSession,
        actor: str,
        event_type: AuditEventType,
        target_id: str,
        details: dict[str, Any] | None = None,
    ) -> AuditLogRow:
        """Log an audit event.

        Args:
            session: Database session.
            actor: User who performed the action.
            event_type: Type of audit event.
            target_id: Identifier of the affected resource.
            details: Additional event details as JSON.

        Returns:
            Created AuditLogRow.
        """
        row = AuditLogRow(
            actor=actor,
            event_type=event_type,
            target_id=str(target_id),
            details=details or {},
        )
        session.add(row)
        await session.flush()

        logger.info(
            "AUDIT: %s actor=%s target=%s details=%s",
            event_type.value,
            actor,
            target_id,
            details,
        )

        return row

    async def log_repo_event(
        self,
        session: AsyncSession,
        event_type: AuditEventType,
        repo_id: UUID,
        actor: str,
        details: dict[str, Any] | None = None,
    ) -> AuditLogRow:
        """Log a repository-related audit event.

        Args:
            session: Database session.
            event_type: Type of audit event.
            repo_id: Repository UUID.
            actor: User who performed the action.
            details: Additional event details.

        Returns:
            Created AuditLogRow.
        """
        return await self.log_event(
            session=session,
            actor=actor,
            event_type=event_type,
            target_id=str(repo_id),
            details=details,
        )

    async def log_workflow_event(
        self,
        session: AsyncSession,
        event_type: AuditEventType,
        workflow_id: str,
        actor: str,
        details: dict[str, Any] | None = None,
    ) -> AuditLogRow:
        """Log a workflow-related audit event.

        Args:
            session: Database session.
            event_type: Type of audit event.
            workflow_id: Temporal workflow ID.
            actor: User who performed the action.
            details: Additional event details.

        Returns:
            Created AuditLogRow.
        """
        return await self.log_event(
            session=session,
            actor=actor,
            event_type=event_type,
            target_id=workflow_id,
            details=details,
        )

    async def query(
        self,
        session: AsyncSession,
        filters: AuditLogFilter | None = None,
    ) -> AuditLogListResult:
        """Query audit log entries with filters.

        Args:
            session: Database session.
            filters: Optional filters for event_type, actor, target_id, hours.

        Returns:
            AuditLogListResult with matching entries and total count.
        """
        if filters is None:
            filters = AuditLogFilter()

        stmt = select(AuditLogRow)

        if filters.event_type is not None:
            stmt = stmt.where(AuditLogRow.event_type == filters.event_type)

        if filters.actor is not None:
            stmt = stmt.where(AuditLogRow.actor == filters.actor)

        if filters.target_id is not None:
            stmt = stmt.where(AuditLogRow.target_id == filters.target_id)

        if filters.hours is not None:
            cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=filters.hours)
            stmt = stmt.where(AuditLogRow.timestamp >= cutoff)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await session.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.order_by(AuditLogRow.timestamp.desc())
        stmt = stmt.offset(filters.offset).limit(filters.limit)

        result = await session.execute(stmt)
        rows = list(result.scalars().all())

        filtered_by: dict[str, Any] = {}
        if filters.event_type is not None:
            filtered_by["event_type"] = filters.event_type.value
        if filters.actor is not None:
            filtered_by["actor"] = filters.actor
        if filters.target_id is not None:
            filtered_by["target_id"] = filters.target_id
        if filters.hours is not None:
            filtered_by["hours"] = filters.hours

        return AuditLogListResult(
            entries=[
                AuditLogRead(
                    id=row.id,
                    timestamp=row.timestamp,
                    actor=row.actor,
                    event_type=row.event_type,
                    target_id=row.target_id,
                    details=row.details,
                )
                for row in rows
            ],
            total=total,
            filtered_by=filtered_by,
        )

    async def get_by_id(
        self,
        session: AsyncSession,
        audit_id: UUID,
    ) -> AuditLogRow | None:
        """Get a single audit log entry by ID.

        Args:
            session: Database session.
            audit_id: Audit log entry UUID.

        Returns:
            AuditLogRow if found, None otherwise.
        """
        stmt = select(AuditLogRow).where(AuditLogRow.id == audit_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


_audit_service: AuditService | None = None


def get_audit_service() -> AuditService:
    """Get or create audit service instance."""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service


def set_audit_service(service: AuditService | None) -> None:
    """Set audit service (for testing)."""
    global _audit_service
    _audit_service = service
