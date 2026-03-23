"""Unit tests for auto-merge dashboard API endpoints (Epic 42 Story 42.13).

Covers:
(g) /auto-merge/outcomes returns correct data
(g) /auto-merge/rule-health returns correct data
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.dashboard.auto_merge_router import router as auto_merge_router

# ---------------------------------------------------------------------------
# Test app setup
# ---------------------------------------------------------------------------


def _make_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(auto_merge_router)
    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_outcome_read(**overrides):
    """Return a mock AutoMergeOutcomeRead-like object."""
    from src.dashboard.models.auto_merge_outcomes import AutoMergeOutcomeRead

    now = datetime.now(UTC)
    data = {
        "id": uuid4(),
        "taskpacket_id": uuid4(),
        "rule_id": uuid4(),
        "pr_number": 42,
        "repo": "owner/repo",
        "merged_at": now,
        "outcome": "succeeded",
        "detected_at": now,
        "revert_sha": None,
        "linked_issue_number": None,
        "notes": None,
        "created_at": now,
    }
    data.update(overrides)
    return AutoMergeOutcomeRead(**data)


# ---------------------------------------------------------------------------
# GET /auto-merge/outcomes tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_outcomes_endpoint_returns_list():
    """GET /auto-merge/outcomes returns outcomes list with correct shape."""
    outcome1 = _make_outcome_read(outcome="succeeded")
    outcome2 = _make_outcome_read(outcome="reverted", revert_sha="abc123")

    with patch(
        "src.dashboard.auto_merge_router.list_outcomes",
        new_callable=AsyncMock,
        return_value=[outcome1, outcome2],
    ):
        app = _make_test_app()

        async def override_session():
            return AsyncMock()

        from src.db.connection import get_session
        app.dependency_overrides[get_session] = override_session

        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/auto-merge/outcomes?period=7d")

    assert response.status_code == 200
    data = response.json()
    assert data["period"] == "7d"
    assert data["count"] == 2
    outcomes = data["outcomes"]
    assert len(outcomes) == 2
    assert outcomes[0]["outcome"] == "succeeded"
    assert outcomes[1]["outcome"] == "reverted"
    assert outcomes[1]["revert_sha"] == "abc123"


@pytest.mark.asyncio
async def test_outcomes_endpoint_empty_list():
    """GET /auto-merge/outcomes returns empty list when no outcomes exist."""
    with patch(
        "src.dashboard.auto_merge_router.list_outcomes",
        new_callable=AsyncMock,
        return_value=[],
    ):
        app = _make_test_app()

        async def override_session():
            return AsyncMock()

        from src.db.connection import get_session
        app.dependency_overrides[get_session] = override_session

        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/auto-merge/outcomes?period=1d")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["outcomes"] == []


@pytest.mark.asyncio
async def test_outcomes_endpoint_period_mapping():
    """GET /auto-merge/outcomes accepts all valid period values."""
    with patch(
        "src.dashboard.auto_merge_router.list_outcomes",
        new_callable=AsyncMock,
        return_value=[],
    ):
        app = _make_test_app()

        async def override_session():
            return AsyncMock()

        from src.db.connection import get_session
        app.dependency_overrides[get_session] = override_session

        client = TestClient(app)
        for period in ["1d", "7d", "30d"]:
            response = client.get(f"/auto-merge/outcomes?period={period}")
            assert response.status_code == 200, f"period={period} failed"


# ---------------------------------------------------------------------------
# GET /auto-merge/rule-health tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rule_health_endpoint_returns_summary():
    """GET /auto-merge/rule-health returns per-rule health metrics."""
    mock_summary = [
        {
            "rule_id": str(uuid4()),
            "priority": 10,
            "description": "Execute safe bug fixes",
            "active": True,
            "dry_run": False,
            "merge_count": 20,
            "revert_count": 1,
            "success_rate": 95.0,
            "deactivation_reason": None,
            "sample_warning": False,
        }
    ]

    with patch(
        "src.dashboard.auto_merge_router.get_rule_health_summary",
        new_callable=AsyncMock,
        return_value=mock_summary,
    ):
        app = _make_test_app()

        async def override_session():
            return AsyncMock()

        from src.db.connection import get_session
        app.dependency_overrides[get_session] = override_session

        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/auto-merge/rule-health")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert data["threshold_pct"] == 90
    assert data["min_samples"] == 20
    rules = data["rules"]
    assert len(rules) == 1
    assert rules[0]["success_rate"] == 95.0
    assert rules[0]["sample_warning"] is False


@pytest.mark.asyncio
async def test_rule_health_endpoint_deactivated_rule():
    """GET /auto-merge/rule-health shows deactivation reason for inactive rules."""
    mock_summary = [
        {
            "rule_id": str(uuid4()),
            "priority": 5,
            "description": "Risky rule",
            "active": False,
            "dry_run": False,
            "merge_count": 21,
            "revert_count": 3,
            "success_rate": 85.7,
            "deactivation_reason": "auto: success rate 85.7% below threshold 90%",
            "sample_warning": False,
        }
    ]

    with patch(
        "src.dashboard.auto_merge_router.get_rule_health_summary",
        new_callable=AsyncMock,
        return_value=mock_summary,
    ):
        app = _make_test_app()

        async def override_session():
            return AsyncMock()

        from src.db.connection import get_session
        app.dependency_overrides[get_session] = override_session

        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/auto-merge/rule-health")

    assert response.status_code == 200
    data = response.json()
    rule = data["rules"][0]
    assert rule["active"] is False
    assert "85.7" in rule["deactivation_reason"]


@pytest.mark.asyncio
async def test_rule_health_endpoint_empty():
    """GET /auto-merge/rule-health returns empty list when no Execute rules exist."""
    with patch(
        "src.dashboard.auto_merge_router.get_rule_health_summary",
        new_callable=AsyncMock,
        return_value=[],
    ):
        app = _make_test_app()

        async def override_session():
            return AsyncMock()

        from src.db.connection import get_session
        app.dependency_overrides[get_session] = override_session

        client = TestClient(app, raise_server_exceptions=True)
        response = client.get("/auto-merge/rule-health")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["rules"] == []
