"""Tests for src/dashboard/reputation_router.py and reputation_queries.py.

Covers:
- GET /reputation/experts   — happy path, empty state
- GET /reputation/experts/{id} — happy path, 404 for unknown expert
- GET /reputation/outcomes  — happy path, empty state, limit param
- GET /reputation/drift     — insufficient_data state, happy path with alerts
- GET /reputation/summary   — happy path, empty data fallback

All tests mock the AsyncSession so no real database is required.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.app import app
from src.db.connection import get_session

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE = "http://test"
_PATH = "/api/v1/dashboard/reputation"


# ---------------------------------------------------------------------------
# Session mock helpers
# ---------------------------------------------------------------------------


def _make_session(*result_mocks: MagicMock) -> AsyncMock:
    """Return a session mock whose ``execute`` calls return ``result_mocks`` in order."""
    session = AsyncMock()
    session.add = MagicMock()
    if len(result_mocks) == 1:
        session.execute.return_value = result_mocks[0]
    else:
        session.execute.side_effect = list(result_mocks)
    return session


def _row(**kwargs: object) -> MagicMock:
    """Build a MagicMock row with the given attributes."""
    row = MagicMock()
    for k, v in kwargs.items():
        setattr(row, k, v)
    return row


def _result(rows: list[MagicMock] | MagicMock) -> MagicMock:
    """Wrap rows in a result mock for session.execute return value."""
    result = MagicMock()
    if isinstance(rows, list):
        result.fetchall.return_value = rows
        result.fetchone.return_value = rows[0] if rows else None
    else:
        result.fetchone.return_value = rows
        result.fetchall.return_value = [rows]
    return result


# ---------------------------------------------------------------------------
# /experts
# ---------------------------------------------------------------------------


class TestGetExperts:
    @pytest.mark.asyncio
    async def test_experts_happy_path(self, no_dashboard_auth: None) -> None:
        """GET /experts returns list of expert rows."""
        now = datetime.now(UTC)
        row = _row(
            expert_id="abc12345-0000-0000-0000-000000000000",
            context_count=2,
            avg_weight=0.72,
            total_samples=15,
            avg_confidence=0.55,
            trust_tier="probation",
            drift_signal="stable",
            last_updated_at=now,
        )
        session = _make_session(_result([row]))

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=_BASE
        ) as client:
            with patch("src.dashboard.reputation_router.get_session", return_value=session):
                with patch("src.db.connection.get_session", return_value=session):
                    app.dependency_overrides[get_session] = lambda: session
                    resp = await client.get(f"{_PATH}/experts")
                    app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert "experts" in body
        assert len(body["experts"]) == 1
        exp = body["experts"][0]
        assert exp["expert_id"] == "abc12345-0000-0000-0000-000000000000"
        assert exp["trust_tier"] == "probation"
        assert exp["drift_signal"] == "stable"
        assert exp["context_count"] == 2
        assert exp["total_samples"] == 15

    @pytest.mark.asyncio
    async def test_experts_empty(self, no_dashboard_auth: None) -> None:
        """GET /experts returns empty list when no experts exist."""
        session = _make_session(_result([]))

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=_BASE
        ) as client:
            app.dependency_overrides[get_session] = lambda: session
            resp = await client.get(f"{_PATH}/experts")
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json() == {"experts": []}


# ---------------------------------------------------------------------------
# /experts/{expert_id}
# ---------------------------------------------------------------------------


class TestGetExpertDetail:
    @pytest.mark.asyncio
    async def test_expert_detail_happy_path(self, no_dashboard_auth: None) -> None:
        """GET /experts/{id} returns expert contexts with weight history."""
        now = datetime.now(UTC)
        eid = "abc12345-0000-0000-0000-000000000000"
        row = _row(
            expert_id=eid,
            context_key="owner/repo:low:small",
            weight=0.68,
            sample_count=10,
            confidence=0.5,
            trust_tier="probation",
            drift_signal="improving",
            weight_history=[0.5, 0.55, 0.62, 0.68],
            last_updated_at=now,
        )
        session = _make_session(_result([row]))

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=_BASE
        ) as client:
            app.dependency_overrides[get_session] = lambda: session
            resp = await client.get(f"{_PATH}/experts/{eid}")
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert body["expert_id"] == eid
        assert len(body["contexts"]) == 1
        ctx = body["contexts"][0]
        assert ctx["context_key"] == "owner/repo:low:small"
        assert ctx["drift_signal"] == "improving"
        assert ctx["weight_history"] == [0.5, 0.55, 0.62, 0.68]

    @pytest.mark.asyncio
    async def test_expert_detail_404(self, no_dashboard_auth: None) -> None:
        """GET /experts/{id} returns 404 for unknown expert_id."""
        session = _make_session(_result([]))

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=_BASE
        ) as client:
            app.dependency_overrides[get_session] = lambda: session
            resp = await client.get(f"{_PATH}/experts/nonexistent-id")
            app.dependency_overrides.clear()

        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# /outcomes
# ---------------------------------------------------------------------------


class TestGetOutcomes:
    @pytest.mark.asyncio
    async def test_outcomes_happy_path(self, no_dashboard_auth: None) -> None:
        """GET /outcomes returns outcome entries with task context."""
        now = datetime.now(UTC)
        row = _row(
            id="sig-0001-0000-0000-0000-000000000001",
            task_id="task-0001-0000-0000-0000-000000000001",
            signal_type="qa_passed",
            outcome_type="success",
            signal_at=now,
            issue_id=42,
            repo="owner/repo",
            task_status="published",
            payload={},
        )
        count_row = _row(total=1)
        session = _make_session(_result([row]), _result(count_row))

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=_BASE
        ) as client:
            app.dependency_overrides[get_session] = lambda: session
            resp = await client.get(f"{_PATH}/outcomes")
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert "outcomes" in body
        assert "total" in body
        assert body["total"] == 1
        entry = body["outcomes"][0]
        assert entry["signal_type"] == "qa_passed"
        assert entry["outcome_type"] == "success"
        assert entry["issue_id"] == 42

    @pytest.mark.asyncio
    async def test_outcomes_empty(self, no_dashboard_auth: None) -> None:
        """GET /outcomes returns empty list when no signals exist."""
        count_row = _row(total=0)
        session = _make_session(_result([]), _result(count_row))

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=_BASE
        ) as client:
            app.dependency_overrides[get_session] = lambda: session
            resp = await client.get(f"{_PATH}/outcomes")
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert body["outcomes"] == []
        assert body["total"] == 0

    @pytest.mark.asyncio
    async def test_outcomes_limit_param(self, no_dashboard_auth: None) -> None:
        """GET /outcomes?limit=10 passes limit to query."""
        count_row = _row(total=0)
        session = _make_session(_result([]), _result(count_row))

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=_BASE
        ) as client:
            app.dependency_overrides[get_session] = lambda: session
            resp = await client.get(f"{_PATH}/outcomes?limit=10")
            app.dependency_overrides.clear()

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_outcomes_limit_validation(self, no_dashboard_auth: None) -> None:
        """GET /outcomes?limit=0 is rejected (ge=1)."""
        session = AsyncMock()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=_BASE
        ) as client:
            app.dependency_overrides[get_session] = lambda: session
            resp = await client.get(f"{_PATH}/outcomes?limit=0")
            app.dependency_overrides.clear()

        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /drift
# ---------------------------------------------------------------------------


class TestGetDrift:
    @pytest.mark.asyncio
    async def test_drift_insufficient_data(self, no_dashboard_auth: None) -> None:
        """GET /drift returns insufficient_data when task count < 20."""
        # Only the task count query runs when data is insufficient
        count_row = _row(cnt=5)
        session = _make_session(_result(count_row))

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=_BASE
        ) as client:
            app.dependency_overrides[get_session] = lambda: session
            resp = await client.get(f"{_PATH}/drift")
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert body["insufficient_data"] is True
        assert body["alerts"] == []
        assert body["drift_score"] == "low"
        assert body["task_count"] == 5

    @pytest.mark.asyncio
    async def test_drift_happy_path_no_alerts(self, no_dashboard_auth: None) -> None:
        """GET /drift returns low drift when all metrics are within bounds."""
        # Sufficient tasks
        count_row = _row(cnt=25)
        # Gate pass rate: stable (0% change)
        gate_row = _row(cur_pass_rate=0.85, prev_pass_rate=0.85)
        # Expert weights: no declining fraction
        expert_row = _row(avg_weight=0.72, declining_count=0, total_experts=5)
        # Cost: no significant change
        cost_row = _row(cur_cost=10.0, prev_cost=9.5)
        # Loopback: no significant change
        loopback_row = _row(cur_loopbacks=0.3, prev_loopbacks=0.3)

        session = _make_session(
            _result(count_row),
            _result(gate_row),
            _result(expert_row),
            _result(cost_row),
            _result(loopback_row),
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=_BASE
        ) as client:
            app.dependency_overrides[get_session] = lambda: session
            resp = await client.get(f"{_PATH}/drift")
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert body["insufficient_data"] is False
        assert body["drift_score"] == "low"
        assert body["alerts"] == []


# ---------------------------------------------------------------------------
# /summary
# ---------------------------------------------------------------------------


class TestGetReputationSummary:
    @pytest.mark.asyncio
    async def test_summary_shape(self, no_dashboard_auth: None) -> None:
        """GET /summary returns four summary cards with trend indicators."""
        # We patch query_drift to avoid complex multi-query session setup
        summary_row = _row(
            cur_qa_passed=8.0,
            cur_qa_total=10.0,
            prev_qa_passed=7.0,
            prev_qa_total=10.0,
            cur_avg_loopbacks=0.5,
            prev_avg_loopbacks=0.4,
            cur_merged=4,
            cur_published=5,
            prev_merged=3,
            prev_published=5,
        )
        session = _make_session(_result(summary_row))

        drift_data = {
            "window_days": 14,
            "drift_score": "low",
            "composite_score": 0.0,
            "alerts": [],
            "insufficient_data": True,
            "task_count": 0,
            "min_tasks_required": 20,
        }

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=_BASE
        ) as client:
            app.dependency_overrides[get_session] = lambda: session
            with patch(
                "src.dashboard.reputation_queries.query_drift",
                AsyncMock(return_value=drift_data),
            ):
                resp = await client.get(f"{_PATH}/summary")
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        cards = body["cards"]
        assert "success_rate" in cards
        assert "avg_loopbacks" in cards
        assert "pr_merge_rate" in cards
        assert "drift_score" in cards

        # Verify trend calculations
        assert cards["success_rate"]["trend"] == "up"   # 0.8 > 0.7
        assert cards["avg_loopbacks"]["trend"] == "up"  # 0.5 > 0.4
        assert cards["pr_merge_rate"]["trend"] == "up"  # 0.8 > 0.6
        assert cards["drift_score"]["value"] == "low"

    @pytest.mark.asyncio
    async def test_summary_empty_data_fallback(self, no_dashboard_auth: None) -> None:
        """GET /summary returns zeroed cards when no data is available."""
        session = _make_session(_result(None))

        drift_data = {
            "window_days": 14,
            "drift_score": "low",
            "composite_score": 0.0,
            "alerts": [],
            "insufficient_data": True,
            "task_count": 0,
            "min_tasks_required": 20,
        }

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=_BASE
        ) as client:
            app.dependency_overrides[get_session] = lambda: session
            with patch(
                "src.dashboard.reputation_queries.query_drift",
                AsyncMock(return_value=drift_data),
            ):
                resp = await client.get(f"{_PATH}/summary")
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        body = resp.json()
        assert body["cards"]["success_rate"]["value"] == 0.0
        assert body["cards"]["drift_score"]["value"] == "low"
