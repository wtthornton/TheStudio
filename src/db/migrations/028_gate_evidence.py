"""Migration 028: Create gate_evidence table.

Stores gate pass/fail results with checks and evidence artifacts
for the dashboard Gate Inspector (Epic 35, Slice 2).

Run with: python -m src.db.migrations.028_gate_evidence
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    """
    CREATE TABLE IF NOT EXISTS gate_evidence (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        task_id UUID NOT NULL,
        stage VARCHAR(50) NOT NULL,
        result VARCHAR(20) NOT NULL,
        checks JSONB,
        defect_category VARCHAR(100),
        evidence_artifact JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_gate_evidence_task_id ON gate_evidence (task_id)",
    "CREATE INDEX IF NOT EXISTS ix_gate_evidence_stage ON gate_evidence (stage)",
    "CREATE INDEX IF NOT EXISTS ix_gate_evidence_result ON gate_evidence (result)",
]

SQL_DOWN = [
    "DROP INDEX IF EXISTS ix_gate_evidence_result",
    "DROP INDEX IF EXISTS ix_gate_evidence_stage",
    "DROP INDEX IF EXISTS ix_gate_evidence_task_id",
    "DROP TABLE IF EXISTS gate_evidence",
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
    print("Migration 028 applied.")
