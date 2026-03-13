"""Tests for AsyncReputationEngine DB persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.reputation.engine import (
    AsyncReputationEngine,
    InMemoryReputationEngine,
    clear,
)
from src.reputation.models import WeightQuery, WeightUpdate


@pytest.fixture(autouse=True)
def _clean_state():
    """Reset module-level caches before each test."""
    clear()
    yield
    clear()


def _make_session() -> AsyncMock:
    """Create a mock AsyncSession."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


def _make_update(
    expert_id=None,
    context_key="repo:risk:band",
) -> WeightUpdate:
    return WeightUpdate(
        expert_id=expert_id or uuid4(),
        expert_version=1,
        context_key=context_key,
        normalized_weight=0.8,
        timestamp=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_write_read_roundtrip():
    """Update weight persistently, verify result fields."""
    engine = AsyncReputationEngine()
    session = _make_session()
    update = _make_update()

    result = await engine.update_weight_persistent(update, session)

    assert result.expert_id == update.expert_id
    assert result.context_key == update.context_key
    assert result.sample_count == 1
    assert result.weight > 0.0
    assert result.confidence > 0.0
    session.add.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_cache_hit_avoids_db():
    """After update, get_weight_persistent uses cache, not DB."""
    engine = AsyncReputationEngine()
    session = _make_session()
    update = _make_update()

    await engine.update_weight_persistent(update, session)

    # Reset mock call counts
    session.get.reset_mock()

    result = await engine.get_weight_persistent(update.expert_id, update.context_key, session)

    assert result is not None
    assert result.expert_id == update.expert_id
    session.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_clear_resets_state():
    """After clear(), get_weight returns None from cache."""
    sync = InMemoryReputationEngine()
    engine = AsyncReputationEngine(sync_engine=sync)
    session = _make_session()
    update = _make_update()

    await engine.update_weight_persistent(update, session)
    engine.clear()

    cached = sync.get_weight(update.expert_id, update.context_key)
    assert cached is None


@pytest.mark.asyncio
async def test_query_weights_cache_first():
    """query_weights_persistent returns cached data without DB query."""
    engine = AsyncReputationEngine()
    session = _make_session()
    update = _make_update()

    await engine.update_weight_persistent(update, session)

    # Reset mock to track subsequent calls
    session.execute.reset_mock()

    query = WeightQuery(expert_id=update.expert_id)
    results = await engine.query_weights_persistent(query, session)

    assert len(results) == 1
    assert results[0].expert_id == update.expert_id
    session.execute.assert_not_awaited()
