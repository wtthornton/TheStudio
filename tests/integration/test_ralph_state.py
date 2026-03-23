"""Integration tests for PostgresStateBackend (Story 43.9).

Covers:
  - Round-trip: write then read back every key type (status, circuit_breaker,
    call_count, last_reset, session_id, fix_plan)
  - Isolation: two distinct taskpacket_ids never share state
  - Concurrent upsert: racing writes resolve without error; last value wins
  - TTL: clear_session_if_stale() removes old sessions, keeps fresh ones

Requires a running PostgreSQL instance. Marked as integration tests.
Run with: pytest -m integration tests/integration/test_ralph_state.py
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.settings import settings

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Table DDL — mirrors migration 048 exactly
# ---------------------------------------------------------------------------

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ralph_agent_state (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    taskpacket_id   UUID         NOT NULL,
    key_name        VARCHAR(64)  NOT NULL,
    value_json      TEXT         NOT NULL,
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ralph_agent_state_task_key UNIQUE (taskpacket_id, key_name)
);
"""

_DROP_TABLE_SQL = "DROP TABLE IF EXISTS ralph_agent_state CASCADE;"
_CREATE_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS ix_ralph_agent_state_taskpacket_id"
    " ON ralph_agent_state (taskpacket_id);"
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def engine():
    """Async engine backed by settings.database_url with fresh ralph_agent_state table."""
    eng = create_async_engine(settings.database_url, echo=False)
    async with eng.begin() as conn:
        await conn.execute(text(_DROP_TABLE_SQL))
        await conn.execute(text(_CREATE_TABLE_SQL))
        await conn.execute(text(_CREATE_INDEX_SQL))
    yield eng
    async with eng.begin() as conn:
        await conn.execute(text(_DROP_TABLE_SQL))
    await eng.dispose()


@pytest.fixture
def session_factory(engine):
    """Return an async_sessionmaker bound to the test engine."""
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def patch_get_async_session(session_factory):
    """Patch src.agent.ralph_state.get_async_session to use the test engine."""

    @asynccontextmanager
    async def _test_session():
        async with session_factory() as sess:
            yield sess

    with patch("src.agent.ralph_state.get_async_session", side_effect=_test_session):
        yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _backend(taskpacket_id=None):
    """Construct a PostgresStateBackend for a new (or given) UUID."""
    from src.agent.ralph_state import PostgresStateBackend

    return PostgresStateBackend(taskpacket_id or uuid4())


# ---------------------------------------------------------------------------
# Round-trip: every public method pair
# ---------------------------------------------------------------------------


async def test_roundtrip_status(patch_get_async_session) -> None:
    """write_status → read_status returns identical dict."""
    backend = _backend()
    data = {"phase": "running", "iteration": 3, "errors": []}
    await backend.write_status(data)
    result = await backend.read_status()
    assert result == data


async def test_roundtrip_circuit_breaker(patch_get_async_session) -> None:
    """write_circuit_breaker → read_circuit_breaker returns identical dict."""
    backend = _backend()
    data = {"open": True, "failure_count": 5, "last_failure": "2026-03-23T00:00:00Z"}
    await backend.write_circuit_breaker(data)
    result = await backend.read_circuit_breaker()
    assert result == data


async def test_roundtrip_call_count(patch_get_async_session) -> None:
    """write_call_count → read_call_count returns identical int."""
    backend = _backend()
    await backend.write_call_count(42)
    assert await backend.read_call_count() == 42


async def test_roundtrip_last_reset(patch_get_async_session) -> None:
    """write_last_reset → read_last_reset returns identical Unix timestamp."""
    backend = _backend()
    ts = 1742688000  # 2025-03-23T00:00:00Z
    await backend.write_last_reset(ts)
    assert await backend.read_last_reset() == ts


async def test_roundtrip_session_id(patch_get_async_session) -> None:
    """write_session_id → read_session_id returns identical string."""
    backend = _backend()
    sid = f"session-{uuid4().hex}"
    await backend.write_session_id(sid)
    assert await backend.read_session_id() == sid


async def test_roundtrip_fix_plan(patch_get_async_session) -> None:
    """write_fix_plan → read_fix_plan returns identical multiline string."""
    backend = _backend()
    plan = "- [ ] Task 1\n- [ ] Task 2\n- [x] Task 3\n"
    await backend.write_fix_plan(plan)
    assert await backend.read_fix_plan() == plan


async def test_default_returns_empty(patch_get_async_session) -> None:
    """All read methods return safe defaults when no row exists."""
    backend = _backend()
    assert await backend.read_status() == {}
    assert await backend.read_circuit_breaker() == {}
    assert await backend.read_call_count() == 0
    assert await backend.read_last_reset() == 0
    assert await backend.read_session_id() == ""
    assert await backend.read_fix_plan() == ""


async def test_upsert_overwrites_existing(patch_get_async_session) -> None:
    """Second write to same key replaces first value (upsert semantics)."""
    backend = _backend()
    await backend.write_call_count(10)
    await backend.write_call_count(99)
    assert await backend.read_call_count() == 99


# ---------------------------------------------------------------------------
# Isolation: two taskpacket_ids never share state
# ---------------------------------------------------------------------------


async def test_isolation_between_taskpackets(patch_get_async_session) -> None:
    """State written under one taskpacket_id is invisible to another."""
    backend_a = _backend()
    backend_b = _backend()

    await backend_a.write_status({"owner": "a"})
    await backend_b.write_status({"owner": "b"})

    assert (await backend_a.read_status())["owner"] == "a"
    assert (await backend_b.read_status())["owner"] == "b"


