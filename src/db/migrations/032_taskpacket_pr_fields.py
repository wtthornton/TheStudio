"""Migration 032: Add pr_number and pr_url columns to taskpacket.

Stores the GitHub PR number and URL after the Publisher creates a draft PR,
so the dashboard can link directly to published PRs.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    "ALTER TABLE taskpacket ADD COLUMN IF NOT EXISTS pr_number INTEGER DEFAULT NULL",
    "ALTER TABLE taskpacket ADD COLUMN IF NOT EXISTS pr_url VARCHAR(500) DEFAULT NULL",
]

SQL_DOWN = [
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS pr_url",
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS pr_number",
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
    print("Migration 032 applied.")
