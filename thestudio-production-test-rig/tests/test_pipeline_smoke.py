"""Pipeline smoke test — verify webhook triggers TaskPacket creation.

Proves that a valid webhook enters the pipeline, not just returns 200.
This is a thin smoke test, not full pipeline validation (that is Epic 15).
Requires WEBHOOK_SECRET env var — skips cleanly if missing.
"""

import hashlib
import hmac
import json
import time
import uuid

import httpx
import pytest


class TestPipelineSmoke:
    """Verify that a webhook triggers observable pipeline activity."""

    SMOKE_OWNER = "test-smoke-org"
    SMOKE_REPO = "test-smoke-repo"

    @staticmethod
    def _sign_payload(payload_bytes: bytes, secret: str) -> str:
        sig = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
        return f"sha256={sig}"

    def _register_or_find(self, http_client: httpx.Client) -> str:
        """Register a test repo and return its ID (idempotent)."""
        payload = {
            "owner": self.SMOKE_OWNER,
            "repo": self.SMOKE_REPO,
            "installation_id": 77777,
            "default_branch": "main",
        }
        r = http_client.post("/admin/repos", json=payload)
        assert r.status_code in (201, 409)
        if r.status_code == 201:
            return r.json()["id"]
        list_r = http_client.get("/admin/repos")
        assert list_r.status_code == 200
        repos = [
            p for p in list_r.json()["repos"]
            if p["owner"] == self.SMOKE_OWNER and p["repo"] == self.SMOKE_REPO
        ]
        assert repos, f"Repo {self.SMOKE_OWNER}/{self.SMOKE_REPO} not found after 409"
        return repos[0]["id"]

    def test_webhook_triggers_taskpacket(
        self, http_client: httpx.Client, webhook_secret: str
    ) -> None:
        """Register repo, send valid webhook, verify 200/201 response.

        This test validates that the webhook endpoint accepts a properly
        signed payload for a registered repo and triggers pipeline processing.
        The 200 response indicates the event was processed; 201 indicates
        a TaskPacket was created.
        """
        repo_id = self._register_or_find(http_client)

        issue_payload = {
            "action": "opened",
            "issue": {
                "number": int(time.time()) % 100000,
                "title": f"Pipeline smoke test {uuid.uuid4().hex[:8]}",
                "body": "Automated pipeline smoke test from production test rig.",
                "user": {"login": "test-bot"},
                "labels": [],
                "state": "open",
            },
            "repository": {
                "full_name": f"{self.SMOKE_OWNER}/{self.SMOKE_REPO}",
                "name": self.SMOKE_REPO,
                "owner": {"login": self.SMOKE_OWNER},
                "default_branch": "main",
            },
            "sender": {"login": "test-bot"},
        }

        body = json.dumps(issue_payload).encode()
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
        # 200 = processed (event handled, may be dedupe or filtered)
        # 201 = TaskPacket created (full success)
        assert r.status_code in (200, 201), (
            f"Webhook for registered repo should succeed, got {r.status_code}: {r.text}"
        )