async def test_isolation_call_count(patch_get_async_session) -> None:
    """call_count is scoped per-taskpacket — increments don't bleed across."""
    backend_a = _backend()
    backend_b = _backend()

    await backend_a.write_call_count(5)
    # backend_b has never written — should read 0
    assert await backend_b.read_call_count() == 0


async def test_isolation_session_id(patch_get_async_session) -> None:
    """session_id for taskpacket A is independent of taskpacket B."""
    backend_a = _backend()
    backend_b = _backend()

    sid_a = f"session-a-{uuid4().hex}"
    sid_b = f"session-b-{uuid4().hex}"
    await backend_a.write_session_id(sid_a)
    await backend_b.write_session_id(sid_b)

    assert await backend_a.read_session_id() == sid_a
    assert await backend_b.read_session_id() == sid_b


# ---------------------------------------------------------------------------
# Concurrent upsert: no errors, deterministic final state
# ---------------------------------------------------------------------------


async def test_concurrent_upsert_no_error(patch_get_async_session) -> None:
    """Multiple concurrent writes to the same key complete without exception."""
    backend = _backend()

    async def _write(n: int) -> None:
        await backend.write_call_count(n)

    # Launch 10 concurrent upserts — none should raise
    await asyncio.gather(*[_write(i) for i in range(10)])

    # Final value is one of the 10 writes — just verify it's readable
    result = await backend.read_call_count()
    assert 0 <= result <= 9


async def test_concurrent_upsert_different_keys(patch_get_async_session) -> None:
    """Concurrent writes to different keys do not interfere with each other."""
    backend = _backend()

    async def _write_status() -> None:
        await backend.write_status({"phase": "concurrent"})

    async def _write_count() -> None:
        await backend.write_call_count(7)

    async def _write_session() -> None:
        await backend.write_session_id("sid-concurrent")

    await asyncio.gather(_write_status(), _write_count(), _write_session())

    assert (await backend.read_status())["phase"] == "concurrent"
    assert await backend.read_call_count() == 7
    assert await backend.read_session_id() == "sid-concurrent"


async def test_concurrent_upsert_multiple_tasks(patch_get_async_session) -> None:
    """Concurrent upserts across multiple taskpacket_ids are each correct."""
    backends = [_backend() for _ in range(5)]

    async def _set_count(b, n: int) -> None:
        await b.write_call_count(n)

    await asyncio.gather(*[_set_count(b, i) for i, b in enumerate(backends)])

    for i, b in enumerate(backends):
        assert await b.read_call_count() == i


# ---------------------------------------------------------------------------
# TTL: clear_session_if_stale
# ---------------------------------------------------------------------------


async def test_ttl_no_session_returns_false(patch_get_async_session) -> None:
    """clear_session_if_stale returns False when no session_id row exists."""
    backend = _backend()
    cleared = await backend.clear_session_if_stale(ttl_seconds=3600)
    assert cleared is False


async def test_ttl_fresh_session_not_cleared(patch_get_async_session) -> None:
    """A freshly written session_id is not cleared (age < TTL)."""
    backend = _backend()
    await backend.write_session_id("fresh-session")
    cleared = await backend.clear_session_if_stale(ttl_seconds=3600)
    assert cleared is False
    # Session ID still present
    assert await backend.read_session_id() == "fresh-session"


async def test_ttl_stale_session_cleared(patch_get_async_session, engine) -> None:
    """A session_id older than TTL is deleted and clear_session_if_stale returns True."""
    backend = _backend()
    await backend.write_session_id("stale-session")

    # Manually backdate updated_at by 3 hours so the row is stale
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE ralph_agent_state"
                "   SET updated_at = NOW() - INTERVAL '3 hours'"
                " WHERE taskpacket_id = :tid AND key_name = 'session_id'"
            ),
            {"tid": backend._taskpacket_id},
        )

    cleared = await backend.clear_session_if_stale(ttl_seconds=7200)  # 2h TTL
    assert cleared is True

    # Row should be gone → read_session_id returns ""
    assert await backend.read_session_id() == ""


async def test_ttl_only_clears_session_id(patch_get_async_session, engine) -> None:
    """clear_session_if_stale deletes only the session_id row, not other keys."""
    backend = _backend()
    await backend.write_session_id("doomed-session")
    await backend.write_call_count(42)
    await backend.write_fix_plan("- [ ] Task A\n")

    # Backdate only the session_id row
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE ralph_agent_state"
                "   SET updated_at = NOW() - INTERVAL '3 hours'"
                " WHERE taskpacket_id = :tid AND key_name = 'session_id'"
            ),
            {"tid": backend._taskpacket_id},
        )

    await backend.clear_session_if_stale(ttl_seconds=7200)

    # Other keys are unaffected
    assert await backend.read_call_count() == 42
    assert await backend.read_fix_plan() == "- [ ] Task A\n"
    assert await backend.read_session_id() == ""


async def test_ttl_does_not_clear_other_tasks_session(
    patch_get_async_session, engine
) -> None:
    """Stale session clear for task A does not remove session_id from task B."""
    backend_a = _backend()
    backend_b = _backend()

    await backend_a.write_session_id("stale-a")
    await backend_b.write_session_id("fresh-b")

    # Backdate only task A's session_id
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE ralph_agent_state"
                "   SET updated_at = NOW() - INTERVAL '3 hours'"
                " WHERE taskpacket_id = :tid AND key_name = 'session_id'"
            ),
            {"tid": backend_a._taskpacket_id},
        )

    cleared = await backend_a.clear_session_if_stale(ttl_seconds=7200)
    assert cleared is True

    # Task B's session is untouched
    assert await backend_b.read_session_id() == "fresh-b"
