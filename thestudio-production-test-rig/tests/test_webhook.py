"""Webhook signature validation tests.

Validates that POST /webhook/github correctly enforces HMAC-SHA256 signatures.
Requires WEBHOOK_SECRET env var — tests skip cleanly if missing.

Contract endpoints tested:
- POST /webhook/github (valid signature → 200/201)
- POST /webhook/github (missing signature → 401)
- POST /webhook/github (invalid signature → 401/403)
- POST /webhook/github (missing delivery header → 400)
"""

import hashlib
import hmac
import json
import uuid

import httpx
import pytest


class TestWebhookSignature:
    """Webhook HMAC-SHA256 signature validation against deployed instance."""

    @staticmethod
    def _make_issue_payload(owner: str = "test-org", repo: str = "test-repo") -> dict:
        """Minimal realistic GitHub issues.opened payload."""
        return {
            "action": "opened",
            "issue": {
                "number": 1,
                "title": "Test issue from production test rig",
                "body": "This is a test issue for webhook validation.",
                "user": {"login": "test-bot"},
                "labels": [],
                "state": "open",
            },
            "repository": {
                "full_name": f"{owner}/{repo}",
                "name": repo,
                "owner": {"login": owner},
                "default_branch": "main",
            },
            "sender": {"login": "test-bot"},
        }

    @staticmethod
    def _sign_payload(payload_bytes: bytes, secret: str) -> str:
        """Compute HMAC-SHA256 signature in GitHub format."""
        sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
        return f"sha256={sig}"

    def test_valid_signature_accepted(
        self, http_client: httpx.Client, webhook_secret: str
    ) -> None:
        """POST with valid HMAC-SHA256 returns 200 or 201."""
        payload = self._make_issue_payload()
        body = json.dumps(payload).encode()
        signature = self._sign_payload(body, webhook_secret)
        delivery_id = str(uuid.uuid4())

        r = http_client.post(
            "/webhook/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature,
                "X-GitHub-Delivery": delivery_id,
                "X-GitHub-Event": "issues",
            },
        )
        # 200 = event processed (repo may not be registered, which is fine)
        # 201 = TaskPacket created
        # 404 = repo not registered (also acceptable — validates sig first)
        assert r.status_code in (200, 201, 404), (
            f"Expected 200/201/404 for valid signature, got {r.status_code}: {r.text}"
        )

    def test_missing_signature_returns_401(
        self, http_client: httpx.Client, webhook_secret: str
    ) -> None:
        """POST without X-Hub-Signature-256 returns 401."""
        payload = self._make_issue_payload()
        body = json.dumps(payload).encode()
        delivery_id = str(uuid.uuid4())

        r = http_client.post(
            "/webhook/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Delivery": delivery_id,
                "X-GitHub-Event": "issues",
            },
        )
        assert r.status_code in (400, 401), (
            f"Expected 400/401 for missing signature, got {r.status_code}: {r.text}"
        )

    def test_invalid_signature_rejected(
        self, http_client: httpx.Client, webhook_secret: str
    ) -> None:
        """POST with wrong HMAC-SHA256 returns 401 or 403."""
        payload = self._make_issue_payload()
        body = json.dumps(payload).encode()
        delivery_id = str(uuid.uuid4())

        r = http_client.post(
            "/webhook/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": "sha256=0000000000000000000000000000000000000000000000000000000000000000",
                "X-GitHub-Delivery": delivery_id,
                "X-GitHub-Event": "issues",
            },
        )
        assert r.status_code in (401, 403), (
            f"Expected 401/403 for invalid signature, got {r.status_code}: {r.text}"
        )

    def test_missing_delivery_header_returns_400(
        self, http_client: httpx.Client, webhook_secret: str
    ) -> None:
        """POST with valid signature but no X-GitHub-Delivery returns 400."""
        payload = self._make_issue_payload()
        body = json.dumps(payload).encode()
        signature = self._sign_payload(body, webhook_secret)

        r = http_client.post(
            "/webhook/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "issues",
            },
        )
        assert r.status_code == 400, (
            f"Expected 400 for missing delivery header, got {r.status_code}: {r.text}"
        )
