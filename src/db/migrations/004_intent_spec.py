"""Migration 004: Create intent_spec table.

Run with: python -m src.db.migrations.004_intent_spec
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    """CREATE TABLE intent_spec (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    taskpacket_id UUID NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    goal VARCHAR(2000) NOT NULL,
    constraints JSONB NOT NULL DEFAULT '[]'::jsonb,
    acceptance_criteria JSONB NOT NULL DEFAULT '[]'::jsonb,
    non_goals JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
    "CREATE INDEX ix_intent_spec_taskpacket_id ON intent_spec (taskpacket_id)",
    "CREATE INDEX ix_intent_spec_tp_version ON intent_spec (taskpacket_id, version)",
    "COMMENT ON TABLE intent_spec IS 'Intent Specification — definition of correctness for a task'",
]

SQL_DOWN = [
    "DROP TABLE IF EXISTS intent_spec",
]


async def migrate_up() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL_UP:
            await conn.execute(text(stmt))
    await engine.dispose()


async def migrate_down() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL_DOWN:
            await conn.execute(text(stmt))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate_up())
    print("Migration 004_intent_spec applied.")
