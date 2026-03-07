"""Tests for Platform Maturity Admin UI (Stories 7.10-7.14)."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.admin.rbac import Role, get_current_user_id, get_current_user_role
from src.app import app


@pytest.fixture(autouse=True)
def override_auth():
    """Override auth to bypass DB for UI routes."""
    app.dependency_overrides[get_current_user_id] = lambda: "test-user"
    app.dependency_overrides[get_current_user_role] = lambda: Role.ADMIN
    yield
    app.dependency_overrides.pop(get_current_user_id, None)
    app.dependency_overrides.pop(get_current_user_role, None)


def _mock_resolve_role():
    """Patch _resolve_role to avoid DB access in UI routes."""
    return patch("src.admin.ui_router._resolve_role", return_value=Role.ADMIN)


@pytest.mark.asyncio
class TestNavigation:
    """Story 7.14: Navigation entries."""

    async def test_nav_has_tool_hub_link(self):
        with _mock_resolve_role():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/ui/tools")
            assert resp.status_code == 200
            assert "Tool Hub" in resp.text
            assert "/admin/ui/tools" in resp.text

    async def test_nav_has_models_link(self):
        with _mock_resolve_role():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/ui/models")
            assert resp.status_code == 200
            assert "Models" in resp.text

    async def test_nav_has_compliance_link(self):
        with _mock_resolve_role():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/ui/compliance")
            assert resp.status_code == 200
            assert "Compliance" in resp.text


@pytest.mark.asyncio
class TestToolHubUI:
    """Story 7.10: Tool Hub Console."""

    async def test_tools_page_renders(self):
        with _mock_resolve_role():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/ui/tools")
            assert resp.status_code == 200
            assert "Tool Hub" in resp.text

    async def test_tools_partial_shows_suites(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/tools")
        assert resp.status_code == 200
        assert "code-quality" in resp.text
        assert "context-retrieval" in resp.text
        assert "documentation" in resp.text
        assert "tool-catalog-card" in resp.text

    async def test_tools_partial_shows_profiles(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/tools")
        assert resp.status_code == 200
        assert "tool-profiles-card" in resp.text
        assert "observe-default" in resp.text

    async def test_tools_partial_shows_access_check(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/tools")
        assert resp.status_code == 200
        assert "access-check-card" in resp.text

    async def test_tools_partial_shows_approval_badges(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/tools")
        assert resp.status_code == 200
        assert "EXECUTE" in resp.text
        assert "SUGGEST" in resp.text


@pytest.mark.asyncio
class TestModelGatewayUI:
    """Story 7.11: Model Gateway Console."""

    async def test_models_page_renders(self):
        with _mock_resolve_role():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/ui/models")
            assert resp.status_code == 200
            assert "Model Gateway" in resp.text

    async def test_models_partial_shows_providers(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/models")
        assert resp.status_code == 200
        assert "providers-card" in resp.text
        assert "anthropic" in resp.text
        assert "FAST" in resp.text
        assert "BALANCED" in resp.text
        assert "STRONG" in resp.text

    async def test_models_partial_shows_routing_rules(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/models")
        assert resp.status_code == 200
        assert "routing-rules-card" in resp.text
        assert "intake" in resp.text
        assert "primary_agent" in resp.text

    async def test_models_partial_shows_simulator(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/models")
        assert resp.status_code == 200
        assert "routing-simulator-card" in resp.text


@pytest.mark.asyncio
class TestComplianceScorecardUI:
    """Story 7.12: Compliance Scorecard Console."""

    async def test_compliance_page_renders(self):
        with _mock_resolve_role():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/ui/compliance")
            assert resp.status_code == 200
            assert "Compliance Scorecard" in resp.text

    async def test_compliance_partial_shows_checks(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/compliance?repo_id=test-repo")
        assert resp.status_code == 200
        assert "compliance-status-card" in resp.text
        assert "compliance-checks-card" in resp.text
        assert "FAIL" in resp.text  # Default data is all False

    async def test_compliance_partial_shows_7_checks(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/compliance?repo_id=test-repo")
        assert resp.status_code == 200
        assert "Branch protection" in resp.text
        assert "Required reviewers" in resp.text
        assert "Standard platform labels" in resp.text
        assert "Projects v2" in resp.text
        assert "Evidence comment format" in resp.text
        assert "Idempotency guard" in resp.text
        assert "Execution plane health" in resp.text

    async def test_compliance_partial_shows_remediation(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/compliance?repo_id=test-repo")
        assert resp.status_code == 200
        # Failed checks show remediation detail
        assert "not configured" in resp.text or "not active" in resp.text


@pytest.mark.asyncio
class TestOperationalTargetsUI:
    """Story 7.13: Operational Targets on metrics page."""

    async def test_targets_partial_renders(self):
        with patch("src.admin.ui_router.get_targets_service") as mock_svc:
            from src.admin.operational_targets import (
                CycleTimeMetrics,
                LeadTimeMetrics,
                ReopenTargetMetrics,
            )
            svc = mock_svc.return_value
            svc.get_lead_time.return_value = LeadTimeMetrics(p50=1.5, p95=4.0, p99=8.0, sample_count=20)
            svc.get_cycle_time.return_value = CycleTimeMetrics(p50=0.5, p95=2.0, p99=5.0, sample_count=15)
            svc.get_reopen_target.return_value = ReopenTargetMetrics(current_rate=0.03, met=True, sample_count=100)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/ui/partials/targets")
        assert resp.status_code == 200
        assert "lead-time-card" in resp.text
        assert "cycle-time-card" in resp.text
        assert "reopen-target-card" in resp.text

    async def test_targets_shows_lead_time_values(self):
        with patch("src.admin.ui_router.get_targets_service") as mock_svc:
            from src.admin.operational_targets import (
                CycleTimeMetrics,
                LeadTimeMetrics,
                ReopenTargetMetrics,
            )
            svc = mock_svc.return_value
            svc.get_lead_time.return_value = LeadTimeMetrics(p50=2.5, p95=6.0, p99=10.0, sample_count=25)
            svc.get_cycle_time.return_value = CycleTimeMetrics(p50=1.0, p95=3.0, p99=7.0, sample_count=25)
            svc.get_reopen_target.return_value = ReopenTargetMetrics(current_rate=0.02, met=True, sample_count=50)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/ui/partials/targets")
        assert resp.status_code == 200
        assert "2.5" in resp.text  # P50
        assert "6.0" in resp.text  # P95

    async def test_targets_shows_reopen_meeting(self):
        with patch("src.admin.ui_router.get_targets_service") as mock_svc:
            from src.admin.operational_targets import (
                CycleTimeMetrics,
                LeadTimeMetrics,
                ReopenTargetMetrics,
            )
            svc = mock_svc.return_value
            svc.get_lead_time.return_value = LeadTimeMetrics(p50=1.0, p95=3.0, p99=5.0, sample_count=20)
            svc.get_cycle_time.return_value = CycleTimeMetrics(p50=0.5, p95=1.5, p99=3.0, sample_count=20)
            svc.get_reopen_target.return_value = ReopenTargetMetrics(current_rate=0.03, met=True, sample_count=100)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/ui/partials/targets")
        assert resp.status_code == 200
        assert "MEETING" in resp.text

    async def test_targets_shows_reopen_not_meeting(self):
        with patch("src.admin.ui_router.get_targets_service") as mock_svc:
            from src.admin.operational_targets import (
                CycleTimeMetrics,
                LeadTimeMetrics,
                ReopenTargetMetrics,
            )
            svc = mock_svc.return_value
            svc.get_lead_time.return_value = LeadTimeMetrics(p50=1.0, p95=3.0, p99=5.0, sample_count=20)
            svc.get_cycle_time.return_value = CycleTimeMetrics(p50=0.5, p95=1.5, p99=3.0, sample_count=20)
            svc.get_reopen_target.return_value = ReopenTargetMetrics(current_rate=0.08, met=False, sample_count=100)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/ui/partials/targets")
        assert resp.status_code == 200
        assert "NOT MEETING" in resp.text

    async def test_targets_insufficient_data(self):
        with patch("src.admin.ui_router.get_targets_service") as mock_svc:
            from src.admin.operational_targets import (
                CycleTimeMetrics,
                LeadTimeMetrics,
                ReopenTargetMetrics,
            )
            svc = mock_svc.return_value
            svc.get_lead_time.return_value = LeadTimeMetrics(insufficient_data=True, sample_count=3)
            svc.get_cycle_time.return_value = CycleTimeMetrics(insufficient_data=True, sample_count=2)
            svc.get_reopen_target.return_value = ReopenTargetMetrics(insufficient_data=True, met=True, sample_count=1)

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/ui/partials/targets")
        assert resp.status_code == 200
        assert "Insufficient Data" in resp.text

    async def test_metrics_page_has_targets_section(self):
        with _mock_resolve_role():
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/ui/metrics")
        assert resp.status_code == 200
        assert "Operational Targets" in resp.text
        assert "/admin/ui/partials/targets" in resp.text
