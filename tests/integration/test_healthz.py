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
