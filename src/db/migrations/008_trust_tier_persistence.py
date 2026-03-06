"""Migration 008: Add trust tier persistence columns to expert_reputation.

Per Story 2.6:
- trust_tier: enum (shadow, probation, trusted)
- tier_changed_at: timestamp of last tier transition
- last_outcome_at: timestamp for decay calculation
- drift_direction: enum (improving, stable, declining)
- drift_score: rolling window trend

Run with: python -m src.db.migrations.008_trust_tier_persistence
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    # Create enum type for trust tiers
    """
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'trust_tier') THEN
            CREATE TYPE trust_tier AS ENUM ('shadow', 'probation', 'trusted');
        END IF;
    END
    $$
    """,
    # Create enum type for drift direction
    """
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'drift_direction') THEN
            CREATE TYPE drift_direction AS ENUM ('improving', 'stable', 'declining');
        END IF;
    END
    $$
    """,
    # Create expert_reputation table if not exists
    """
    CREATE TABLE IF NOT EXISTS expert_reputation (
        expert_id UUID NOT NULL,
        context_key VARCHAR(255) NOT NULL,
        expert_version INTEGER NOT NULL DEFAULT 1,
        weight FLOAT NOT NULL DEFAULT 0.5,
        raw_weight_sum FLOAT NOT NULL DEFAULT 0.0,
        sample_count INTEGER NOT NULL DEFAULT 0,
        confidence FLOAT NOT NULL DEFAULT 0.1,
        trust_tier trust_tier NOT NULL DEFAULT 'shadow',
        tier_changed_at TIMESTAMPTZ,
        last_outcome_at TIMESTAMPTZ,
        drift_direction drift_direction NOT NULL DEFAULT 'stable',
        drift_score FLOAT NOT NULL DEFAULT 0.0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (expert_id, context_key)
    )
    """,
    # Add columns if table already exists (for idempotency)
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'expert_reputation' AND column_name = 'trust_tier'
        ) THEN
            ALTER TABLE expert_reputation ADD COLUMN trust_tier trust_tier NOT NULL DEFAULT 'shadow';
        END IF;
    END
    $$
    """,
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'expert_reputation' AND column_name = 'tier_changed_at'
        ) THEN
            ALTER TABLE expert_reputation ADD COLUMN tier_changed_at TIMESTAMPTZ;
        END IF;
    END
    $$
    """,
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'expert_reputation' AND column_name = 'last_outcome_at'
        ) THEN
            ALTER TABLE expert_reputation ADD COLUMN last_outcome_at TIMESTAMPTZ;
        END IF;
    END
    $$
    """,
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'expert_reputation' AND column_name = 'drift_direction'
        ) THEN
            ALTER TABLE expert_reputation ADD COLUMN drift_direction drift_direction NOT NULL DEFAULT 'stable';
        END IF;
    END
    $$
    """,
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'expert_reputation' AND column_name = 'drift_score'
        ) THEN
            ALTER TABLE expert_reputation ADD COLUMN drift_score FLOAT NOT NULL DEFAULT 0.0;
        END IF;
    END
    $$
    """,
    # Create indexes
    "CREATE INDEX IF NOT EXISTS idx_expert_reputation_trust_tier ON expert_reputation(trust_tier)",
    "CREATE INDEX IF NOT EXISTS idx_expert_reputation_last_outcome ON expert_reputation(last_outcome_at)",
    "CREATE INDEX IF NOT EXISTS idx_expert_reputation_drift ON expert_reputation(drift_direction)",
]

SQL_DOWN = [
    "ALTER TABLE expert_reputation DROP COLUMN IF EXISTS drift_score",
    "ALTER TABLE expert_reputation DROP COLUMN IF EXISTS drift_direction",
    "ALTER TABLE expert_reputation DROP COLUMN IF EXISTS last_outcome_at",
    "ALTER TABLE expert_reputation DROP COLUMN IF EXISTS tier_changed_at",
    "ALTER TABLE expert_reputation DROP COLUMN IF EXISTS trust_tier",
    "DROP TYPE IF EXISTS drift_direction",
    "DROP TYPE IF EXISTS trust_tier",
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
    print("Migration 008_trust_tier_persistence applied.")
