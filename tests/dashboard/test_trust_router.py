"""Tests for the trust tier configuration API (src/dashboard/trust_router.py).

Covers:
- GET  /trust/rules                — list all rules, active_only filter
- POST /trust/rules                — create rule (happy path + 422 validation)
- GET  /trust/rules/{rule_id}      — get rule (200 + 404)
- PUT  /trust/rules/{rule_id}      — update rule (200 + 404 + 422)
- DELETE /trust/rules/{rule_id}    — delete rule (204 + 404)
- GET  /trust/safety-bounds        — get safety bounds
- PUT  /trust/safety-bounds        — update safety bounds
- GET  /trust/default-tier         — get default tier
- PUT  /trust/default-tier         — set default tier
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.app import app
from src.dashboard.models.trust_config import (
    AssignedTier,
    ConditionOperator,
    DefaultTierRead,
    RuleCondition,
    SafeBoundsRead,
    TrustTierRuleRead,
)
from src.db.connection import get_session

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE = "http://test"
_PATH = "/api/v1/dashboard/trust"

# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

_NOW = datetime.now(UTC)


def _make_rule(
    *,
    priority: int = 100,
    assigned_tier: AssignedTier = AssignedTier.OBSERVE,
    active: bool = True,
    description: str | None = "test rule",
    conditions: list[RuleCondition] | None = None,
) -> TrustTierRuleRead:
    return TrustTierRuleRead(
        id=uuid4(),
        priority=priority,
        conditions=conditions or [],
        assigned_tier=assigned_tier,
        active=active,
        description=description,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _make_bounds(
    *,
    max_auto_merge_lines: int | None = 500,
    max_auto_merge_cost: int | None = 500,
    max_loopbacks: int | None = 3,
    mandatory_review_patterns: list[str] | None = None,
) -> SafeBoundsRead:
    return SafeBoundsRead(
        max_auto_merge_lines=max_auto_merge_lines,
        max_auto_merge_cost=max_auto_merge_cost,
        max_loopbacks=max_loopbacks,
        mandatory_review_patterns=mandatory_review_patterns or ["**/migrations/**"],
        updated_at=_NOW,
    )


def _make_default_tier(tier: AssignedTier = AssignedTier.OBSERVE) -> DefaultTierRead:
    return DefaultTierRead(default_tier=tier, updated_at=_NOW)


def _mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    return session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CRUD_PREFIX = "src.dashboard.trust_router"


# ===========================================================================
# GET /trust/rules
# ===========================================================================


@pytest.mark.asyncio
async def test_list_rules_returns_empty(no_dashboard_auth: None) -> None:
    """Empty DB → 200 with empty list."""
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.list_rules", AsyncMock(return_value=[])):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.get(f"{_PATH}/rules")
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_list_rules_returns_items(no_dashboard_auth: None) -> None:
    """DB has two rules → 200 with both items."""
    rules = [_make_rule(priority=10), _make_rule(priority=20)]
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.list_rules", AsyncMock(return_value=rules)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.get(f"{_PATH}/rules")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        assert body[0]["priority"] == 10
        assert body[1]["priority"] == 20
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_list_rules_active_only_filter(no_dashboard_auth: None) -> None:
    """active_only=true → list_rules called with active_only=True."""
    active_rule = _make_rule(active=True)
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    mock_list = AsyncMock(return_value=[active_rule])
    try:
        with patch(f"{_CRUD_PREFIX}.list_rules", mock_list):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.get(f"{_PATH}/rules", params={"active_only": "true"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        # Verify the CRUD function received active_only=True
        _call_kwargs = mock_list.call_args
        assert _call_kwargs.kwargs.get("active_only") is True or (
            len(_call_kwargs.args) > 1 and _call_kwargs.args[1] is True
        )
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_list_rules_active_only_false_by_default(no_dashboard_auth: None) -> None:
    """active_only defaults to False when not supplied."""
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    mock_list = AsyncMock(return_value=[])
    try:
        with patch(f"{_CRUD_PREFIX}.list_rules", mock_list):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                await client.get(f"{_PATH}/rules")
        _call_kwargs = mock_list.call_args
        assert _call_kwargs.kwargs.get("active_only") is False or (
            len(_call_kwargs.args) > 1 and _call_kwargs.args[1] is False
        )
    finally:
        app.dependency_overrides.pop(get_session, None)


# ===========================================================================
# POST /trust/rules
# ===========================================================================


@pytest.mark.asyncio
async def test_create_rule_happy_path(no_dashboard_auth: None) -> None:
    """Valid payload → 201 with rule body."""
    rule = _make_rule(priority=50, assigned_tier=AssignedTier.SUGGEST)
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.create_rule", AsyncMock(return_value=rule)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(
                    f"{_PATH}/rules",
                    json={
                        "priority": 50,
                        "assigned_tier": "suggest",
                        "active": True,
                        "conditions": [],
                        "description": "created rule",
                    },
                )
        assert resp.status_code == 201
        body = resp.json()
        assert body["priority"] == 50
        assert body["assigned_tier"] == "suggest"
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_create_rule_with_conditions(no_dashboard_auth: None) -> None:
    """Payload with conditions list is accepted."""
    condition = RuleCondition(field="complexity_index", op=ConditionOperator.GREATER_THAN, value=0.8)
    rule = _make_rule(conditions=[condition])
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.create_rule", AsyncMock(return_value=rule)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(
                    f"{_PATH}/rules",
                    json={
                        "priority": 100,
                        "assigned_tier": "observe",
                        "conditions": [
                            {"field": "complexity_index", "op": "greater_than", "value": 0.8}
                        ],
                    },
                )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["conditions"]) == 1
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_create_rule_missing_required_field_422(no_dashboard_auth: None) -> None:
    """Missing assigned_tier → 422 validation error."""
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.post(f"{_PATH}/rules", json={"priority": 50})
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_create_rule_invalid_priority_422(no_dashboard_auth: None) -> None:
    """priority=0 violates ge=1 constraint → 422."""
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.post(
                f"{_PATH}/rules",
                json={"priority": 0, "assigned_tier": "observe"},
            )
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.pop(get_session, None)


# ===========================================================================
# GET /trust/rules/{rule_id}
# ===========================================================================


@pytest.mark.asyncio
async def test_get_rule_happy_path(no_dashboard_auth: None) -> None:
    """Existing rule → 200."""
    rule = _make_rule()
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.get_rule", AsyncMock(return_value=rule)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.get(f"{_PATH}/rules/{rule.id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == str(rule.id)
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_get_rule_not_found_404(no_dashboard_auth: None) -> None:
    """Missing rule → 404."""
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.get_rule", AsyncMock(return_value=None)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.get(f"{_PATH}/rules/{uuid4()}")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_session, None)


# ===========================================================================
# PUT /trust/rules/{rule_id}
# ===========================================================================


@pytest.mark.asyncio
async def test_update_rule_happy_path(no_dashboard_auth: None) -> None:
    """Partial update → 200 with updated fields."""
    updated = _make_rule(priority=200, assigned_tier=AssignedTier.EXECUTE)
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.update_rule", AsyncMock(return_value=updated)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.put(
                    f"{_PATH}/rules/{updated.id}",
                    json={"priority": 200, "assigned_tier": "execute"},
                )
        assert resp.status_code == 200
        body = resp.json()
        assert body["priority"] == 200
        assert body["assigned_tier"] == "execute"
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_update_rule_not_found_404(no_dashboard_auth: None) -> None:
    """Missing rule → 404."""
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.update_rule", AsyncMock(return_value=None)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.put(
                    f"{_PATH}/rules/{uuid4()}",
                    json={"priority": 100},
                )
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_update_rule_empty_body_accepted(no_dashboard_auth: None) -> None:
    """Empty body is valid (all fields optional) → 200."""
    rule = _make_rule()
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.update_rule", AsyncMock(return_value=rule)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.put(f"{_PATH}/rules/{rule.id}", json={})
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.pop(get_session, None)


# ===========================================================================
# DELETE /trust/rules/{rule_id}
# ===========================================================================


@pytest.mark.asyncio
async def test_delete_rule_happy_path(no_dashboard_auth: None) -> None:
    """Existing rule → 204 with no body."""
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.delete_rule", AsyncMock(return_value=True)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.delete(f"{_PATH}/rules/{uuid4()}")
        assert resp.status_code == 204
        assert resp.content == b""
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_delete_rule_not_found_404(no_dashboard_auth: None) -> None:
    """Missing rule → 404."""
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.delete_rule", AsyncMock(return_value=False)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.delete(f"{_PATH}/rules/{uuid4()}")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_session, None)


# ===========================================================================
# GET /trust/safety-bounds
# ===========================================================================


@pytest.mark.asyncio
async def test_get_safety_bounds_returns_singleton(no_dashboard_auth: None) -> None:
    """GET safety bounds → 200 with SafeBoundsRead payload."""
    bounds = _make_bounds()
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.get_safety_bounds", AsyncMock(return_value=bounds)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.get(f"{_PATH}/safety-bounds")
        assert resp.status_code == 200
        body = resp.json()
        assert body["max_auto_merge_lines"] == 500
        assert body["max_auto_merge_cost"] == 500
        assert body["max_loopbacks"] == 3
        assert isinstance(body["mandatory_review_patterns"], list)
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_get_safety_bounds_null_fields(no_dashboard_auth: None) -> None:
    """Null limit fields are serialised correctly."""
    bounds = _make_bounds(max_auto_merge_lines=None, max_auto_merge_cost=None, max_loopbacks=None)
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.get_safety_bounds", AsyncMock(return_value=bounds)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.get(f"{_PATH}/safety-bounds")
        assert resp.status_code == 200
        body = resp.json()
        assert body["max_auto_merge_lines"] is None
        assert body["max_auto_merge_cost"] is None
        assert body["max_loopbacks"] is None
    finally:
        app.dependency_overrides.pop(get_session, None)


# ===========================================================================
# PUT /trust/safety-bounds
# ===========================================================================


@pytest.mark.asyncio
async def test_update_safety_bounds_happy_path(no_dashboard_auth: None) -> None:
    """Valid update payload → 200 with updated SafeBoundsRead."""
    updated = _make_bounds(max_auto_merge_lines=1000, max_auto_merge_cost=2000, max_loopbacks=5)
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.update_safety_bounds", AsyncMock(return_value=updated)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.put(
                    f"{_PATH}/safety-bounds",
                    json={
                        "max_auto_merge_lines": 1000,
                        "max_auto_merge_cost": 2000,
                        "max_loopbacks": 5,
                    },
                )
        assert resp.status_code == 200
        body = resp.json()
        assert body["max_auto_merge_lines"] == 1000
        assert body["max_auto_merge_cost"] == 2000
        assert body["max_loopbacks"] == 5
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_update_safety_bounds_partial(no_dashboard_auth: None) -> None:
    """Only max_loopbacks supplied → 200 (partial update)."""
    updated = _make_bounds(max_loopbacks=10)
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.update_safety_bounds", AsyncMock(return_value=updated)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.put(f"{_PATH}/safety-bounds", json={"max_loopbacks": 10})
        assert resp.status_code == 200
        assert resp.json()["max_loopbacks"] == 10
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_update_safety_bounds_invalid_value_422(no_dashboard_auth: None) -> None:
    """max_auto_merge_lines=0 violates ge=1 → 422."""
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.put(
                f"{_PATH}/safety-bounds",
                json={"max_auto_merge_lines": 0},
            )
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_update_safety_bounds_mandatory_patterns(no_dashboard_auth: None) -> None:
    """mandatory_review_patterns list is accepted and returned."""
    patterns = ["**/migrations/**", "src/settings.py"]
    updated = _make_bounds(mandatory_review_patterns=patterns)
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.update_safety_bounds", AsyncMock(return_value=updated)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.put(
                    f"{_PATH}/safety-bounds",
                    json={"mandatory_review_patterns": patterns},
                )
        assert resp.status_code == 200
        assert resp.json()["mandatory_review_patterns"] == patterns
    finally:
        app.dependency_overrides.pop(get_session, None)


# ===========================================================================
# GET /trust/default-tier
# ===========================================================================


@pytest.mark.asyncio
async def test_get_default_tier_returns_observe(no_dashboard_auth: None) -> None:
    """GET default-tier → 200, default is 'observe'."""
    default = _make_default_tier(AssignedTier.OBSERVE)
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.get_default_tier", AsyncMock(return_value=default)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.get(f"{_PATH}/default-tier")
        assert resp.status_code == 200
        body = resp.json()
        assert body["default_tier"] == "observe"
        assert "updated_at" in body
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_get_default_tier_suggest(no_dashboard_auth: None) -> None:
    """GET default-tier when tier is 'suggest' → returns 'suggest'."""
    default = _make_default_tier(AssignedTier.SUGGEST)
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.get_default_tier", AsyncMock(return_value=default)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.get(f"{_PATH}/default-tier")
        assert resp.status_code == 200
        assert resp.json()["default_tier"] == "suggest"
    finally:
        app.dependency_overrides.pop(get_session, None)


# ===========================================================================
# PUT /trust/default-tier
# ===========================================================================


@pytest.mark.asyncio
async def test_set_default_tier_happy_path(no_dashboard_auth: None) -> None:
    """PUT default-tier with 'execute' → 200 with updated tier."""
    updated = _make_default_tier(AssignedTier.EXECUTE)
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.update_default_tier", AsyncMock(return_value=updated)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.put(
                    f"{_PATH}/default-tier",
                    json={"default_tier": "execute"},
                )
        assert resp.status_code == 200
        assert resp.json()["default_tier"] == "execute"
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_set_default_tier_observe(no_dashboard_auth: None) -> None:
    """PUT default-tier with 'observe' → 200."""
    updated = _make_default_tier(AssignedTier.OBSERVE)
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.update_default_tier", AsyncMock(return_value=updated)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.put(
                    f"{_PATH}/default-tier",
                    json={"default_tier": "observe"},
                )
        assert resp.status_code == 200
        assert resp.json()["default_tier"] == "observe"
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_set_default_tier_invalid_value_422(no_dashboard_auth: None) -> None:
    """Unknown tier value → 422 validation error."""
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.put(
                f"{_PATH}/default-tier",
                json={"default_tier": "superuser"},
            )
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_set_default_tier_missing_field_422(no_dashboard_auth: None) -> None:
    """Missing default_tier field → 422."""
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
            resp = await client.put(f"{_PATH}/default-tier", json={})
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.pop(get_session, None)


# ===========================================================================
# Compound: all three tier values round-trip
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("tier", ["observe", "suggest", "execute"])
async def test_set_default_tier_all_values(no_dashboard_auth: None, tier: str) -> None:
    """Each valid tier value is accepted by PUT /trust/default-tier."""
    updated = _make_default_tier(AssignedTier(tier))
    session = _mock_session()
    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch(f"{_CRUD_PREFIX}.update_default_tier", AsyncMock(return_value=updated)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.put(f"{_PATH}/default-tier", json={"default_tier": tier})
        assert resp.status_code == 200
        assert resp.json()["default_tier"] == tier
    finally:
        app.dependency_overrides.pop(get_session, None)
