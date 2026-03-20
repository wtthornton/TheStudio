"""Tests for dashboard health endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.app import app


@pytest.mark.asyncio
async def test_dashboard_health():
    """GET /api/v1/dashboard/health returns ok."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v1/dashboard/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
