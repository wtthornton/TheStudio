"""Tests for Admin UI — Metrics Dashboard & Expert Console (Stories 5.7, 5.8)."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.admin.experts import ExpertDetail, ExpertRepoBreakdown, ExpertSummary
from src.admin.metrics import LoopbackEntry, LoopbackMetrics, ReopenMetrics, SinglePassMetrics
from src.app import app


@pytest.fixture
def mock_ui_services():
    """Mock services used by metrics and expert UI routes."""
    single_pass = SinglePassMetrics(
        overall_rate_7d=0.75, overall_rate_30d=0.65,
        total_workflows_7d=20, total_workflows_30d=40,
        successful_7d=15, successful_30d=26,
    )
    loopbacks = LoopbackMetrics(
        total_loopbacks=10,
        categories=[
            LoopbackEntry(category="lint", count=4, percentage=40.0),
            LoopbackEntry(category="test", count=3, percentage=30.0),
            LoopbackEntry(category="security", count=2, percentage=20.0),
            LoopbackEntry(category="other", count=1, percentage=10.0),
        ],
    )
    reopen = ReopenMetrics(
        total_reopened=3, reopen_rate=0.05,
        attribution={"intent_gap": 1, "implementation_bug": 1, "regression": 1, "governance_failure": 0},
    )

    experts_list = [
        ExpertSummary(
            expert_id="aaaa-1111", expert_version=1, trust_tier="shadow",
            confidence=0.2, weight=0.75, drift_signal="stable", context_count=2,
        ),
    ]

    expert_detail = ExpertDetail(
        expert_id="aaaa-1111", expert_version=1, trust_tier="shadow",
        confidence=0.2, weight=0.75, drift_signal="stable", sample_count=5,
        repos=[ExpertRepoBreakdown(repo="repo-1", consults=3, avg_weight=0.7, drift_signal="stable")],
    )

    mock_metrics = type("MockMetrics", (), {
        "get_single_pass": lambda self, **kw: single_pass,
        "get_loopbacks": lambda self, **kw: loopbacks,
        "get_reopen": lambda self, **kw: reopen,
    })()

    mock_expert_svc = type("MockExpertSvc", (), {
        "list_experts": lambda self, **kw: experts_list,
        "get_expert": lambda self, eid: expert_detail if eid == "aaaa-1111" else None,
    })()

    mock_role_svc = AsyncMock()
    mock_role_svc.get_user_role.return_value = None

    with (
        patch("src.admin.ui_router.get_metrics_service", return_value=mock_metrics),
        patch("src.admin.ui_router.get_expert_service", return_value=mock_expert_svc),
        patch("src.admin.ui_router.get_rbac_service", return_value=mock_role_svc),
        patch("src.admin.ui_router.get_async_session") as mock_session,
    ):
        mock_session.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
        yield


@pytest.mark.asyncio
class TestMetricsDashboardUI:
    """Tests for Metrics Dashboard page (Story 5.7)."""

    async def test_metrics_page_renders(self, mock_ui_services):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/metrics")
            assert resp.status_code == 200
            assert "Metrics" in resp.text

    async def test_metrics_partial_renders(self, mock_ui_services):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/metrics")
            assert resp.status_code == 200
            assert "single-pass-card" in resp.text
            assert "loopback-card" in resp.text
            assert "reopen-card" in resp.text

    async def test_metrics_partial_single_pass_values(self, mock_ui_services):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/metrics")
            assert "75.0%" in resp.text
            assert "15/20" in resp.text

    async def test_metrics_partial_loopback_categories(self, mock_ui_services):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/metrics")
            assert "lint" in resp.text.lower()
            assert "test" in resp.text.lower()

    async def test_metrics_partial_reopen(self, mock_ui_services):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/metrics")
            assert "Reopen Rate" in resp.text
            assert "intent gap" in resp.text.lower() or "intent_gap" in resp.text

    async def test_metrics_page_has_nav_link(self, mock_ui_services):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/metrics")
            assert "/admin/ui/metrics" in resp.text

    async def test_metrics_partial_with_repo_filter(self, mock_ui_services):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/metrics?repo=repo-1")
            assert resp.status_code == 200


@pytest.mark.asyncio
class TestExpertConsoleUI:
    """Tests for Expert Performance Console (Story 5.8)."""

    async def test_experts_page_renders(self, mock_ui_services):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/experts")
            assert resp.status_code == 200
            assert "Expert" in resp.text

    async def test_experts_partial_renders(self, mock_ui_services):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/experts")
            assert resp.status_code == 200
            assert "experts-table" in resp.text
            assert "aaaa-111" in resp.text

    async def test_experts_partial_tier_badge(self, mock_ui_services):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/experts")
            assert "SHADOW" in resp.text

    async def test_experts_partial_drift_indicator(self, mock_ui_services):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/experts")
            assert "stable" in resp.text.lower()

    async def test_expert_detail_page(self, mock_ui_services):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/experts/aaaa-1111")
            assert resp.status_code == 200
            assert "Expert Detail" in resp.text

    async def test_expert_detail_partial(self, mock_ui_services):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/partials/expert/aaaa-1111")
            assert resp.status_code == 200
            assert "repo-1" in resp.text
            assert "Per-Repo Breakdown" in resp.text

    async def test_expert_detail_not_found(self, mock_ui_services):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/experts/nonexistent")
            assert resp.status_code == 200
            assert "not found" in resp.text.lower()

    async def test_experts_page_has_nav_link(self, mock_ui_services):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/ui/experts")
            assert "/admin/ui/experts" in resp.text

    async def test_experts_partial_with_filters(self, mock_ui_services):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/admin/ui/partials/experts?repo=repo-1&tier=shadow"
            )
            assert resp.status_code == 200
