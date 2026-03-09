"""Migration 005: Create expert library tables.

Run with: python -m src.db.migrations.005_expert_library
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    """CREATE TYPE expert_class AS ENUM (
    'technical', 'business', 'partner', 'qa_validation',
    'security', 'compliance', 'service', 'process_quality'
)""",
    """CREATE TYPE trust_tier AS ENUM ('shadow', 'probation', 'trusted')""",
    """CREATE TYPE lifecycle_state AS ENUM ('active', 'deprecated', 'retired')""",
    """CREATE TABLE experts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    expert_class expert_class NOT NULL,
    capability_tags VARCHAR(100)[] NOT NULL,
    scope_description VARCHAR(2000) NOT NULL,
    tool_policy JSONB NOT NULL DEFAULT '{}',
    trust_tier trust_tier NOT NULL DEFAULT 'shadow',
    lifecycle_state lifecycle_state NOT NULL DEFAULT 'active',
    current_version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
    """CREATE TABLE expert_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    expert_id UUID NOT NULL REFERENCES experts(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    definition JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
)""",
    "CREATE INDEX ix_expert_versions_expert_id ON expert_versions (expert_id)",
    "CREATE INDEX ix_experts_class ON experts (expert_class)",
    "CREATE INDEX ix_experts_capability_tags ON experts USING GIN (capability_tags)",
    "COMMENT ON TABLE experts IS 'Expert Library — registry of domain experts'",
    "COMMENT ON TABLE expert_versions IS 'Expert version history'",
]

SQL_DOWN = [
    "DROP TABLE IF EXISTS expert_versions",
    "DROP TABLE IF EXISTS experts",
    "DROP TYPE IF EXISTS lifecycle_state",
    "DROP TYPE IF EXISTS trust_tier",
    "DROP TYPE IF EXISTS expert_class",
]


async def migrate_up() -> None:
    """Apply migration 005."""
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL_UP:
            await conn.execute(text(stmt))
    await engine.dispose()


async def migrate_down() -> None:
    """Reverse migration 005."""
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for stmt in SQL_DOWN:
            await conn.execute(text(stmt))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate_up())
    print("Migration 005_expert_library applied.")
