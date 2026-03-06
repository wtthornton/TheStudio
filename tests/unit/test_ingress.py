"""Unit tests for Ingress (Story 0.1)."""

import hashlib
import hmac
import json
from datetime import UTC
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.ingress.signature import validate_signature


class TestSignatureValidation:
    def test_valid_signature(self) -> None:
        test_secret = "test-secret"  # noqa: S105
        payload = b'{"action": "opened"}'
        sig = "sha256=" + hmac.new(test_secret.encode(), payload, hashlib.sha256).hexdigest()
        assert validate_signature(payload, test_secret, sig) is True

    def test_invalid_signature(self) -> None:
        test_secret = "test-secret"  # noqa: S105
        payload = b'{"action": "opened"}'
        assert validate_signature(payload, test_secret, "sha256=wrong") is False

    def test_missing_sha256_prefix(self) -> None:
        assert validate_signature(b"test", "secret", "noprefixhash") is False

    def test_different_secret_fails(self) -> None:
        payload = b'{"action": "opened"}'
        sig = "sha256=" + hmac.new(b"secret-a", payload, hashlib.sha256).hexdigest()
        assert validate_signature(payload, "secret-b", sig) is False


class TestWebhookEndpoint:
    """Tests using FastAPI TestClient with mocked dependencies."""

    @pytest.fixture
    def webhook_secret(self) -> str:
        return "test-webhook-secret"

    @pytest.fixture
    def valid_payload(self) -> dict:
        return {
            "action": "opened",
            "issue": {"number": 42, "title": "Test issue"},
            "repository": {"full_name": "owner/repo"},
        }

    def _sign(self, payload: bytes, secret: str) -> str:
        return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    @pytest.fixture
    def client(self) -> TestClient:
        from src.app import app

        return TestClient(app)

    def test_missing_delivery_id(
        self, client: TestClient, valid_payload: dict, webhook_secret: str
    ) -> None:
        body = json.dumps(valid_payload).encode()
        response = client.post(
            "/webhook/github",
            content=body,
            headers={
                "X-Hub-Signature-256": self._sign(body, webhook_secret),
                "X-GitHub-Event": "issues",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 400

    def test_missing_signature(self, client: TestClient, valid_payload: dict) -> None:
        body = json.dumps(valid_payload).encode()
        response = client.post(
            "/webhook/github",
            content=body,
            headers={
                "X-GitHub-Delivery": str(uuid4()),
                "X-GitHub-Event": "issues",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 401

    @patch("src.ingress.webhook_handler.get_webhook_secret", new_callable=AsyncMock)
    def test_unknown_repo(
        self, mock_secret: AsyncMock, client: TestClient, valid_payload: dict, webhook_secret: str
    ) -> None:
        mock_secret.return_value = None
        body = json.dumps(valid_payload).encode()
        response = client.post(
            "/webhook/github",
            content=body,
            headers={
                "X-GitHub-Delivery": str(uuid4()),
                "X-Hub-Signature-256": self._sign(body, webhook_secret),
                "X-GitHub-Event": "issues",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 404

    @patch("src.ingress.webhook_handler.start_workflow", new_callable=AsyncMock)
    @patch("src.ingress.webhook_handler.get_webhook_secret", new_callable=AsyncMock)
    @patch("src.ingress.webhook_handler.is_duplicate", new_callable=AsyncMock)
    @patch("src.ingress.webhook_handler.create_taskpacket", new_callable=AsyncMock)
    def test_valid_new_webhook(
        self,
        mock_create: AsyncMock,
        mock_dedupe: AsyncMock,
        mock_secret: AsyncMock,
        mock_workflow: AsyncMock,
        client: TestClient,
        valid_payload: dict,
        webhook_secret: str,
    ) -> None:
        from datetime import datetime

        from src.models.taskpacket import TaskPacketRead, TaskPacketStatus

        tp_id = uuid4()
        mock_secret.return_value = webhook_secret
        mock_dedupe.return_value = False
        mock_create.return_value = TaskPacketRead(
            id=tp_id,
            repo="owner/repo",
            issue_id=42,
            delivery_id="test",
            correlation_id=uuid4(),
            status=TaskPacketStatus.RECEIVED,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_workflow.return_value = "run-id-123"

        body = json.dumps(valid_payload).encode()
        response = client.post(
            "/webhook/github",
            content=body,
            headers={
                "X-GitHub-Delivery": str(uuid4()),
                "X-Hub-Signature-256": self._sign(body, webhook_secret),
                "X-GitHub-Event": "issues",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 201
        mock_create.assert_called_once()
        mock_workflow.assert_called_once()

    @patch("src.ingress.webhook_handler.get_webhook_secret", new_callable=AsyncMock)
    @patch("src.ingress.webhook_handler.is_duplicate", new_callable=AsyncMock)
    def test_duplicate_webhook(
        self,
        mock_dedupe: AsyncMock,
        mock_secret: AsyncMock,
        client: TestClient,
        valid_payload: dict,
        webhook_secret: str,
    ) -> None:
        mock_secret.return_value = webhook_secret
        mock_dedupe.return_value = True

        body = json.dumps(valid_payload).encode()
        response = client.post(
            "/webhook/github",
            content=body,
            headers={
                "X-GitHub-Delivery": str(uuid4()),
                "X-Hub-Signature-256": self._sign(body, webhook_secret),
                "X-GitHub-Event": "issues",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 200

    @patch("src.ingress.webhook_handler.get_webhook_secret", new_callable=AsyncMock)
    def test_invalid_signature_returns_401(
        self, mock_secret: AsyncMock, client: TestClient, valid_payload: dict, webhook_secret: str
    ) -> None:
        mock_secret.return_value = webhook_secret

        body = json.dumps(valid_payload).encode()
        response = client.post(
            "/webhook/github",
            content=body,
            headers={
                "X-GitHub-Delivery": str(uuid4()),
                "X-Hub-Signature-256": "sha256=invalid",
                "X-GitHub-Event": "issues",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 401

    @patch("src.ingress.webhook_handler.get_webhook_secret", new_callable=AsyncMock)
    def test_non_issue_event(
        self, mock_secret: AsyncMock, client: TestClient, valid_payload: dict, webhook_secret: str
    ) -> None:
        mock_secret.return_value = webhook_secret

        body = json.dumps(valid_payload).encode()
        response = client.post(
            "/webhook/github",
            content=body,
            headers={
                "X-GitHub-Delivery": str(uuid4()),
                "X-Hub-Signature-256": self._sign(body, webhook_secret),
                "X-GitHub-Event": "push",
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 200
