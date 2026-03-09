"""Migration 001: Create taskpacket table.

Run with: python -m src.db.migrations.001_taskpacket
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    """CREATE TYPE taskpacket_status AS ENUM (
    'received', 'enriched', 'intent_built', 'in_progress',
    'verification_passed', 'verification_failed', 'published', 'failed'
)""",
    """CREATE TABLE taskpacket (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo VARCHAR(255) NOT NULL,
    issue_id INTEGER NOT NULL,
    delivery_id VARCHAR(255) NOT NULL,
    correlation_id UUID NOT NULL,
    status taskpacket_status NOT NULL DEFAULT 'received',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
    "CREATE UNIQUE INDEX ix_taskpacket_delivery_repo ON taskpacket (delivery_id, repo)",
    "CREATE INDEX ix_taskpacket_correlation_id ON taskpacket (correlation_id)",
    "CREATE INDEX ix_taskpacket_status ON taskpacket (status)",
    "COMMENT ON TABLE taskpacket IS 'TaskPacket — durable work record'",
]

SQL_DOWN = [
    "DROP TABLE IF EXISTS taskpacket",
    "DROP TYPE IF EXISTS taskpacket_status",
]


async def migrate_up() -> None:
    """Apply migration 001."""
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL_UP:
            await conn.execute(text(stmt))
    await engine.dispose()


async def migrate_down() -> None:
    """Reverse migration 001."""
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL_DOWN:
            await conn.execute(text(stmt))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate_up())
    print("Migration 001_taskpacket applied.")
