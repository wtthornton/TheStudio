"""Migration 025: Add readiness gate columns to taskpacket.

Epic 28 — Preflight Readiness Gate. These columns track readiness evaluation
state per TaskPacket: evaluation count, hold comment ID, score, and miss flag.

Run with: python -m src.db.migrations.025_taskpacket_readiness
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    """
    ALTER TABLE taskpacket
    ADD COLUMN IF NOT EXISTS readiness_evaluation_count INTEGER NOT NULL DEFAULT 0
    """,
    """
    ALTER TABLE taskpacket
    ADD COLUMN IF NOT EXISTS readiness_hold_comment_id VARCHAR(255) DEFAULT NULL
    """,
    """
    ALTER TABLE taskpacket
    ADD COLUMN IF NOT EXISTS readiness_score FLOAT DEFAULT NULL
    """,
    """
    ALTER TABLE taskpacket
    ADD COLUMN IF NOT EXISTS readiness_miss BOOLEAN NOT NULL DEFAULT FALSE
    """,
]

SQL_DOWN = [
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS readiness_miss",
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS readiness_score",
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS readiness_hold_comment_id",
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS readiness_evaluation_count",
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
    print("Migration 025 applied.")
