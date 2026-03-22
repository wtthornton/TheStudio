"""OutcomeSignalRow — SQLAlchemy model and CRUD for persisted outcome signals.

Replaces the in-memory `_signals` list in ingestor.py with PostgreSQL persistence.
The in-memory list is preserved as a cache layer for test isolation and legacy API
compatibility.

Epic 39 Story 39.0c.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.outcome.models import OutcomeSignal, SignalEvent


class OutcomeSignalRow(Base):
    """Persistence row for a consumed and validated outcome signal.

    Stores the signal type, associated task, and raw payload for analytics
    and audit queries (Epic 39 Slice 2: Outcome Signals Feed).
    """

    __tablename__ = "outcome_signals"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    # The task this signal is associated with (may be NULL for quarantined signals)
    task_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    # The correlation_id from the originating event
    correlation_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    # Signal event type (e.g. "verification_passed", "qa_defect")
    signal_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # Full raw payload from the JetStream message
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    # Timestamp of the original signal event
    signal_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # When this row was persisted
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_outcome_signals_task_id", "task_id"),
        Index("ix_outcome_signals_created_at", "created_at"),
        Index("ix_outcome_signals_signal_type", "signal_type"),
        {"comment": "OutcomeSignalRow — persisted outcome signals for analytics"},
    )


async def save_signal(session: AsyncSession, signal: OutcomeSignal) -> OutcomeSignalRow:
    """Persist an OutcomeSignal to the database.

    Args:
        session: Active async SQLAlchemy session.
        signal: Validated OutcomeSignal to persist.

    Returns:
        The persisted OutcomeSignalRow.
    """
    row = OutcomeSignalRow(
        id=uuid4(),
        task_id=signal.taskpacket_id,
        correlation_id=signal.correlation_id,
        signal_type=signal.event.value,
        payload=signal.payload,
        signal_at=signal.timestamp,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def list_signals(
    session: AsyncSession,
    task_id: UUID | None = None,
    signal_type: SignalEvent | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[OutcomeSignalRow]:
    """Query persisted outcome signals with optional filters.

    Args:
        session: Active async SQLAlchemy session.
        task_id: Filter by task ID (optional).
        signal_type: Filter by signal event type (optional).
        limit: Maximum rows to return (default 100).
        offset: Row offset for pagination (default 0).

    Returns:
        List of matching OutcomeSignalRow records ordered by created_at DESC.
    """
    stmt = select(OutcomeSignalRow).order_by(OutcomeSignalRow.created_at.desc())

    if task_id is not None:
        stmt = stmt.where(OutcomeSignalRow.task_id == task_id)
    if signal_type is not None:
        stmt = stmt.where(OutcomeSignalRow.signal_type == signal_type.value)

    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


def signal_row_to_outcome_signal(row: OutcomeSignalRow) -> OutcomeSignal:
    """Convert an OutcomeSignalRow back to an OutcomeSignal Pydantic model."""
    return OutcomeSignal(
        event=SignalEvent(row.signal_type),
        taskpacket_id=row.task_id or UUID(int=0),
        correlation_id=row.correlation_id or UUID(int=0),
        timestamp=row.signal_at,
        payload=row.payload,
    )
