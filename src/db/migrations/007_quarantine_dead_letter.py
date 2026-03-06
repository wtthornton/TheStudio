"""Migration 007: Create quarantined_events and dead_letter_events tables.

Per thestudioarc/12-outcome-ingestor.md lines 83-105:
- Quarantine rules for malformed or uncorrelated events
- Dead-letter for events that fail after N attempts
- Replay and correction support

Run with: python -m src.db.migrations.007_quarantine_dead_letter
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    # Create enum type for quarantine reasons
    """
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'quarantine_reason') THEN
            CREATE TYPE quarantine_reason AS ENUM (
                'missing_correlation_id',
                'unknown_taskpacket',
                'unknown_repo',
                'invalid_event',
                'invalid_category_severity',
                'idempotency_conflict'
            );
        END IF;
    END
    $$
    """,
    # Create quarantined_events table
    """
    CREATE TABLE IF NOT EXISTS quarantined_events (
        quarantine_id UUID PRIMARY KEY,
        event_payload JSONB NOT NULL,
        reason quarantine_reason NOT NULL,
        repo_id VARCHAR(255),
        category VARCHAR(100),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        corrected_at TIMESTAMPTZ,
        corrected_payload JSONB,
        replayed_at TIMESTAMPTZ
    )
    """,
    # Create indexes for quarantined_events
    "CREATE INDEX IF NOT EXISTS idx_quarantined_events_repo_id ON quarantined_events(repo_id)",
    "CREATE INDEX IF NOT EXISTS idx_quarantined_events_reason ON quarantined_events(reason)",
    "CREATE INDEX IF NOT EXISTS idx_quarantined_events_created_at ON quarantined_events(created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_quarantined_events_not_replayed ON quarantined_events(replayed_at) WHERE replayed_at IS NULL",
    # Create dead_letter_events table
    """
    CREATE TABLE IF NOT EXISTS dead_letter_events (
        id UUID PRIMARY KEY,
        raw_payload BYTEA NOT NULL,
        failure_reason TEXT NOT NULL,
        attempt_count INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    # Create index for dead_letter_events
    "CREATE INDEX IF NOT EXISTS idx_dead_letter_events_created_at ON dead_letter_events(created_at DESC)",
]

SQL_DOWN = [
    "DROP TABLE IF EXISTS dead_letter_events",
    "DROP TABLE IF EXISTS quarantined_events",
    "DROP TYPE IF EXISTS quarantine_reason",
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
    print("Migration 007_quarantine_dead_letter applied.")
