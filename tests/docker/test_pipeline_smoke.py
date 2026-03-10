"""Full pipeline smoke test through the Docker Compose stack.

Proves that a webhook payload flows through the deployed stack and
creates a TaskPacket. Pure HTTP — no in-process imports of application code.
"""

import json
import time

import httpx
import pytest

from tests.docker.conftest import build_webhook_headers, make_issue_payload

pytestmark = pytest.mark.docker


class TestPipelineSmoke:
    """End-to-end: webhook POST -> TaskPacket creation."""

    def test_webhook_creates_taskpacket(
        self,
        http_client: httpx.Client,
        registered_repo: dict,
    ) -> None:
        """Send a webhook and verify the intake pipeline creates a TaskPacket.

        The full intake path: real HTTP -> signature validation -> repo lookup
        -> dedup check -> TaskPacket creation -> Temporal workflow attempt.
        A 201 response proves the entire intake pipeline executed successfully.
        """
        # Use a unique issue number to avoid dedup
        issue_number = int(time.time()) % 100000

        payload = make_issue_payload(issue_number=issue_number)
        body = json.dumps(payload).encode()
        headers = build_webhook_headers(body, event="issues")

        # Send webhook through the real deployed HTTP layer
        r = http_client.post("/webhook/github", content=body, headers=headers)
        assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"

        # 201 = "TaskPacket created" — proves the full intake pipeline ran:
        # signature validated, repo found, not a duplicate, TaskPacket persisted.
        # The response body confirms this.
        assert "TaskPacket created" in r.text

    def test_duplicate_webhook_is_idempotent(
        self,
        http_client: httpx.Client,
        registered_repo: dict,
    ) -> None:
        """Sending the same delivery ID twice should be deduplicated."""
        payload = make_issue_payload(issue_number=88888)
        body = json.dumps(payload).encode()
        headers = build_webhook_headers(body, event="issues")

        # First request — should create
        r1 = http_client.post("/webhook/github", content=body, headers=headers)
        assert r1.status_code == 201

        # Second request with same delivery ID — should be deduped (200)
        r2 = http_client.post("/webhook/github", content=body, headers=headers)
        assert r2.status_code == 200
        assert "Duplicate" in r2.text or "already processed" in r2.text
