"""Migration 020: Add merge_method column to repo_profile.

Stores the preferred merge method (squash, merge, rebase) per repository.
Defaults to 'squash'. Required for Execute tier auto-merge (Epic 22).

Run with: python -m src.db.migrations.020_repo_profile_merge_method
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    """
    ALTER TABLE repo_profile
    ADD COLUMN IF NOT EXISTS merge_method VARCHAR(20) NOT NULL DEFAULT 'squash'
    """,
]

SQL_DOWN = [
    """
    ALTER TABLE repo_profile
    DROP COLUMN IF EXISTS merge_method
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
