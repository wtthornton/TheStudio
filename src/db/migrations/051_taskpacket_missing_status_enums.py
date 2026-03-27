"""Migration 051: Add missing values to taskpacket_status enum.

The Python StrEnum gained triage, clarification_requested,
human_review_required, awaiting_approval, and awaiting_approval_expired
values but no migration added them to the PostgreSQL enum type.
This causes 500 errors when filtering tasks by these statuses.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    "ALTER TYPE taskpacket_status ADD VALUE IF NOT EXISTS 'triage'",
    "ALTER TYPE taskpacket_status ADD VALUE IF NOT EXISTS 'clarification_requested'",
    "ALTER TYPE taskpacket_status ADD VALUE IF NOT EXISTS 'human_review_required'",
    "ALTER TYPE taskpacket_status ADD VALUE IF NOT EXISTS 'awaiting_approval'",
    "ALTER TYPE taskpacket_status ADD VALUE IF NOT EXISTS 'awaiting_approval_expired'",
]

SQL_DOWN: list[str] = []


async def upgrade() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL_UP:
            await conn.execute(text(stmt))
    await engine.dispose()


async def downgrade() -> None:
    pass


if __name__ == "__main__":
    asyncio.run(upgrade())
    print("Migration 051 applied.")
