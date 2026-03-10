"""Tests for Admin UI — Success Gate Card (Story 6.8)."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.admin.experts import ExpertSummary
from src.admin.metrics import LoopbackEntry, LoopbackMetrics, ReopenMetrics, SinglePassMetrics
from src.admin.success_gate import SuccessGateResult
from src.app import app


def _make_mock_services(gate_result):
    """Create mock services for metrics partial."""
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

    mock_metrics = type("M", (), {
        "get_single_pass": lambda self, **kw: single_pass,
        "get_loopbacks": lambda self, **kw: loopbacks,
        "get_reopen": lambda self, **kw: reopen,
    })()
    mock_gate = type("G", (), {
        "check": lambda self, **kw: gate_result,
    })()
    mock_role = AsyncMock()
    mock_role.get_user_role.return_value = None

    return mock_metrics, mock_gate, mock_role


@pytest.mark.asyncio
class TestSuccessGateUI:
    """Tests for success gate card on metrics dashboard."""

    async def test_success_gate_card_renders_passing(self):
        gate_result = SuccessGateResult(
            met=True, current_rate=0.65, threshold=0.60,
            sample_count=40, window_days=28,
        )
        mock_metrics, mock_gate, mock_role = _make_mock_services(gate_result)

        with (
            patch("src.admin.ui_router.get_metrics_service", return_value=mock_metrics),
            patch("src.admin.ui_router.get_success_gate_service", return_value=mock_gate),
            patch("src.admin.ui_router.get_rbac_service", return_value=mock_role),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/ui/partials/metrics", headers={"X-User-ID": "test@studio"})
            assert resp.status_code == 200
            assert "success-gate-card" in resp.text
            assert "PASSING" in resp.text

    async def test_success_gate_card_renders_failing(self):
        gate_result = SuccessGateResult(
            met=False, current_rate=0.45, threshold=0.60,
            sample_count=40, window_days=28,
        )
        mock_metrics, mock_gate, mock_role = _make_mock_services(gate_result)

        with (
            patch("src.admin.ui_router.get_metrics_service", return_value=mock_metrics),
            patch("src.admin.ui_router.get_success_gate_service", return_value=mock_gate),
            patch("src.admin.ui_router.get_rbac_service", return_value=mock_role),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/ui/partials/metrics", headers={"X-User-ID": "test@studio"})
            assert resp.status_code == 200
            assert "FAILING" in resp.text

    async def test_success_gate_card_insufficient_data(self):
        gate_result = SuccessGateResult(
            met=True, current_rate=0.33, threshold=0.60,
            sample_count=3, window_days=28, insufficient_data=True,
        )
        mock_metrics, mock_gate, mock_role = _make_mock_services(gate_result)

        with (
            patch("src.admin.ui_router.get_metrics_service", return_value=mock_metrics),
            patch("src.admin.ui_router.get_success_gate_service", return_value=mock_gate),
            patch("src.admin.ui_router.get_rbac_service", return_value=mock_role),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/ui/partials/metrics", headers={"X-User-ID": "test@studio"})
            assert resp.status_code == 200
            assert "Insufficient Data" in resp.text
            assert "Not enough data" in resp.text

    async def test_success_gate_shows_rate_and_threshold(self):
        gate_result = SuccessGateResult(
            met=True, current_rate=0.75, threshold=0.60,
            sample_count=20, window_days=28,
        )
        mock_metrics, mock_gate, mock_role = _make_mock_services(gate_result)

        with (
            patch("src.admin.ui_router.get_metrics_service", return_value=mock_metrics),
            patch("src.admin.ui_router.get_success_gate_service", return_value=mock_gate),
            patch("src.admin.ui_router.get_rbac_service", return_value=mock_role),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/ui/partials/metrics", headers={"X-User-ID": "test@studio"})
            assert resp.status_code == 200
            assert "75.0%" in resp.text
            assert "60%" in resp.text

    async def test_success_gate_shows_sample_count(self):
        gate_result = SuccessGateResult(
            met=True, current_rate=0.65, threshold=0.60,
            sample_count=42, window_days=28,
        )
        mock_metrics, mock_gate, mock_role = _make_mock_services(gate_result)

        with (
            patch("src.admin.ui_router.get_metrics_service", return_value=mock_metrics),
            patch("src.admin.ui_router.get_success_gate_service", return_value=mock_gate),
            patch("src.admin.ui_router.get_rbac_service", return_value=mock_role),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/ui/partials/metrics", headers={"X-User-ID": "test@studio"})
            assert "42" in resp.text
