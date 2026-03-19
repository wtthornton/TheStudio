"""Migration 026: Add poll conditional header columns to repo_profile.

Stores ETag, Last-Modified, and since-timestamp for conditional polling
requests (Epic 17). Also adds readiness_gate_enabled feature flag.

Run with: python -m src.db.migrations.026_repo_profile_poll_headers
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    """
    ALTER TABLE repo_profile
    ADD COLUMN IF NOT EXISTS poll_etag VARCHAR(255) DEFAULT NULL
    """,
    """
    ALTER TABLE repo_profile
    ADD COLUMN IF NOT EXISTS poll_last_modified VARCHAR(255) DEFAULT NULL
    """,
    """
    ALTER TABLE repo_profile
    ADD COLUMN IF NOT EXISTS poll_since VARCHAR(64) DEFAULT NULL
    """,
    """
    ALTER TABLE repo_profile
    ADD COLUMN IF NOT EXISTS readiness_gate_enabled BOOLEAN NOT NULL DEFAULT FALSE
    """,
]

SQL_DOWN = [
    "ALTER TABLE repo_profile DROP COLUMN IF EXISTS readiness_gate_enabled",
    "ALTER TABLE repo_profile DROP COLUMN IF EXISTS poll_since",
    "ALTER TABLE repo_profile DROP COLUMN IF EXISTS poll_last_modified",
    "ALTER TABLE repo_profile DROP COLUMN IF EXISTS poll_etag",
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
    print("Migration 026 applied.")
