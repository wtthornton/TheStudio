"""Tests for Success Gate API endpoint (Story 6.7)."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.admin.rbac import get_current_user_id
from src.admin.success_gate import SuccessGateResult
from src.app import app


@pytest.fixture
def mock_gate_services():
    """Mock services used by the success gate endpoint."""
    app.dependency_overrides[get_current_user_id] = lambda: "test-user"

    with (
        patch("src.admin.router.get_success_gate_service") as mock_svc,
        patch("src.admin.router.require_permission"),
    ):
        yield mock_svc

    app.dependency_overrides.pop(get_current_user_id, None)


@pytest.mark.asyncio
class TestSuccessGateAPI:
    """Tests for GET /admin/metrics/success-gate."""

    async def test_gate_passes(self, mock_gate_services):
        mock_gate_services.return_value.check.return_value = SuccessGateResult(
            met=True, current_rate=0.75, threshold=0.60,
            sample_count=20, window_days=28,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/metrics/success-gate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["met"] is True
        assert data["current_rate"] == 0.75

    async def test_gate_fails(self, mock_gate_services):
        mock_gate_services.return_value.check.return_value = SuccessGateResult(
            met=False, current_rate=0.45, threshold=0.60,
            sample_count=20, window_days=28,
            category_breakdown={"lint": 5, "test": 3},
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/metrics/success-gate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["met"] is False
        assert data["category_breakdown"]["lint"] == 5

    async def test_gate_insufficient_data(self, mock_gate_services):
        mock_gate_services.return_value.check.return_value = SuccessGateResult(
            met=True, current_rate=0.33, threshold=0.60,
            sample_count=3, window_days=28, insufficient_data=True,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/metrics/success-gate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["insufficient_data"] is True

    async def test_gate_with_repo_filter(self, mock_gate_services):
        mock_gate_services.return_value.check.return_value = SuccessGateResult(
            met=True, current_rate=0.80, threshold=0.60,
            sample_count=15, window_days=28,
        )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/metrics/success-gate?repo=my-repo")
        assert resp.status_code == 200
        mock_gate_services.return_value.check.assert_called_once_with(repo_filter="my-repo")

    async def test_gate_failure_logs_signal(self, mock_gate_services):
        mock_gate_services.return_value.check.return_value = SuccessGateResult(
            met=False, current_rate=0.45, threshold=0.60,
            sample_count=20, window_days=28,
        )
        with patch("src.admin.router.logger") as mock_logger:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/metrics/success-gate")
            assert resp.status_code == 200
            mock_logger.warning.assert_called()

    async def test_gate_pass_no_signal(self, mock_gate_services):
        mock_gate_services.return_value.check.return_value = SuccessGateResult(
            met=True, current_rate=0.75, threshold=0.60,
            sample_count=20, window_days=28,
        )
        with patch("src.admin.router._emit_success_gate_signal") as mock_emit:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/admin/metrics/success-gate")
            mock_emit.assert_not_called()
