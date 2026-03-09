"""Migration 006: Upgrade complexity_index from VARCHAR(20) to JSONB.

Complexity Index v1 stores full dimensions for learning loop normalization.
See docs/architecture/complexity-index-v1.md for schema details.

Run with: python -m src.db.migrations.006_complexity_index_v1
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    # Add new JSONB column for v1 complexity index
    "ALTER TABLE taskpacket ADD COLUMN complexity_index_v1 JSONB",
    # Migrate existing band values to v1 format (preserve backward compat)
    """
    UPDATE taskpacket
    SET complexity_index_v1 = jsonb_build_object(
        'score', NULL,
        'band', complexity_index,
        'dimensions', NULL
    )
    WHERE complexity_index IS NOT NULL
    """,
    # Drop old VARCHAR column
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS complexity_index",
    # Rename v1 column to complexity_index
    "ALTER TABLE taskpacket RENAME COLUMN complexity_index_v1 TO complexity_index",
]

SQL_DOWN = [
    # Add back VARCHAR column
    "ALTER TABLE taskpacket ADD COLUMN complexity_index_old VARCHAR(20)",
    # Extract band from JSONB
    """
    UPDATE taskpacket
    SET complexity_index_old = complexity_index->>'band'
    WHERE complexity_index IS NOT NULL
    """,
    # Drop JSONB column
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS complexity_index",
    # Rename back
    "ALTER TABLE taskpacket RENAME COLUMN complexity_index_old TO complexity_index",
]


async def migrate_up() -> None:
    """Apply migration 006."""
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL_UP:
            await conn.execute(text(stmt))
    await engine.dispose()


async def migrate_down() -> None:
    """Reverse migration 006."""
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL_DOWN:
            await conn.execute(text(stmt))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate_up())
    print("Migration 006_complexity_index_v1 applied.")
