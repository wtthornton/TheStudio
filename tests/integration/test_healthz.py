"""Health check endpoint test.

Story 9.8 (Epic 9): Verify the /healthz endpoint returns 200 with expected body.
"""

from fastapi.testclient import TestClient

from src.app import app


class TestHealthzEndpoint:
    """Unauthenticated liveness probe endpoint."""

    def test_healthz_returns_200(self):
        client = TestClient(app)
        response = client.get("/healthz")
        assert response.status_code == 200

    def test_healthz_returns_ok_status(self):
        client = TestClient(app)
        response = client.get("/healthz")
        data = response.json()
        assert data["status"] == "ok"

    def test_root_redirects(self):
        """Root / redirects to /dashboard/ (when built) or /admin/ui/ (fallback)."""
        client = TestClient(app)
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] in ("/dashboard/", "/admin/ui/")
