"""Migration 003: Add enrichment, intent, and loopback fields to taskpacket.

Run with: python -m src.db.migrations.003_taskpacket_enrichment
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    "ALTER TABLE taskpacket ADD COLUMN scope JSONB",
    "ALTER TABLE taskpacket ADD COLUMN risk_flags JSONB",
    "ALTER TABLE taskpacket ADD COLUMN complexity_index VARCHAR(20)",
    "ALTER TABLE taskpacket ADD COLUMN context_packs JSONB",
    "ALTER TABLE taskpacket ADD COLUMN intent_spec_id UUID",
    "ALTER TABLE taskpacket ADD COLUMN intent_version INTEGER",
    "ALTER TABLE taskpacket ADD COLUMN loopback_count INTEGER NOT NULL DEFAULT 0",
]

SQL_DOWN = [
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS scope",
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS risk_flags",
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS complexity_index",
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS context_packs",
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS intent_spec_id",
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS intent_version",
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS loopback_count",
]


async def migrate_up() -> None:
    """Apply migration 003."""
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL_UP:
            await conn.execute(text(stmt))
    await engine.dispose()


async def migrate_down() -> None:
    """Reverse migration 003."""
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL_DOWN:
            await conn.execute(text(stmt))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate_up())
    print("Migration 003_taskpacket_enrichment applied.")
