"""Migration 035: Create trust_tier_rules and trust_safety_bounds tables.

Supports Epic 37 Slice 3 (Trust Tier Configuration).

trust_tier_rules   — operator-defined ordered rules that map TaskPacket
                     metadata to a trust tier (observe / suggest / execute).
trust_safety_bounds — singleton row capping the blast radius of automated
                      actions regardless of tier assignment.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    # trust_tier_rules
    """
    CREATE TABLE IF NOT EXISTS trust_tier_rules (
        id              UUID         PRIMARY KEY,
        priority        INTEGER      NOT NULL DEFAULT 100,
        conditions      JSONB        NOT NULL DEFAULT '[]',
        assigned_tier   VARCHAR(20)  NOT NULL,
        active          BOOLEAN      NOT NULL DEFAULT TRUE,
        description     TEXT,
        created_at      TIMESTAMPTZ  NOT NULL,
        updated_at      TIMESTAMPTZ  NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_trust_tier_rules_priority ON trust_tier_rules (priority ASC);",
    "CREATE INDEX IF NOT EXISTS ix_trust_tier_rules_active   ON trust_tier_rules (active);",
    # trust_safety_bounds (singleton)
    """
    CREATE TABLE IF NOT EXISTS trust_safety_bounds (
        id                          UUID     PRIMARY KEY,
        max_auto_merge_lines        INTEGER,
        max_auto_merge_cost         INTEGER,
        max_loopbacks               INTEGER,
        mandatory_review_patterns   JSONB    NOT NULL DEFAULT '[]',
        updated_at                  TIMESTAMPTZ NOT NULL
    );
    """,
    # Seed the singleton row with safe defaults
    """
    INSERT INTO trust_safety_bounds (
        id,
        max_auto_merge_lines,
        max_auto_merge_cost,
        max_loopbacks,
        mandatory_review_patterns,
        updated_at
    )
    VALUES (
        '00000000-0000-0000-0000-000000000001',
        500,
        500,
        3,
        '["**/migrations/**", "**/settings*"]',
        NOW()
    )
    ON CONFLICT (id) DO NOTHING;
    """,
]

SQL_DOWN = [
    "DROP TABLE IF EXISTS trust_safety_bounds;",
    "DROP TABLE IF EXISTS trust_tier_rules;",
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
    print("Migration 035 applied.")
