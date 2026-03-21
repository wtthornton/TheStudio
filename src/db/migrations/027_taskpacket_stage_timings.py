"""Migration 027: Add stage_timings JSONB column to taskpacket.

Stores per-stage start/end timestamps for the 9 pipeline stages.
Nullable for historical records that predate this migration.

Schema: {
    "intake": {"start": "2026-03-21T10:00:00Z", "end": "2026-03-21T10:00:05Z"},
    "context": {"start": "...", "end": "..."},
    ...
}

Run with: python -m src.db.migrations.027_taskpacket_stage_timings
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    """
    ALTER TABLE taskpacket
    ADD COLUMN IF NOT EXISTS stage_timings JSONB DEFAULT NULL
    """,
]

SQL_DOWN = [
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS stage_timings",
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
    print("Migration 027 applied.")
