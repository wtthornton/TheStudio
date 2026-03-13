"""Tests for Platform Maturity API — Tool Hub, Model Gateway, Compliance, Targets (Stories 7.3, 7.6, 7.8, 7.9)."""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.admin.rbac import Role, get_current_user_id, get_current_user_role
from src.app import app


@pytest.fixture(autouse=True)
def override_auth():
    """Override auth to bypass DB access for permission checks."""
    app.dependency_overrides[get_current_user_id] = lambda: "test-user"
    app.dependency_overrides[get_current_user_role] = lambda: Role.ADMIN
    yield
    app.dependency_overrides.pop(get_current_user_id, None)
    app.dependency_overrides.pop(get_current_user_role, None)


@pytest.mark.asyncio
class TestToolCatalogAPI:

    async def test_list_catalog(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/tools/catalog")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3
        suite_names = [s["name"] for s in data["suites"]]
        assert "code-quality" in suite_names
        assert "context-retrieval" in suite_names
        assert "documentation" in suite_names

    async def test_get_suite_detail(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/tools/catalog/code-quality")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "code-quality"
        assert data["tool_count"] >= 4

    async def test_get_suite_not_found(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/tools/catalog/nonexistent")
        assert resp.status_code == 404

    async def test_list_profiles(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/tools/profiles")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3

    async def test_check_access_allowed(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/admin/tools/check-access", json={
                "role": "developer",
                "overlays": [],
                "repo_tier": "execute",
                "suite_name": "code-quality",
                "tool_name": "ruff",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["allowed"] is True

    async def test_check_access_denied(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/admin/tools/check-access", json={
                "role": "planner",
                "overlays": [],
                "repo_tier": "execute",
                "suite_name": "code-quality",
                "tool_name": "ruff",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["allowed"] is False


@pytest.mark.asyncio
class TestModelGatewayAPI:

    async def test_route_model(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/admin/models/route", json={
                "step": "intake",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["resolved_class"] == "fast"
        assert data["selected"]["model_class"] == "fast"

    async def test_route_model_with_overlay(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/admin/models/route", json={
                "step": "intent",
                "overlays": ["security"],
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["resolved_class"] == "strong"

    async def test_list_providers(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/models/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3

    async def test_query_audit_empty(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/models/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["records"], list)

    async def test_set_budget(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/admin/models/budget/repo-1", json={
                "per_task_max_spend": 5.0,
                "per_step_token_cap": 100000,
                "conservative_mode": True,
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["repo_id"] == "repo-1"
        assert data["budget"]["per_task_max_spend"] == 5.0
        assert data["budget"]["conservative_mode"] is True


@pytest.mark.asyncio
class TestComplianceScorecardAPI:

    async def test_get_scorecard_default(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/repos/repo-1/compliance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["repo_id"] == "repo-1"
        assert data["checks_total"] == 8
        assert data["overall_pass"] is False

    async def test_evaluate_compliance_all_pass(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/admin/repos/repo-1/compliance/evaluate", json={
                "branch_protection_enabled": True,
                "required_reviewers_configured": True,
                "standard_labels_present": True,
                "projects_v2_configured": True,
                "evidence_format_valid": True,
                "idempotency_guard_active": True,
                "execution_plane_healthy": True,
                "execute_tier_policy_passed": True,
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_pass"] is True
        assert data["checks_passed"] == 8

    async def test_evaluate_compliance_partial_fail(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/admin/repos/repo-1/compliance/evaluate", json={
                "branch_protection_enabled": True,
                "required_reviewers_configured": False,
                "standard_labels_present": True,
                "projects_v2_configured": True,
                "evidence_format_valid": True,
                "idempotency_guard_active": True,
                "execution_plane_healthy": True,
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_pass"] is False
        assert data["checks_passed"] == 6


@pytest.mark.asyncio
class TestOperationalTargetsAPI:

    async def test_lead_time(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/metrics/lead-time")
        assert resp.status_code == 200
        data = resp.json()
        assert "p50_hours" in data
        assert "p95_hours" in data
        assert "insufficient_data" in data

    async def test_cycle_time(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/metrics/cycle-time")
        assert resp.status_code == 200
        data = resp.json()
        assert "p50_hours" in data

    async def test_reopen_target(self):
        with patch("src.admin.operational_targets.get_metrics_service") as mock_metrics:
            from src.admin.metrics import ReopenMetrics
            mock_metrics.return_value.get_reopen.return_value = ReopenMetrics(
                total_merged=100, total_reopened=3, reopen_rate=0.03,
            )
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/metrics/reopen-target")
        assert resp.status_code == 200
        data = resp.json()
        assert data["met"] is True
        assert data["target"] == 0.05
