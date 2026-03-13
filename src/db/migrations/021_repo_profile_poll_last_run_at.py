"""Migration 021: Add poll_last_run_at column to repo_profile.

Tracks when each repo was last polled, enabling per-repo interval enforcement.
The scheduler skips repos whose poll_last_run_at + poll_interval_minutes > now.

Run with: python -m src.db.migrations.021_repo_profile_poll_last_run_at
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    """
    ALTER TABLE repo_profile
    ADD COLUMN IF NOT EXISTS poll_last_run_at TIMESTAMPTZ DEFAULT NULL
    """,
]

SQL_DOWN = [
    """
    ALTER TABLE repo_profile
    DROP COLUMN IF EXISTS poll_last_run_at
    """,
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
