"""Unit tests for Cost Dashboard routes — Epic 32, Story 32.13.

Covers: page render, partial render, time window selector, breakdown content.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.admin.model_gateway import ModelCallAudit
from src.admin.model_spend import SpendReport, SpendSummary, TierBudgetUtilization
from src.admin.rbac import Role


@pytest.fixture(autouse=True)
def _mock_services():
    rbac_svc = MagicMock()
    rbac_svc.get_user_role = AsyncMock(return_value=Role.ADMIN)

    health_svc = MagicMock()
    health_svc.check_all = AsyncMock(return_value=MagicMock(
        healthy=True,
        services={},
        overall_status="healthy",
    ))

    with (
        patch("src.admin.ui_router.get_rbac_service", return_value=rbac_svc),
        patch("src.admin.ui_router.get_health_service", return_value=health_svc),
        patch("src.admin.ui_router.get_async_session"),
    ):
        from src.admin import ui_router as ui_mod

        mock_session = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        ui_mod.get_async_session = MagicMock(return_value=mock_cm)
        yield


@pytest.fixture
def client() -> TestClient:
    from src.admin.ui_router import ui_router

    app = FastAPI()
    app.include_router(ui_router)
    return TestClient(app)


ADMIN_HEADERS = {"X-User-ID": "admin@studio"}


def _sample_report(window_hours: int = 24) -> SpendReport:
    return SpendReport(
        total_cost=0.15,
        total_calls=10,
        by_provider=[SpendSummary(key="anthropic", total_cost=0.15, call_count=10)],
        by_step=[SpendSummary(key="intent", total_cost=0.10, call_count=6),
                 SpendSummary(key="qa", total_cost=0.05, call_count=4)],
        by_model=[SpendSummary(key="claude-sonnet-4-6", total_cost=0.15, call_count=10)],
        by_repo=[SpendSummary(key="org/repo-a", total_cost=0.12, call_count=7),
                 SpendSummary(key="org/repo-b", total_cost=0.03, call_count=3)],
        by_day=[SpendSummary(key="2026-03-18", total_cost=0.10, call_count=6),
                SpendSummary(key="2026-03-19", total_cost=0.05, call_count=4)],
        window_hours=window_hours,
        total_cache_creation_tokens=500,
        total_cache_read_tokens=300,
        cache_hit_rate=0.375,
    )


class TestCostDashboardPage:
    def test_page_renders(self, client):
        resp = client.get("/admin/ui/cost-dashboard", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "Cost Dashboard" in resp.text

    def test_page_has_time_window_buttons(self, client):
        resp = client.get("/admin/ui/cost-dashboard", headers=ADMIN_HEADERS)
        assert "window=24" in resp.text
        assert "window=168" in resp.text
        assert "window=720" in resp.text


class TestCostDashboardPartial:
    @patch("src.admin.ui_router.get_spend_report")
    def test_partial_renders_empty(self, mock_report, client):
        mock_report.return_value = SpendReport(window_hours=24)
        resp = client.get("/admin/ui/partials/cost-dashboard", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "No spend data" in resp.text or "No data" in resp.text

    @patch("src.admin.ui_router.get_spend_report")
    def test_partial_renders_with_data(self, mock_report, client):
        mock_report.return_value = _sample_report()
        resp = client.get("/admin/ui/partials/cost-dashboard", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "anthropic" in resp.text
        assert "org/repo-a" in resp.text
        assert "2026-03-18" in resp.text
        assert "37.5%" in resp.text  # cache hit rate

    @patch("src.admin.ui_router.get_spend_report")
    def test_partial_respects_window_param(self, mock_report, client):
        mock_report.return_value = _sample_report(window_hours=168)
        resp = client.get("/admin/ui/partials/cost-dashboard?window=168", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        mock_report.assert_called_once_with(window_hours=168)

    @patch("src.admin.ui_router.get_spend_report")
    def test_partial_shows_by_step(self, mock_report, client):
        mock_report.return_value = _sample_report()
        resp = client.get("/admin/ui/partials/cost-dashboard", headers=ADMIN_HEADERS)
        assert "intent" in resp.text
        assert "qa" in resp.text

    @patch("src.admin.ui_router.get_spend_report")
    def test_partial_shows_by_model(self, mock_report, client):
        mock_report.return_value = _sample_report()
        resp = client.get("/admin/ui/partials/cost-dashboard", headers=ADMIN_HEADERS)
        assert "claude-sonnet-4-6" in resp.text

    @patch("src.admin.ui_router.get_spend_report")
    def test_partial_shows_by_repo(self, mock_report, client):
        mock_report.return_value = _sample_report()
        resp = client.get("/admin/ui/partials/cost-dashboard", headers=ADMIN_HEADERS)
        assert "org/repo-a" in resp.text
        assert "org/repo-b" in resp.text

    @patch("src.admin.ui_router.get_spend_report")
    def test_partial_shows_by_day(self, mock_report, client):
        mock_report.return_value = _sample_report()
        resp = client.get("/admin/ui/partials/cost-dashboard", headers=ADMIN_HEADERS)
        assert "2026-03-18" in resp.text
        assert "2026-03-19" in resp.text

    @patch("src.admin.ui_router.get_spend_report")
    def test_partial_shows_cache_metrics(self, mock_report, client):
        mock_report.return_value = _sample_report()
        resp = client.get("/admin/ui/partials/cost-dashboard", headers=ADMIN_HEADERS)
        assert "Cache Hit Rate" in resp.text
        assert "300 read" in resp.text  # cache read tokens

    def test_partial_rejects_invalid_window(self, client):
        resp = client.get("/admin/ui/partials/cost-dashboard?window=0", headers=ADMIN_HEADERS)
        assert resp.status_code == 422

    def test_partial_rejects_excessive_window(self, client):
        resp = client.get("/admin/ui/partials/cost-dashboard?window=999", headers=ADMIN_HEADERS)
        assert resp.status_code == 422


class TestBudgetUtilizationPartial:
    """Story 32.14: Budget utilization widget route tests."""

    @patch("src.admin.ui_router.get_budget_utilization")
    def test_partial_renders(self, mock_util, client):
        mock_util.return_value = [
            TierBudgetUtilization(tier="observe", budget_limit=2.0, current_spend=0.5, active_tasks=2, utilization_pct=25.0),
            TierBudgetUtilization(tier="suggest", budget_limit=5.0, current_spend=0.0, active_tasks=0, utilization_pct=0.0),
            TierBudgetUtilization(tier="execute", budget_limit=8.0, current_spend=7.5, active_tasks=1, utilization_pct=93.75),
        ]
        resp = client.get("/admin/ui/partials/budget-utilization", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        assert "observe" in resp.text
        assert "suggest" in resp.text
        assert "execute" in resp.text

    @patch("src.admin.ui_router.get_budget_utilization")
    def test_partial_shows_spend_and_limit(self, mock_util, client):
        mock_util.return_value = [
            TierBudgetUtilization(tier="observe", budget_limit=2.0, current_spend=0.5, active_tasks=2, utilization_pct=25.0),
            TierBudgetUtilization(tier="suggest", budget_limit=5.0, current_spend=0.0, active_tasks=0, utilization_pct=0.0),
            TierBudgetUtilization(tier="execute", budget_limit=8.0, current_spend=7.5, active_tasks=1, utilization_pct=93.75),
        ]
        resp = client.get("/admin/ui/partials/budget-utilization", headers=ADMIN_HEADERS)
        assert "$0.5000" in resp.text  # observe spend
        assert "$2.00" in resp.text  # observe limit
        assert "93.8%" in resp.text  # execute utilization (rounded)

    @patch("src.admin.ui_router.get_budget_utilization")
    def test_partial_respects_window(self, mock_util, client):
        mock_util.return_value = [
            TierBudgetUtilization(tier=t, budget_limit=5.0, current_spend=0, active_tasks=0, utilization_pct=0)
            for t in ["observe", "suggest", "execute"]
        ]
        resp = client.get("/admin/ui/partials/budget-utilization?window=168", headers=ADMIN_HEADERS)
        assert resp.status_code == 200
        mock_util.assert_called_once_with(window_hours=168)

    def test_page_includes_budget_widget_loader(self, client):
        resp = client.get("/admin/ui/cost-dashboard", headers=ADMIN_HEADERS)
        assert "budget-utilization" in resp.text
