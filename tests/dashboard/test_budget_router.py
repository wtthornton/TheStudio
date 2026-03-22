"""Tests for src/dashboard/budget_router.py.

Covers:
- GET /budget/summary      — window_hours default and custom, response shape
- GET /budget/history      — time-series buckets, response shape
- GET /budget/by-stage     — by_stage aggregation, response shape
- GET /budget/by-model     — by_model aggregation, response shape
- GET /budget/config       — returns singleton config (creates defaults if absent)
- PUT /budget/config       — partial update, persists only supplied fields
- ``window_hours`` query param validation (ge=1, le=8760)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.app import app
from src.dashboard.models.budget_config import BudgetConfigRead
from src.db.connection import get_session

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE = "http://test"
_PATH = "/api/v1/dashboard/budget"


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _make_spend_summary(key: str = "claude-3-5-sonnet", cost: float = 0.05) -> MagicMock:
    """Return a minimal SpendSummary mock with a to_dict() implementation."""
    s = MagicMock()
    s.key = key
    s.to_dict.return_value = {
        "key": key,
        "total_cost": round(cost, 6),
        "total_tokens_in": 1000,
        "total_tokens_out": 200,
        "total_tokens": 1200,
        "call_count": 3,
        "avg_latency_ms": 450.0,
        "error_count": 0,
    }
    return s


def _make_spend_report(
    *,
    total_cost: float = 0.15,
    total_calls: int = 5,
    window_hours: int = 24,
    by_day: list[Any] | None = None,
    by_model: list[Any] | None = None,
    by_step: list[Any] | None = None,
    total_cache_creation_tokens: int = 500,
    total_cache_read_tokens: int = 100,
    cache_hit_rate: float = 0.1667,
) -> MagicMock:
    """Return a minimal SpendReport mock."""
    report = MagicMock()
    report.total_cost = total_cost
    report.total_calls = total_calls
    report.window_hours = window_hours
    report.by_day = by_day if by_day is not None else [_make_spend_summary("2026-03-22")]
    report.by_model = by_model if by_model is not None else [_make_spend_summary()]
    report.by_step = by_step if by_step is not None else [_make_spend_summary("agent")]
    report.total_cache_creation_tokens = total_cache_creation_tokens
    report.total_cache_read_tokens = total_cache_read_tokens
    report.cache_hit_rate = cache_hit_rate
    return report


def _make_budget_config_read(**overrides: Any) -> BudgetConfigRead:
    """Return a BudgetConfigRead instance with sensible defaults."""
    defaults: dict[str, Any] = {
        "daily_spend_warning": None,
        "weekly_budget_cap": None,
        "per_task_warning": None,
        "pause_on_budget_exceeded": False,
        "model_downgrade_on_approach": False,
        "downgrade_threshold_percent": 80.0,
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return BudgetConfigRead(**defaults)


def _mock_session() -> AsyncMock:
    """Return a mocked AsyncSession with session.begin() configured as async CM."""
    session = AsyncMock()
    session.add = MagicMock()

    # session.begin() must work as an async context manager.
    # MagicMock provides __aenter__/__aexit__ as AsyncMocks automatically, but
    # we configure explicitly to be safe.
    begin_cm = MagicMock()
    begin_cm.__aenter__ = AsyncMock(return_value=None)
    begin_cm.__aexit__ = AsyncMock(return_value=False)
    session.begin = MagicMock(return_value=begin_cm)

    return session


# ===========================================================================
# GET /budget/summary
# ===========================================================================


@pytest.mark.asyncio
async def test_summary_default_window(no_dashboard_auth: None) -> None:
    """Default window_hours=24; response contains expected keys."""
    report = _make_spend_report(window_hours=24)

    with patch("src.dashboard.budget_router.get_spend_report", return_value=report):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(f"{_PATH}/summary")

    assert resp.status_code == 200
    body = resp.json()
    assert body["window_hours"] == 24
    assert body["total_cost"] == round(report.total_cost, 6)
    assert body["total_calls"] == report.total_calls
    assert "total_cache_creation_tokens" in body
    assert "total_cache_read_tokens" in body
    assert "cache_hit_rate" in body


@pytest.mark.asyncio
async def test_summary_custom_window(no_dashboard_auth: None) -> None:
    """Custom window_hours is forwarded to get_spend_report."""
    report = _make_spend_report(window_hours=48)

    with patch("src.dashboard.budget_router.get_spend_report", return_value=report) as mock_fn:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(f"{_PATH}/summary?window_hours=48")

    assert resp.status_code == 200
    mock_fn.assert_called_once_with(window_hours=48)


@pytest.mark.asyncio
async def test_summary_window_too_small_rejected(no_dashboard_auth: None) -> None:
    """window_hours < 1 is rejected with 422."""
    with patch("src.dashboard.budget_router.get_spend_report"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(f"{_PATH}/summary?window_hours=0")

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_summary_window_too_large_rejected(no_dashboard_auth: None) -> None:
    """window_hours > 8760 is rejected with 422."""
    with patch("src.dashboard.budget_router.get_spend_report"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(f"{_PATH}/summary?window_hours=9000")

    assert resp.status_code == 422


# ===========================================================================
# GET /budget/history
# ===========================================================================


@pytest.mark.asyncio
async def test_history_default_window(no_dashboard_auth: None) -> None:
    """Default window_hours=168 (7 days); response includes by_day and by_model."""
    report = _make_spend_report(window_hours=168)

    with patch("src.dashboard.budget_router.get_spend_report", return_value=report):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(f"{_PATH}/history")

    assert resp.status_code == 200
    body = resp.json()
    assert body["window_hours"] == 168
    assert "by_day" in body
    assert "by_model" in body
    assert isinstance(body["by_day"], list)
    assert isinstance(body["by_model"], list)


@pytest.mark.asyncio
async def test_history_custom_window(no_dashboard_auth: None) -> None:
    """Custom window_hours forwarded to get_spend_report."""
    report = _make_spend_report(window_hours=72)

    with patch("src.dashboard.budget_router.get_spend_report", return_value=report) as mock_fn:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(f"{_PATH}/history?window_hours=72")

    assert resp.status_code == 200
    mock_fn.assert_called_once_with(window_hours=72)


@pytest.mark.asyncio
async def test_history_window_validation(no_dashboard_auth: None) -> None:
    """window_hours=0 rejected; window_hours=8760 accepted; window_hours=8761 rejected."""
    with patch("src.dashboard.budget_router.get_spend_report", return_value=_make_spend_report(window_hours=8760)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            r_low = await client.get(f"{_PATH}/history?window_hours=0")
            r_max = await client.get(f"{_PATH}/history?window_hours=8760")
            r_over = await client.get(f"{_PATH}/history?window_hours=8761")

    assert r_low.status_code == 422
    assert r_max.status_code == 200
    assert r_over.status_code == 422


# ===========================================================================
# GET /budget/by-stage
# ===========================================================================


@pytest.mark.asyncio
async def test_by_stage_response_shape(no_dashboard_auth: None) -> None:
    """by_stage list comes from report.by_step; response includes total_cost/calls."""
    stage_summary = _make_spend_summary("agent", cost=0.08)
    report = _make_spend_report(by_step=[stage_summary], total_cost=0.08, total_calls=2)

    with patch("src.dashboard.budget_router.get_spend_report", return_value=report):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(f"{_PATH}/by-stage")

    assert resp.status_code == 200
    body = resp.json()
    assert body["window_hours"] == 24
    assert "by_stage" in body
    assert len(body["by_stage"]) == 1
    assert body["by_stage"][0]["key"] == "agent"


@pytest.mark.asyncio
async def test_by_stage_window_validation(no_dashboard_auth: None) -> None:
    """Invalid window_hours rejected with 422."""
    with patch("src.dashboard.budget_router.get_spend_report"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(f"{_PATH}/by-stage?window_hours=-1")

    assert resp.status_code == 422


# ===========================================================================
# GET /budget/by-model
# ===========================================================================


@pytest.mark.asyncio
async def test_by_model_response_shape(no_dashboard_auth: None) -> None:
    """by_model list contains per-model breakdown entries."""
    model_summary = _make_spend_summary("claude-3-5-haiku", cost=0.02)
    report = _make_spend_report(by_model=[model_summary], total_cost=0.02, total_calls=1)

    with patch("src.dashboard.budget_router.get_spend_report", return_value=report):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(f"{_PATH}/by-model")

    assert resp.status_code == 200
    body = resp.json()
    assert "by_model" in body
    assert len(body["by_model"]) == 1
    assert body["by_model"][0]["key"] == "claude-3-5-haiku"


@pytest.mark.asyncio
async def test_by_model_custom_window(no_dashboard_auth: None) -> None:
    """Custom window_hours forwarded to get_spend_report."""
    report = _make_spend_report(window_hours=12)

    with patch("src.dashboard.budget_router.get_spend_report", return_value=report) as mock_fn:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.get(f"{_PATH}/by-model?window_hours=12")

    assert resp.status_code == 200
    mock_fn.assert_called_once_with(window_hours=12)


@pytest.mark.asyncio
async def test_by_model_window_validation(no_dashboard_auth: None) -> None:
    """window_hours out of bounds rejected."""
    with patch("src.dashboard.budget_router.get_spend_report"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            r_low = await client.get(f"{_PATH}/by-model?window_hours=0")
            r_over = await client.get(f"{_PATH}/by-model?window_hours=10000")

    assert r_low.status_code == 422
    assert r_over.status_code == 422


# ===========================================================================
# GET /budget/config
# ===========================================================================


@pytest.mark.asyncio
async def test_get_config_returns_defaults(no_dashboard_auth: None) -> None:
    """GET /budget/config returns BudgetConfigRead with all expected fields."""
    cfg = _make_budget_config_read()
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.budget_router.get_budget_config", AsyncMock(return_value=cfg)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.get(f"{_PATH}/config")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["pause_on_budget_exceeded"] is False
    assert body["model_downgrade_on_approach"] is False
    assert body["downgrade_threshold_percent"] == 80.0
    assert body["daily_spend_warning"] is None
    assert body["weekly_budget_cap"] is None
    assert body["per_task_warning"] is None
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_get_config_returns_configured_values(no_dashboard_auth: None) -> None:
    """GET /budget/config reflects previously stored non-default values."""
    cfg = _make_budget_config_read(
        daily_spend_warning=10.0,
        weekly_budget_cap=50.0,
        per_task_warning=5.0,
        pause_on_budget_exceeded=True,
        model_downgrade_on_approach=True,
        downgrade_threshold_percent=75.0,
    )
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.budget_router.get_budget_config", AsyncMock(return_value=cfg)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.get(f"{_PATH}/config")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["daily_spend_warning"] == 10.0
    assert body["weekly_budget_cap"] == 50.0
    assert body["per_task_warning"] == 5.0
    assert body["pause_on_budget_exceeded"] is True
    assert body["downgrade_threshold_percent"] == 75.0


# ===========================================================================
# PUT /budget/config
# ===========================================================================


@pytest.mark.asyncio
async def test_put_config_partial_update(no_dashboard_auth: None) -> None:
    """PUT /budget/config updates only supplied fields, returns updated config."""
    updated_cfg = _make_budget_config_read(
        weekly_budget_cap=100.0,
        pause_on_budget_exceeded=True,
        downgrade_threshold_percent=80.0,
    )
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(
            "src.dashboard.budget_router.update_budget_config",
            AsyncMock(return_value=updated_cfg),
        ) as mock_update:
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.put(
                    f"{_PATH}/config",
                    json={"weekly_budget_cap": 100.0, "pause_on_budget_exceeded": True},
                )
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["weekly_budget_cap"] == 100.0
    assert body["pause_on_budget_exceeded"] is True
    mock_update.assert_awaited_once()


@pytest.mark.asyncio
async def test_put_config_all_fields(no_dashboard_auth: None) -> None:
    """PUT /budget/config accepts all valid fields simultaneously."""
    now = datetime.now(UTC)
    updated_cfg = _make_budget_config_read(
        daily_spend_warning=20.0,
        weekly_budget_cap=200.0,
        per_task_warning=10.0,
        pause_on_budget_exceeded=True,
        model_downgrade_on_approach=True,
        downgrade_threshold_percent=90.0,
        updated_at=now,
    )
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(
            "src.dashboard.budget_router.update_budget_config",
            AsyncMock(return_value=updated_cfg),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.put(
                    f"{_PATH}/config",
                    json={
                        "daily_spend_warning": 20.0,
                        "weekly_budget_cap": 200.0,
                        "per_task_warning": 10.0,
                        "pause_on_budget_exceeded": True,
                        "model_downgrade_on_approach": True,
                        "downgrade_threshold_percent": 90.0,
                    },
                )
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    body = resp.json()
    assert body["downgrade_threshold_percent"] == 90.0
    assert body["model_downgrade_on_approach"] is True


@pytest.mark.asyncio
async def test_put_config_empty_body_accepted(no_dashboard_auth: None) -> None:
    """PUT with empty JSON body is accepted (all fields optional, no-op update)."""
    cfg = _make_budget_config_read()
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(
            "src.dashboard.budget_router.update_budget_config",
            AsyncMock(return_value=cfg),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.put(f"{_PATH}/config", json={})
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_put_config_negative_cap_rejected(no_dashboard_auth: None) -> None:
    """Negative weekly_budget_cap is rejected by Pydantic ge=0 constraint."""
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.budget_router.update_budget_config"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.put(f"{_PATH}/config", json={"weekly_budget_cap": -1.0})
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_put_config_downgrade_threshold_out_of_range(no_dashboard_auth: None) -> None:
    """downgrade_threshold_percent > 100 is rejected by Pydantic le=100 constraint."""
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.budget_router.update_budget_config"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.put(f"{_PATH}/config", json={"downgrade_threshold_percent": 101.0})
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 422
