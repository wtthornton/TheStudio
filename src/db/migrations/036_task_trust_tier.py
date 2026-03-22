"""Migration 036: Add task_trust_tier column to taskpacket table.

Supports Epic 37 Slice 3 (Trust Tier Configuration).

task_trust_tier — nullable pipeline-level trust tier assigned by the
                  trust rule engine before the first pipeline activity.
                  Values: observe / suggest / execute.
                  NULL for tasks created before the trust engine was deployed.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    # Create the enum type for task_trust_tier
    """
    DO $$ BEGIN
        CREATE TYPE task_trust_tier_enum AS ENUM ('observe', 'suggest', 'execute');
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END $$;
    """,
    # Add the nullable column to taskpacket
    """
    ALTER TABLE taskpacket
        ADD COLUMN IF NOT EXISTS task_trust_tier task_trust_tier_enum;
    """,
    # Index for efficient filtering by trust tier
    "CREATE INDEX IF NOT EXISTS ix_taskpacket_task_trust_tier ON taskpacket (task_trust_tier);",
]

SQL_DOWN = [
    "DROP INDEX IF EXISTS ix_taskpacket_task_trust_tier;",
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS task_trust_tier;",
    "DROP TYPE IF EXISTS task_trust_tier_enum;",
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
    print("Migration 036 applied.")
