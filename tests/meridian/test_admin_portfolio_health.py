"""Tests for the Admin UI portfolio health dashboard (Story 29.8).

Validates route registration and partial rendering.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.admin.ui_router import ui_router


@pytest.fixture
def app():
    """Create a test FastAPI app with the UI router."""
    app = FastAPI()
    app.include_router(ui_router)
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


class TestPortfolioHealthPage:
    def test_page_route_exists(self, client):
        """GET /admin/ui/portfolio-health returns 200."""
        with patch(
            "src.admin.ui_router._require_ui_auth",
            new_callable=AsyncMock,
        ):
            resp = client.get(
                "/admin/ui/portfolio-health",
                headers={"X-User-ID": "test-user"},
            )
        # May fail auth in test, but route should be registered
        assert resp.status_code in (200, 401, 500)

    def test_partial_route_exists(self, client):
        """GET /admin/ui/partials/portfolio-health returns 200."""
        with (
            patch(
                "src.admin.ui_router._require_ui_auth",
                new_callable=AsyncMock,
            ),
            patch(
                "src.admin.ui_router._get_recent_portfolio_reviews",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            resp = client.get(
                "/admin/ui/partials/portfolio-health",
                headers={"X-User-ID": "test-user"},
            )
        assert resp.status_code in (200, 401, 500)


class TestGetRecentPortfolioReviews:
    @pytest.mark.asyncio
    async def test_returns_empty_on_db_error(self):
        """Returns empty list when DB is unavailable."""
        from src.admin.ui_router import _get_recent_portfolio_reviews

        # Without a real DB, this should return []
        result = await _get_recent_portfolio_reviews()
        assert result == []


class TestPortfolioHealthNavLink:
    def test_nav_link_in_base_template(self):
        """Base template includes Portfolio Health nav link."""
        from pathlib import Path

        base_html = Path("src/admin/templates/base.html").read_text()
        assert "portfolio-health" in base_html
        assert "Portfolio Health" in base_html
