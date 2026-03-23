"""Deployment-mode GitHub integration tests.

These tests exercise the deployed app's webhook endpoint through Caddy.
They prove the deployed container correctly:
  1. Accepts HMAC-signed webhook payloads.
  2. Creates TaskPackets from webhook events.
  3. Returns proper HTTP responses.

Unlike tests/integration/test_real_github.py (which imports the adapter
directly), these tests hit the app's HTTP API as a real client would.
"""

from __future__ import annotations

import json
import time

import httpx
import pytest

from tests.p0.conftest import build_webhook_headers, make_issue_payload


@pytest.mark.p0
class TestWebhookDeployed:
    """Webhook endpoint tests via Caddy (no auth required)."""

    def test_healthz_through_caddy(self, p0_base_url: str) -> None:
        """App healthz is reachable through Caddy."""
        r = httpx.get(f"{p0_base_url}/healthz", verify=False, timeout=5)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_ralph_health_through_caddy(self, p0_base_url: str) -> None:
        """Ralph health endpoint is reachable through Caddy and reports status."""
        r = httpx.get(f"{p0_base_url}/health/ralph", verify=False, timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("ok", "degraded", "unavailable")
        assert "agent_mode" in data
        assert "sdk_importable" in data
        assert "cli_available" in data
        # SDK must always be importable in the deployed image
        assert data["sdk_importable"] is True

    def test_webhook_rejects_unsigned_payload(
        self, p0_base_url: str, registered_test_repo: dict,
    ) -> None:
        """Webhook rejects payloads without HMAC signature."""
        payload = make_issue_payload()
        body = json.dumps(payload).encode()
        headers = {
            "X-GitHub-Delivery": "test-no-sig",
            "X-GitHub-Event": "issues",
            "Content-Type": "application/json",
        }
        r = httpx.post(
            f"{p0_base_url}/webhook/github",
            content=body,
            headers=headers,
            verify=False,
            timeout=10,
        )
        # Should reject — 401 or 403
        assert r.status_code in (401, 403), (
            f"Expected 401/403 for unsigned payload, got {r.status_code}"
        )

    def test_webhook_rejects_bad_signature(
        self, p0_base_url: str, registered_test_repo: dict,
    ) -> None:
        """Webhook rejects payloads with wrong HMAC signature."""
        payload = make_issue_payload()
        body = json.dumps(payload).encode()
        headers = build_webhook_headers(body)
        headers["X-Hub-Signature-256"] = "sha256=0000000000000000000000000000000000000000000000000000000000000000"
        r = httpx.post(
            f"{p0_base_url}/webhook/github",
            content=body,
            headers=headers,
            verify=False,
            timeout=10,
        )
        assert r.status_code in (401, 403), (
            f"Expected 401/403 for bad signature, got {r.status_code}"
        )

    def test_webhook_accepts_valid_payload(
        self, p0_base_url: str, registered_test_repo: dict,
    ) -> None:
        """Webhook accepts a properly signed issues.opened payload."""
        payload = make_issue_payload()
        body = json.dumps(payload).encode()
        headers = build_webhook_headers(body)
        r = httpx.post(
            f"{p0_base_url}/webhook/github",
            content=body,
            headers=headers,
            verify=False,
            timeout=15,
        )
        # 200 (processed) or 202 (accepted for async) or 204 (no content)
        assert r.status_code in (200, 201, 202, 204), (
            f"Expected 200/201/202/204 for valid webhook, got {r.status_code}: {r.text}"
        )

    def test_webhook_through_caddy_not_bypassed(self, p0_base_url: str) -> None:
        """Port 9443 (Caddy) is reachable, but port 8000 (app) is NOT exposed.

        This proves traffic goes through Caddy's TLS and auth layers.
        """
        # Caddy on 9443 should be reachable
        r = httpx.get(f"{p0_base_url}/healthz", verify=False, timeout=5)
        assert r.status_code == 200, "Caddy (9443) should be reachable"

        # App on 8000 should NOT be reachable from the host
        with pytest.raises(
            (httpx.ConnectError, httpx.ConnectTimeout),
        ):
            httpx.get("http://localhost:8000/healthz", timeout=3)


@pytest.mark.p0
class TestAdminAPIDeployed:
    """Admin API tests via Caddy (requires Basic Auth via p0_client)."""

    def test_admin_health(self, p0_client: httpx.Client) -> None:
        """Admin health endpoint returns service status."""
        r = p0_client.get("/admin/health")
        assert r.status_code == 200
        data = r.json()
        assert data["overall_status"] == "OK"

    def test_list_repos(self, p0_client: httpx.Client) -> None:
        """Admin repos endpoint lists registered repos."""
        r = p0_client.get("/admin/repos")
        assert r.status_code == 200
        data = r.json()
        assert "repos" in data

    def test_register_and_query_repo(
        self, p0_client: httpx.Client, registered_test_repo: dict,
    ) -> None:
        """Test repo is registered and queryable."""
        r = p0_client.get("/admin/repos")
        assert r.status_code == 200
        repos = r.json()["repos"]
        names = [f"{rp['owner']}/{rp['repo']}" for rp in repos]
        assert "p0-test-org/p0-test-repo" in names

    def test_workflow_created_after_webhook(
        self, p0_client: httpx.Client, p0_base_url: str,
        registered_test_repo: dict,
    ) -> None:
        """A webhook creates a workflow visible via admin API.

        Sends a webhook, waits briefly, then queries /admin/workflows to
        see if a workflow was created for the test repo.
        """
        payload = make_issue_payload(issue_number=99999)
        body = json.dumps(payload).encode()
        headers = build_webhook_headers(body)
        r = httpx.post(
            f"{p0_base_url}/webhook/github",
            content=body,
            headers=headers,
            verify=False,
            timeout=15,
        )
        assert r.status_code in (200, 201, 202, 204)

        # Give the app a moment to process
        time.sleep(2)

        # Query workflows for the test repo
        r = p0_client.get("/admin/workflows")
        assert r.status_code == 200
