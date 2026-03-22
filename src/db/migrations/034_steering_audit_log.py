"""Migration 034: Create steering_audit_log table and steering_action enum.

Supports Epic 37 Slice 1 (Pause/Resume/Abort) and future slices (Retry/Redirect).
Records every manual steering action taken on a pipeline task with full context:
action type, stage transition, optional reason, timestamp, and actor.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    # Create the steering_action enum type
    """
    DO $$ BEGIN
        CREATE TYPE steering_action AS ENUM (
            'pause', 'resume', 'abort', 'redirect', 'retry'
        );
    EXCEPTION
        WHEN duplicate_object THEN NULL;
    END $$;
    """,
    # Create the steering_audit_log table
    """
    CREATE TABLE IF NOT EXISTS steering_audit_log (
        id          UUID         PRIMARY KEY,
        task_id     UUID         NOT NULL,
        action      steering_action NOT NULL,
        from_stage  VARCHAR(100),
        to_stage    VARCHAR(100),
        reason      TEXT,
        timestamp   TIMESTAMPTZ  NOT NULL,
        actor       VARCHAR(255) NOT NULL DEFAULT 'system'
    );
    """,
    # Indexes for common query patterns
    "CREATE INDEX IF NOT EXISTS ix_steering_audit_log_task_id ON steering_audit_log (task_id);",
    "CREATE INDEX IF NOT EXISTS ix_steering_audit_log_ts ON steering_audit_log (timestamp DESC);",
]

SQL_DOWN = [
    "DROP TABLE IF EXISTS steering_audit_log;",
    "DROP TYPE  IF EXISTS steering_action;",
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
    print("Migration 034 applied.")
