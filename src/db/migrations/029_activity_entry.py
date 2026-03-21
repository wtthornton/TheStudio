"""Migration 029: Create activity_entry table.

Stores per-task activity log entries (file edits, searches, test runs, etc.)
for the dashboard Activity Stream (Epic 35, Slice 3).

Run with: python -m src.db.migrations.029_activity_entry
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    """
    CREATE TABLE IF NOT EXISTS activity_entry (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        task_id UUID NOT NULL,
        stage VARCHAR(50) NOT NULL,
        activity_type VARCHAR(50) NOT NULL,
        subphase VARCHAR(100) NOT NULL DEFAULT '',
        content TEXT NOT NULL,
        detail TEXT NOT NULL DEFAULT '',
        metadata JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_activity_entry_task_id ON activity_entry (task_id)",
    "CREATE INDEX IF NOT EXISTS ix_activity_entry_stage ON activity_entry (stage)",
    "CREATE INDEX IF NOT EXISTS ix_activity_entry_activity_type ON activity_entry (activity_type)",
]

SQL_DOWN = [
    "DROP INDEX IF EXISTS ix_activity_entry_activity_type",
    "DROP INDEX IF EXISTS ix_activity_entry_stage",
    "DROP INDEX IF EXISTS ix_activity_entry_task_id",
    "DROP TABLE IF EXISTS activity_entry",
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
    print("Migration 029 applied.")
