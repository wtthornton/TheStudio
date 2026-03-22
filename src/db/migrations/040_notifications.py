"""Migration 040: Create notifications table.

Stores operator-visible notifications generated from pipeline NATS events
(gate failures, cost updates, steering actions, trust tier assignments).

Epic 37 Slice 5 — Task 37.24.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    """
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notification_type') THEN
            CREATE TYPE notification_type AS ENUM (
                'gate_fail',
                'cost_update',
                'steering_action',
                'trust_tier_assigned'
            );
        END IF;
    END $$;
    """,
    """
    CREATE TABLE IF NOT EXISTS notifications (
        id          UUID                     PRIMARY KEY,
        type        notification_type        NOT NULL,
        title       VARCHAR(500)             NOT NULL,
        message     TEXT                     NOT NULL,
        task_id     UUID,
        read        BOOLEAN                  NOT NULL DEFAULT FALSE,
        created_at  TIMESTAMPTZ              NOT NULL DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_notifications_task_id    ON notifications (task_id);",
    "CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications (created_at);",
    "CREATE INDEX IF NOT EXISTS ix_notifications_read       ON notifications (read);",
]

SQL_DOWN = [
    "DROP TABLE IF EXISTS notifications;",
    "DROP TYPE IF EXISTS notification_type;",
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
    print("Migration 040 applied.")
