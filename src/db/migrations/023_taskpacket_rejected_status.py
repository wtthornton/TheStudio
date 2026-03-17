"""Migration 023: Add 'rejected' value to taskpacket_status enum.

Enables the AWAITING_APPROVAL -> REJECTED transition for the rejection
flow (Epic 24 blocker fix).

Run with: python -m src.db.migrations.023_taskpacket_rejected_status
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    """
    ALTER TYPE taskpacket_status ADD VALUE IF NOT EXISTS 'rejected'
    """,
]

SQL_DOWN = [
    # PostgreSQL does not support removing enum values directly.
    # To reverse, you'd recreate the type. This is intentionally a no-op
    # because dropping an enum value requires recreating the column.
]


async def upgrade() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL_UP:
            await conn.execute(text(stmt))
    await engine.dispose()


async def downgrade() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL_DOWN:
            await conn.execute(text(stmt))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(upgrade())
