"""Migration 022: Add source_name column to taskpacket.

Tracks which intake source created the TaskPacket (Epic 27 — multi-source
webhooks). Defaults to 'github' for all existing rows. Indexed for
dashboard filtering by source.

Run with: python -m src.db.migrations.022_taskpacket_source_name
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    """
    ALTER TABLE taskpacket
    ADD COLUMN IF NOT EXISTS source_name VARCHAR(100) NOT NULL DEFAULT 'github'
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_taskpacket_source_name
    ON taskpacket (source_name)
    """,
]

SQL_DOWN = [
    """
    DROP INDEX IF EXISTS ix_taskpacket_source_name
    """,
    """
    ALTER TABLE taskpacket
    DROP COLUMN IF EXISTS source_name
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
