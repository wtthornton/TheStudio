"""PostgreSQL-backed Model Audit Store implementation.

Story 8.8: PostgreSQL Implementations — 3 Critical Stores
Implements ModelAuditStoreProtocol using SQLAlchemy async sessions.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.model_gateway import ModelCallAudit
from src.db.models import ModelCallAuditRow


class PostgresModelAuditStore:
    """PostgreSQL-backed model call audit store."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(self, audit: ModelCallAudit) -> None:
        row = ModelCallAuditRow(
            id=audit.id,
            correlation_id=audit.correlation_id,
            task_id=audit.task_id,
            step=audit.step,
            role=audit.role,
            overlays=audit.overlays,
            provider=audit.provider,
            model=audit.model,
            tokens_in=audit.tokens_in,
            tokens_out=audit.tokens_out,
            cost=audit.cost,
            latency_ms=audit.latency_ms,
            error_class=audit.error_class,
            fallback_chain=audit.fallback_chain,
            created_at=audit.created_at,
        )
        self._session.add(row)
        await self._session.flush()

    async def query(
        self,
        task_id: str | None = None,
        step: str | None = None,
        provider: str | None = None,
        limit: int = 100,
    ) -> list[ModelCallAudit]:
        stmt = select(ModelCallAuditRow)

        if task_id:
            stmt = stmt.where(ModelCallAuditRow.task_id == UUID(task_id))
        if step:
            stmt = stmt.where(ModelCallAuditRow.step == step)
        if provider:
            stmt = stmt.where(ModelCallAuditRow.provider == provider)

        stmt = stmt.order_by(ModelCallAuditRow.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        return [
            ModelCallAudit(
                id=r.id,
                correlation_id=r.correlation_id,
                task_id=r.task_id,
                step=r.step,
                role=r.role,
                overlays=r.overlays,
                provider=r.provider,
                model=r.model,
                tokens_in=r.tokens_in,
                tokens_out=r.tokens_out,
                cost=r.cost,
                latency_ms=r.latency_ms,
                error_class=r.error_class,
                fallback_chain=r.fallback_chain,
                created_at=r.created_at,
            )
            for r in rows
        ]

    async def clear(self) -> None:
        await self._session.execute(delete(ModelCallAuditRow))
        await self._session.flush()
