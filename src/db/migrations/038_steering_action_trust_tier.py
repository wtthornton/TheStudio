"""Migration 038: Extend steering_action enum with trust_tier_assigned and trust_tier_overridden.

Adds two new values to the existing ``steering_action`` PostgreSQL enum so that
trust-tier assignment and safety-bounds overrides can be recorded in the
steering audit log alongside manual steering actions.

Epic 37 Slice 3 — Task 37.18.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    # PostgreSQL ALTER TYPE … ADD VALUE is transactional only in PG 12+.
    # The IF NOT EXISTS guard prevents errors on re-runs.
    "ALTER TYPE steering_action ADD VALUE IF NOT EXISTS 'trust_tier_assigned';",
    "ALTER TYPE steering_action ADD VALUE IF NOT EXISTS 'trust_tier_overridden';",
]

SQL_DOWN = [
    # PostgreSQL does not support removing values from an enum type without
    # recreating it.  The safest rollback is a no-op; the values are harmless
    # if unused.  Document this clearly so operators are aware.
    "SELECT 1; -- NOTE: enum value removal is not supported by PostgreSQL; manual type recreation required if rollback is critical.",
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
    print("Migration 038 applied.")
