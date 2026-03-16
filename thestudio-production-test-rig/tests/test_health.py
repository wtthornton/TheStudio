"""Health endpoint tests — unauthenticated liveness and readiness probes.

Contract: /healthz (200, {"status":"ok"}), /readyz (200, {"status":"ready"}).
"""

import httpx


class TestHealth:
    """Unauthenticated health endpoints."""

    def test_healthz_returns_200(self, http_client: httpx.Client) -> None:
        r = http_client.get("/healthz")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_readyz_returns_200(self, http_client: httpx.Client) -> None:
        r = http_client.get("/readyz")
        assert r.status_code == 200
        data = r.json()
        assert data.get("status") == "ready"
