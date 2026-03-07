"""PostgreSQL-backed Tool Catalog implementation.

Story 8.8: PostgreSQL Implementations — 3 Critical Stores
Implements ToolCatalogProtocol using SQLAlchemy async sessions.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.tool_catalog import (
    ApprovalStatus,
    CapabilityCategory,
    InvalidPromotionError,
    SuiteDuplicateError,
    SuiteNotFoundError,
    ToolEntry,
    ToolSuite,
    _PROMOTION_ORDER,
)
from src.db.models import ToolEntryRow, ToolSuiteRow


class PostgresToolCatalog:
    """PostgreSQL-backed tool catalog.

    Each method receives an AsyncSession to participate in the caller's
    transaction. For use with FastAPI's Depends(get_session).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register(self, suite: ToolSuite) -> None:
        existing = await self._session.get(ToolSuiteRow, suite.name)
        if existing is not None:
            raise SuiteDuplicateError(suite.name)

        row = ToolSuiteRow(
            name=suite.name,
            description=suite.description,
            approval_status=suite.approval_status.value,
            version=suite.version,
            created_at=suite.created_at,
        )
        self._session.add(row)
        await self._session.flush()

        for tool in suite.tools:
            entry_row = ToolEntryRow(
                suite_name=suite.name,
                name=tool.name,
                description=tool.description,
                capability=tool.capability.value,
                read_only=tool.read_only,
            )
            self._session.add(entry_row)

        await self._session.flush()

    async def get_suite(self, name: str) -> ToolSuite:
        row = await self._session.get(ToolSuiteRow, name)
        if row is None:
            raise SuiteNotFoundError(name)
        return await self._row_to_suite(row)

    async def list_suites(self) -> list[ToolSuite]:
        result = await self._session.execute(select(ToolSuiteRow))
        rows = result.scalars().all()
        return [await self._row_to_suite(r) for r in rows]

    async def promote_suite(self, name: str) -> ToolSuite:
        row = await self._session.get(ToolSuiteRow, name)
        if row is None:
            raise SuiteNotFoundError(name)

        current = ApprovalStatus(row.approval_status)
        idx = _PROMOTION_ORDER.index(current)
        if idx >= len(_PROMOTION_ORDER) - 1:
            raise InvalidPromotionError(name, current, current)

        new_status = _PROMOTION_ORDER[idx + 1]
        row.approval_status = new_status.value
        await self._session.flush()
        return await self._row_to_suite(row)

    async def get_suites_for_tier(self, tier: str) -> list[ToolSuite]:
        # All tiers currently return all suites (matches in-memory behavior)
        return await self.list_suites()

    async def clear(self) -> None:
        await self._session.execute(delete(ToolEntryRow))
        await self._session.execute(delete(ToolSuiteRow))
        await self._session.flush()

    async def _row_to_suite(self, row: ToolSuiteRow) -> ToolSuite:
        result = await self._session.execute(
            select(ToolEntryRow).where(ToolEntryRow.suite_name == row.name)
        )
        entry_rows = result.scalars().all()

        tools = [
            ToolEntry(
                name=e.name,
                description=e.description,
                capability=CapabilityCategory(e.capability),
                read_only=e.read_only,
            )
            for e in entry_rows
        ]

        return ToolSuite(
            name=row.name,
            description=row.description,
            tools=tools,
            approval_status=ApprovalStatus(row.approval_status),
            version=row.version,
            created_at=row.created_at,
        )
