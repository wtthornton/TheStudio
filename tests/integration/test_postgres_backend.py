"""Postgres backend smoke test — Story 30.5.

Validates that TaskPackets, intent specs, and enrichment data
persist correctly through PostgreSQL with the full lifecycle:
  RECEIVED → ENRICHED → INTENT_BUILT → IN_PROGRESS →
  VERIFICATION_PASSED → PUBLISHED

Requires a running PostgreSQL instance. Marked as integration tests.
Run with: pytest -m integration tests/integration/test_postgres_backend.py
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.db.base import Base
from src.models.taskpacket import TaskPacketCreate, TaskPacketStatus
from src.models.taskpacket_crud import (
    create,
    get_by_id,
    update_enrichment,
    update_intent,
    update_status,
)
from src.settings import settings

pytestmark = pytest.mark.integration


@pytest.fixture
async def session():
    """Create a test database session with fresh tables."""
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# --- Lifecycle Round-Trip ---


async def test_full_lifecycle_roundtrip(session: AsyncSession) -> None:
    """TaskPacket survives full status lifecycle through Postgres."""
    data = TaskPacketCreate(
        repo="test-org/smoke-test",
        issue_id=1,
        delivery_id=str(uuid4()),
        correlation_id=uuid4(),
    )
    tp = await create(session, data)
    assert tp.status == TaskPacketStatus.RECEIVED
    task_id = tp.id

    # RECEIVED → ENRICHED (via update_enrichment)
    tp = await update_enrichment(
        session,
        task_id,
        scope={"files": ["src/main.py"], "language": "python"},
        risk_flags={"security": False, "migration": True},
        complexity_index={"overall": 0.4, "loc_delta": 50},
        context_packs=[{"type": "readme", "content": "# Test"}],
    )
    assert tp.status == TaskPacketStatus.ENRICHED

    # ENRICHED → INTENT_BUILT (via update_intent)
    intent_id = uuid4()
    tp = await update_intent(session, task_id, intent_id, intent_version=1)
    assert tp.status == TaskPacketStatus.INTENT_BUILT
    assert tp.intent_spec_id == intent_id
    assert tp.intent_version == 1

    # INTENT_BUILT → IN_PROGRESS
    tp = await update_status(session, task_id, TaskPacketStatus.IN_PROGRESS)
    assert tp.status == TaskPacketStatus.IN_PROGRESS

    # IN_PROGRESS → VERIFICATION_PASSED
    tp = await update_status(session, task_id, TaskPacketStatus.VERIFICATION_PASSED)
    assert tp.status == TaskPacketStatus.VERIFICATION_PASSED

    # VERIFICATION_PASSED → PUBLISHED
    tp = await update_status(session, task_id, TaskPacketStatus.PUBLISHED)
    assert tp.status == TaskPacketStatus.PUBLISHED


# --- Enrichment Field Persistence ---


async def test_enrichment_fields_survive_roundtrip(session: AsyncSession) -> None:
    """All JSONB enrichment fields persist and can be read back intact."""
    scope = {"files": ["a.py", "b.py"], "language": "python", "framework": "fastapi"}
    risk_flags = {"security": True, "migration": False, "billing": True}
    complexity = {"overall": 0.72, "loc_delta": 250, "files_touched": 5}
    context_packs = [
        {"type": "readme", "content": "# Hello"},
        {"type": "docstring", "content": "Module docs"},
    ]

    data = TaskPacketCreate(
        repo="test-org/enrichment-test",
        issue_id=2,
        delivery_id=str(uuid4()),
    )
    tp = await create(session, data)
    tp = await update_enrichment(
        session, tp.id, scope, risk_flags, complexity, context_packs
    )

    # Read back from DB
    fetched = await get_by_id(session, tp.id)
    assert fetched is not None
    assert fetched.scope == scope
    assert fetched.risk_flags == risk_flags
    assert fetched.complexity_index == complexity
    assert fetched.context_packs == context_packs


# --- Intent Persistence ---


async def test_intent_spec_persists(session: AsyncSession) -> None:
    """Intent spec ID and version survive round-trip."""
    data = TaskPacketCreate(
        repo="test-org/intent-test",
        issue_id=3,
        delivery_id=str(uuid4()),
    )
    tp = await create(session, data)
    tp = await update_enrichment(
        session, tp.id,
        scope={}, risk_flags={}, complexity_index={}, context_packs=[],
    )

    intent_id = uuid4()
    tp = await update_intent(session, tp.id, intent_id, intent_version=3)

    fetched = await get_by_id(session, tp.id)
    assert fetched is not None
    assert fetched.intent_spec_id == intent_id
    assert fetched.intent_version == 3


# --- Deduplication ---


async def test_deduplication_across_sessions(session: AsyncSession) -> None:
    """Duplicate (delivery_id, repo) returns existing record, not error."""
    delivery = str(uuid4())
    data = TaskPacketCreate(
        repo="test-org/dedup-test",
        issue_id=4,
        delivery_id=delivery,
    )
    first = await create(session, data)
    second = await create(session, data)
    assert first.id == second.id


# --- Correlation ID Lookup ---


async def test_correlation_id_lookup(session: AsyncSession) -> None:
    """TaskPacket can be found by correlation_id after persistence."""
    from src.models.taskpacket_crud import get_by_correlation_id

    cid = uuid4()
    data = TaskPacketCreate(
        repo="test-org/cid-test",
        issue_id=5,
        delivery_id=str(uuid4()),
        correlation_id=cid,
    )
    created = await create(session, data)
    fetched = await get_by_correlation_id(session, cid)
    assert fetched is not None
    assert fetched.id == created.id


# --- Model Audit Persistence ---


async def test_model_audit_roundtrip(session: AsyncSession) -> None:
    """ModelCallAudit records persist through PostgreSQL."""
    from datetime import UTC, datetime

    from src.admin.model_gateway import ModelCallAudit
    from src.admin.persistence.pg_model_audit import PostgresModelAuditStore
    from src.db.models import ModelCallAuditRow  # noqa: F401 — ensure table exists

    # Ensure the model_call_audit table exists
    engine = session.get_bind()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    store = PostgresModelAuditStore(session)
    task_id = uuid4()
    audit = ModelCallAudit(
        id=uuid4(),
        correlation_id=uuid4(),
        task_id=task_id,
        step="intent",
        role="developer",
        overlays=["security"],
        provider="anthropic",
        model="claude-sonnet-4-6",
        tokens_in=500,
        tokens_out=200,
        cost=0.0045,
        latency_ms=1500.0,
        created_at=datetime.now(UTC),
    )
    await store.record(audit)
    results = await store.query(task_id=str(task_id))
    assert len(results) == 1
    assert results[0].step == "intent"
    assert results[0].cost == pytest.approx(0.0045)
