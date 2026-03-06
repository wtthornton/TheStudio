"""Migration 002: Create repo_profile table.

Run with: python -m src.db.migrations.002_repo_profile
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    "CREATE TYPE repo_tier AS ENUM ('observe', 'suggest', 'execute')",
    "CREATE TYPE repo_status AS ENUM ('active', 'paused', 'disabled')",
    """CREATE TABLE repo_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner VARCHAR(255) NOT NULL,
    repo_name VARCHAR(255) NOT NULL,
    installation_id INTEGER NOT NULL,
    tier repo_tier NOT NULL DEFAULT 'observe',
    required_checks JSONB NOT NULL DEFAULT '["ruff", "pytest"]'::jsonb,
    tool_allowlist JSONB NOT NULL DEFAULT '[]'::jsonb,
    webhook_secret_encrypted VARCHAR(512) NOT NULL,
    status repo_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (owner, repo_name)
)""",
    "CREATE INDEX ix_repo_profile_status ON repo_profile (status)",
    "COMMENT ON TABLE repo_profile IS 'Repo Profile — registered repository config'",
]

SQL_DOWN = [
    "DROP TABLE IF EXISTS repo_profile",
    "DROP TYPE IF EXISTS repo_status",
    "DROP TYPE IF EXISTS repo_tier",
]


async def migrate_up() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL_UP:
            await conn.execute(text(stmt))
    await engine.dispose()


async def migrate_down() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL_DOWN:
            await conn.execute(text(stmt))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate_up())
    print("Migration 002_repo_profile applied.")
