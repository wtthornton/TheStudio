"""Migration 031: Create board_preferences table.

Stores per-column UI preferences for the Backlog Board (column width,
collapse state, sort field, sort direction). Keyed by column_id string
(e.g. "triage", "planning", "building", "verify", "done", "rejected").

Epic 36, Slice 4 — Story 36.17
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    """CREATE TABLE IF NOT EXISTS board_preferences (
    column_id VARCHAR(64) PRIMARY KEY,
    width INTEGER DEFAULT NULL,
    collapsed BOOLEAN NOT NULL DEFAULT FALSE,
    sort_field VARCHAR(64) DEFAULT NULL,
    sort_direction VARCHAR(4) DEFAULT NULL CHECK (sort_direction IN ('asc', 'desc')),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
    "COMMENT ON TABLE board_preferences IS"
    " 'Backlog board column UI preferences (width, collapse, sort)'",
]

SQL_DOWN = [
    "DROP TABLE IF EXISTS board_preferences",
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
    print("Migration 031 applied.")
