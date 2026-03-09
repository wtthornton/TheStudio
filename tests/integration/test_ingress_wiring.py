"""Integration tests for ingress-to-workflow wiring.

Story 9.7 (Epic 9): Verify webhook handler → eligibility → workflow trigger
produces correct PipelineInput, and dedupe rejects replayed delivery IDs.

Uses FastAPI TestClient with mocked database and Temporal client.
"""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.ingress.dedupe import is_duplicate
from src.ingress.signature import validate_signature


# --- Signature Validation Tests ---


class TestSignatureValidation:
    """Signature validation follows GitHub HMAC-SHA256 spec."""

    def test_valid_signature(self):
        payload = b'{"action": "opened"}'
        secret = "webhook-secret"
        sig = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        assert validate_signature(payload, secret, sig) is True

    def test_invalid_signature(self):
        payload = b'{"action": "opened"}'
        assert validate_signature(payload, "secret", "sha256=bad") is False

    def test_missing_prefix(self):
        assert validate_signature(b"data", "secret", "md5=abc") is False

    def test_tampered_payload(self):
        secret = "webhook-secret"
        original = b'{"action": "opened"}'
        tampered = b'{"action": "closed"}'
        sig = "sha256=" + hmac.new(secret.encode(), original, hashlib.sha256).hexdigest()

        assert validate_signature(tampered, secret, sig) is False


# --- Webhook Handler Integration Tests ---


def _make_issue_payload(repo: str = "acme/widgets", issue_number: int = 42):
    """Build a minimal GitHub issue event payload."""
    return {
        "action": "opened",
        "repository": {"full_name": repo},
        "issue": {
            "number": issue_number,
            "title": "Add /health endpoint",
            "body": "We need a health check.",
            "labels": [{"name": "agent:run"}, {"name": "type:feature"}],
        },
    }


def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    """Compute GitHub webhook signature."""
    return "sha256=" + hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


class TestWebhookHandlerWiring:
    """Webhook handler correctly wires ingress to TaskPacket creation and workflow start."""

    def test_rejects_missing_delivery_header(self):
        """Missing X-GitHub-Delivery returns 400."""
        client = TestClient(app)
        response = client.post(
            "/webhook/github",
            json=_make_issue_payload(),
            headers={
                "X-Hub-Signature-256": "sha256=fake",
                "X-GitHub-Event": "issues",
            },
        )
        assert response.status_code == 400

    def test_rejects_missing_signature_header(self):
        """Missing X-Hub-Signature-256 returns 401."""
        client = TestClient(app)
        response = client.post(
            "/webhook/github",
            json=_make_issue_payload(),
            headers={
                "X-GitHub-Delivery": str(uuid4()),
                "X-GitHub-Event": "issues",
            },
        )
        assert response.status_code == 401

    def test_rejects_missing_repo_in_payload(self):
        """Payload without repository returns 400."""
        client = TestClient(app)
        payload = {"action": "opened", "issue": {"number": 1}}
        payload_bytes = json.dumps(payload).encode()

        response = client.post(
            "/webhook/github",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Delivery": str(uuid4()),
                "X-Hub-Signature-256": "sha256=fake",
                "X-GitHub-Event": "issues",
            },
        )
        assert response.status_code == 400

    @patch("src.ingress.webhook_handler.get_webhook_secret", new_callable=AsyncMock)
    def test_rejects_unregistered_repo(self, mock_get_secret):
        """Unregistered repo (no webhook secret) returns 404."""
        mock_get_secret.return_value = None
        client = TestClient(app)
        response = client.post(
            "/webhook/github",
            json=_make_issue_payload(),
            headers={
                "X-GitHub-Delivery": str(uuid4()),
                "X-Hub-Signature-256": "sha256=fake",
                "X-GitHub-Event": "issues",
            },
        )
        assert response.status_code == 404

    @patch("src.ingress.webhook_handler.start_workflow", new_callable=AsyncMock)
    @patch("src.ingress.webhook_handler.create_taskpacket", new_callable=AsyncMock)
    @patch("src.ingress.webhook_handler.is_duplicate", new_callable=AsyncMock)
    @patch("src.ingress.webhook_handler.get_webhook_secret", new_callable=AsyncMock)
    def test_happy_path_creates_taskpacket_and_starts_workflow(
        self, mock_get_secret, mock_is_dup, mock_create_tp, mock_start_wf
    ):
        """Valid webhook creates TaskPacket and starts workflow, returns 201."""
        secret = "test-webhook-secret"
        mock_get_secret.return_value = secret
        mock_is_dup.return_value = False

        from src.models.taskpacket import TaskPacketRead, TaskPacketStatus
        from datetime import UTC, datetime

        tp = TaskPacketRead(
            id=uuid4(),
            repo="acme/widgets",
            issue_id=42,
            delivery_id="evt-001",
            correlation_id=uuid4(),
            status=TaskPacketStatus.RECEIVED,
            scope=None,
            risk_flags=None,
            complexity_index=None,
            context_packs=[],
            intent_spec_id=None,
            intent_version=None,
            loopback_count=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_create_tp.return_value = tp
        mock_start_wf.return_value = "run-id-123"

        payload = _make_issue_payload()
        payload_bytes = json.dumps(payload).encode()
        signature = _sign_payload(payload_bytes, secret)

        client = TestClient(app)
        response = client.post(
            "/webhook/github",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Delivery": str(uuid4()),
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "issues",
            },
        )

        assert response.status_code == 201
        assert "workflow started" in response.text.lower()
        mock_create_tp.assert_called_once()
        mock_start_wf.assert_called_once()

    @patch("src.ingress.webhook_handler.start_workflow", new_callable=AsyncMock)
    @patch("src.ingress.webhook_handler.create_taskpacket", new_callable=AsyncMock)
    @patch("src.ingress.webhook_handler.is_duplicate", new_callable=AsyncMock)
    @patch("src.ingress.webhook_handler.get_webhook_secret", new_callable=AsyncMock)
    def test_dedupe_rejects_replayed_delivery(
        self, mock_get_secret, mock_is_dup, mock_create_tp, mock_start_wf
    ):
        """Replayed delivery ID is deduplicated, returns 200."""
        secret = "test-secret"
        mock_get_secret.return_value = secret
        mock_is_dup.return_value = True  # Already processed

        payload = _make_issue_payload()
        payload_bytes = json.dumps(payload).encode()
        signature = _sign_payload(payload_bytes, secret)

        client = TestClient(app)
        response = client.post(
            "/webhook/github",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Delivery": "already-seen-id",
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "issues",
            },
        )

        assert response.status_code == 200
        assert "duplicate" in response.text.lower()
        mock_create_tp.assert_not_called()
        mock_start_wf.assert_not_called()

    @patch("src.ingress.webhook_handler.get_webhook_secret", new_callable=AsyncMock)
    def test_non_issue_event_ignored(self, mock_get_secret):
        """Non-issue events (e.g., push) return 200 but are not processed."""
        secret = "test-secret"
        mock_get_secret.return_value = secret

        payload = {"repository": {"full_name": "acme/widgets"}, "ref": "refs/heads/main"}
        payload_bytes = json.dumps(payload).encode()
        signature = _sign_payload(payload_bytes, secret)

        client = TestClient(app)
        response = client.post(
            "/webhook/github",
            content=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Delivery": str(uuid4()),
                "X-Hub-Signature-256": signature,
                "X-GitHub-Event": "push",
            },
        )

        assert response.status_code == 200
        assert "not handled" in response.text.lower()
