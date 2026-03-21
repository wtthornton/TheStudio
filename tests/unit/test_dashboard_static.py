"""Tests for conditional dashboard static mount (B-0.6)."""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def client():
    """Create test client with the real app."""
    from src.app import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_dashboard_spa_returns_index_html(client):
    """GET /dashboard/ should return the SPA index.html."""
    resp = await client.get("/dashboard/")
    # When frontend/dist exists, should return 200 with HTML
    assert resp.status_code == 200
    assert "<!doctype html>" in resp.text.lower() or "<html" in resp.text.lower()


@pytest.mark.asyncio
async def test_dashboard_spa_catchall(client):
    """GET /dashboard/some/deep/route should still return index.html (SPA routing)."""
    resp = await client.get("/dashboard/some/deep/route")
    assert resp.status_code == 200
    assert "<div id=\"root\">" in resp.text


@pytest.mark.asyncio
async def test_dashboard_favicon(client):
    """GET /dashboard/favicon.svg should return SVG."""
    resp = await client.get("/dashboard/favicon.svg")
    assert resp.status_code == 200
    assert "svg" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_dashboard_assets(client):
    """GET /dashboard/assets/ should serve static files."""
    # Just verify the mount exists — a 404 from StaticFiles is fine (no specific file),
    # but it should not be a 405 or routing error
    resp = await client.get("/dashboard/assets/nonexistent.js")
    assert resp.status_code in (404, 200)
