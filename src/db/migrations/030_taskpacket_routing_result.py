"""Migration 030: Add routing_result JSONB column to taskpacket.

Stores the full ConsultPlan (expert selections, rationale, budget_remaining)
produced by the Router activity so the planning dashboard can display and
allow developers to review/override expert routing.

Nullable for tasks that predate this migration or where routing_review is off.

Schema (stored as JSONB):
{
    "taskpacket_id": "<uuid>",
    "selections": [
        {
            "expert_id": "<uuid>",
            "expert_class": "security",
            "pattern": "parallel",
            "reputation_weight": 0.9,
            "reputation_confidence": 0.8,
            "selection_score": 1.72,
            "selection_reason": "High security risk flags"
        }
    ],
    "rationale": "Selected security + backend experts for auth overhaul",
    "budget_remaining": 3
}

Epic 36, Slice 3 — Story 36.14c
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

SQL_UP = [
    """
    ALTER TABLE taskpacket
    ADD COLUMN IF NOT EXISTS routing_result JSONB DEFAULT NULL
    """,
]

SQL_DOWN = [
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS routing_result",
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
    print("Migration 030 applied.")
