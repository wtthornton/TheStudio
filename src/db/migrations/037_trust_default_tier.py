"""Migration 037: Add default_tier column to trust_safety_bounds singleton.

Supports Epic 37 Slice 3 Task 37.15 (Trust Tier CRUD API).

default_tier — fallback tier used by the evaluation engine when no rule
               matches.  Values: observe / suggest / execute.  Defaults to
               'observe' (most restrictive) so safety is preserved even if
               rules are not yet configured.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    # Ensure the enum type exists (created in migration 036 for taskpacket)
    """
    DO $$ BEGIN
        CREATE TYPE task_trust_tier_enum AS ENUM ('observe', 'suggest', 'execute');
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END $$;
    """,
    # Add default_tier column to the singleton table
    """
    ALTER TABLE trust_safety_bounds
        ADD COLUMN IF NOT EXISTS default_tier VARCHAR(20) NOT NULL DEFAULT 'observe';
    """,
]

SQL_DOWN = [
    "ALTER TABLE trust_safety_bounds DROP COLUMN IF EXISTS default_tier;",
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
    print("Migration 037 applied.")
