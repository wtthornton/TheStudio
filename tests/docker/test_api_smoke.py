"""API smoke tests against the running Docker Compose stack.

Verifies that the deployed app serves requests correctly through the
real network stack. All tests require the stack to be running.
"""

import json

import httpx
import pytest

from tests.docker.conftest import (
    build_webhook_headers,
    make_issue_payload,
)

pytestmark = pytest.mark.docker


class TestHealthEndpoints:
    """Verify liveness and admin health endpoints."""

    def test_healthz_returns_200(self, http_client: httpx.Client) -> None:
        r = http_client.get("/healthz")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_admin_health_returns_200(self, http_client: httpx.Client) -> None:
        r = http_client.get("/admin/health")
        assert r.status_code == 200
        data = r.json()
        assert "overall_status" in data


class TestOpenAPI:
    """Verify OpenAPI docs are served."""

    def test_docs_returns_200(self, http_client: httpx.Client) -> None:
        r = http_client.get("/docs")
        assert r.status_code == 200


class TestWebhookSmoke:
    """Verify webhook endpoint accepts well-formed requests."""

    def test_webhook_with_valid_payload_returns_success(
        self,
        http_client: httpx.Client,
        registered_repo: dict,
    ) -> None:
        """POST a valid issue webhook and expect 200 or 201."""
        payload = make_issue_payload()
        body = json.dumps(payload).encode()
        headers = build_webhook_headers(body, event="issues")

        r = http_client.post("/webhook/github", content=body, headers=headers)
        # 200 = duplicate/non-issue, 201 = created. Both are success.
        assert r.status_code in (200, 201), f"Expected 200/201, got {r.status_code}: {r.text}"

    def test_webhook_without_signature_returns_401(
        self,
        http_client: httpx.Client,
    ) -> None:
        """POST without signature header should be rejected."""
        payload = make_issue_payload()
        body = json.dumps(payload).encode()
        headers = {
            "X-GitHub-Delivery": "test-delivery-no-sig",
            "X-GitHub-Event": "issues",
            "Content-Type": "application/json",
        }

        r = http_client.post("/webhook/github", content=body, headers=headers)
        assert r.status_code == 401
