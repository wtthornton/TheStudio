"""Migration 033: Add PAUSED and ABORTED values to taskpacket_status enum.

Supports Epic 37 Slice 1 — Pipeline Steering (Pause/Resume/Abort).
PAUSED: pipeline held between activities; resumes on resume_task signal.
ABORTED: forcefully terminated by operator; terminal state.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

# PostgreSQL requires ALTER TYPE ... ADD VALUE for enum additions.
# IF NOT EXISTS guard prevents failure if migration is re-run.
SQL_UP = [
    "ALTER TYPE taskpacket_status ADD VALUE IF NOT EXISTS 'paused'",
    "ALTER TYPE taskpacket_status ADD VALUE IF NOT EXISTS 'aborted'",
]

# PostgreSQL does not support removing enum values without full type recreation.
# Downgrade marks this migration as non-reversible (no-op with a warning).
SQL_DOWN: list[str] = []


async def upgrade() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL_UP:
            await conn.execute(text(stmt))
    await engine.dispose()


async def downgrade() -> None:
    # PostgreSQL cannot remove values from an existing enum type without
    # recreating the type. Downgrade is intentionally a no-op; remove rows
    # with PAUSED/ABORTED manually before attempting a full type recreation.
    pass


if __name__ == "__main__":
    asyncio.run(upgrade())
    print("Migration 033 applied.")
