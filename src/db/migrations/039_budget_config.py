"""Migration 039: Create budget_config table.

Stores operator-defined budget thresholds and automated response actions.
A singleton row (id = 00000000-0000-0000-0000-000000000002) is the canonical
source of truth for all budget configuration.

Epic 37 Slice 4 — Task 37.20.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    """
    CREATE TABLE IF NOT EXISTS budget_config (
        id                          UUID         PRIMARY KEY,
        daily_spend_warning         FLOAT,
        weekly_budget_cap           FLOAT,
        per_task_warning            FLOAT,
        pause_on_budget_exceeded    BOOLEAN      NOT NULL DEFAULT FALSE,
        model_downgrade_on_approach BOOLEAN      NOT NULL DEFAULT FALSE,
        downgrade_threshold_percent FLOAT        NOT NULL DEFAULT 80.0,
        updated_at                  TIMESTAMPTZ  NOT NULL
    );
    """,
    # Seed singleton row with safe defaults (no limits, automation disabled)
    """
    INSERT INTO budget_config (
        id,
        daily_spend_warning,
        weekly_budget_cap,
        per_task_warning,
        pause_on_budget_exceeded,
        model_downgrade_on_approach,
        downgrade_threshold_percent,
        updated_at
    )
    VALUES (
        '00000000-0000-0000-0000-000000000002',
        NULL,
        NULL,
        NULL,
        FALSE,
        FALSE,
        80.0,
        NOW()
    )
    ON CONFLICT (id) DO NOTHING;
    """,
]

SQL_DOWN = [
    "DROP TABLE IF EXISTS budget_config;",
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
    print("Migration 039 applied.")
