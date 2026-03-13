"""Migration 019: Add weight_history JSONB column to expert_reputation.

Stores rolling weight history for drift detection and audit trail.

Run with: python -m src.db.migrations.019_reputation_weight_history
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    """
    ALTER TABLE expert_reputation
    ADD COLUMN IF NOT EXISTS weight_history JSONB DEFAULT '[]'
    """,
]

SQL_DOWN = [
    "ALTER TABLE expert_reputation DROP COLUMN IF EXISTS weight_history",
]


async def migrate_up() -> None:
    """Apply migration."""
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL_UP:
            await conn.execute(text(stmt))
    await engine.dispose()


async def migrate_down() -> None:
    """Revert migration."""
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL_DOWN:
            await conn.execute(text(stmt))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate_up())
    print("Migration 019_reputation_weight_history applied.")
