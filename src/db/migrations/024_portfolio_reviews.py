"""Migration 024: Create portfolio_reviews table for Meridian portfolio health reviews.

Epic 29 AC 15: Stores portfolio review results with overall health, flags,
metrics, and recommendations as JSON columns.

Run with: python -m src.db.migrations.024_portfolio_reviews
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    """
    CREATE TABLE IF NOT EXISTS portfolio_reviews (
        id SERIAL PRIMARY KEY,
        reviewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        overall_health VARCHAR(20) NOT NULL,
        flags JSONB NOT NULL DEFAULT '[]'::jsonb,
        metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
        recommendations JSONB NOT NULL DEFAULT '[]'::jsonb
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_portfolio_reviews_reviewed_at
    ON portfolio_reviews (reviewed_at DESC)
    """,
]

SQL_DOWN = [
    "DROP INDEX IF EXISTS ix_portfolio_reviews_reviewed_at",
    "DROP TABLE IF EXISTS portfolio_reviews",
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
