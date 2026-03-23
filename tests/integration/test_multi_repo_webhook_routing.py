"""Integration tests for multi-repo webhook routing (Epic 41, Story 41.3).

Verifies that:
- Webhooks for Repo A (signed with Repo A's secret) are accepted and create a
  TaskPacket with repo="owner-a/repo-alpha".
- Webhooks for Repo B (signed with Repo B's secret) are accepted and create a
  TaskPacket with repo="owner-b/repo-beta".
- A webhook with Repo A's secret but Repo B's payload is rejected (401).
- A webhook for an unregistered repo returns 404.
- Each TaskPacket has the correct ``repo`` field — no cross-repo contamination.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.app import app
from src.db.base import Base
from src.db.connection import get_session
from src.models.taskpacket_crud import get_by_repo_and_issue
from src.settings import settings

pytestmark = pytest.mark.integration

# Two repos with distinct webhook secrets
_SECRET_A = "secret-for-repo-alpha-xkcd"
_SECRET_B = "secret-for-repo-beta-zxcv"
_REPO_A_OWNER = "owner-a"
_REPO_A_NAME = "repo-alpha"
_REPO_B_OWNER = "owner-b"
_REPO_B_NAME = "repo-beta"
_REPO_A_FULL = f"{_REPO_A_OWNER}/{_REPO_A_NAME}"
_REPO_B_FULL = f"{_REPO_B_OWNER}/{_REPO_B_NAME}"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sign(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 signature in GitHub format (sha256=...)."""
    mac = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={mac}"


def _make_issues_payload(owner: str, repo: str, issue_number: int = 1) -> dict:
    """Build a minimal GitHub issues event payload."""
    return {
        "action": "opened",
        "issue": {
            "number": issue_number,
            "title": f"Test issue {issue_number} for {owner}/{repo}",
            "body": "Body text with agent:run label semantics.",
            "labels": [{"name": "agent:run"}],
        },
        "repository": {
            "full_name": f"{owner}/{repo}",
            "name": repo,
            "owner": {"login": owner},
        },
    }


def _send_webhook(http_client, payload: dict, secret: str):
    """Helper: send a signed issues webhook and return the coroutine."""
    body = json.dumps(payload).encode()
    sig = _sign(body, secret)
    return http_client.post(
        "/webhook/github",
        content=body,
        headers={
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": f"delivery-{uuid4().hex}",
            "X-Hub-Signature-256": sig,
            "Content-Type": "application/json",
        },
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_engine():
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess


@pytest.fixture
async def http_client(db_engine, monkeypatch: pytest.MonkeyPatch):
    """HTTP client wired to the app with real DB, no auth."""
    monkeypatch.setattr(settings, "dashboard_token", "")
    monkeypatch.setattr(settings, "llm_provider", "mock")
    # Enable triage mode so no Temporal workflow is needed
    monkeypatch.setattr(settings, "triage_mode_enabled", True)
    monkeypatch.setattr(settings, "webhook_secret", "global-fallback-secret")

    factory = async_sessionmaker(db_engine, expire_on_commit=False)

    async def _override_get_session():
        async with factory() as sess:
            yield sess

    app.dependency_overrides[get_session] = _override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def registered_repos(http_client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    """Register both test repos and patch the per-repo secret lookup.

    The webhook handler calls ``get_webhook_secret(session, owner, repo_name)``
    which reads from the ``repo_profile`` table.  We patch the function to
    return per-repo test secrets without needing encrypted storage.
    """
    monkeypatch.setattr(settings, "webhook_secret", _SECRET_A)
    await http_client.post("/admin/repos", json={
        "owner": _REPO_A_OWNER,
        "repo": _REPO_A_NAME,
        "installation_id": 111,
        "default_branch": "main",
    })
    monkeypatch.setattr(settings, "webhook_secret", _SECRET_B)
    await http_client.post("/admin/repos", json={
        "owner": _REPO_B_OWNER,
        "repo": _REPO_B_NAME,
        "installation_id": 222,
        "default_branch": "main",
    })

    # Patch get_webhook_secret to return per-repo test secrets
    async def _mock_get_webhook_secret(session, owner: str, repo_name: str) -> str | None:
        if owner == _REPO_A_OWNER and repo_name == _REPO_A_NAME:
            return _SECRET_A
        if owner == _REPO_B_OWNER and repo_name == _REPO_B_NAME:
            return _SECRET_B
        return None

    monkeypatch.setattr(
        "src.ingress.webhook_handler.get_webhook_secret",
        _mock_get_webhook_secret,
    )

    # Patch emit_triage_created to avoid NATS
    monkeypatch.setattr(
        "src.dashboard.events_publisher.emit_triage_created",
        AsyncMock(return_value=None),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMultiRepoWebhookRouting:
    """Webhook events are routed to the correct repo profile."""

    async def test_webhook_repo_a_accepted_and_creates_taskpacket(
        self,
        http_client: AsyncClient,
        registered_repos,
        session: AsyncSession,
    ) -> None:
        """A valid webhook for Repo A creates a TaskPacket with repo=Repo A."""
        payload = _make_issues_payload(_REPO_A_OWNER, _REPO_A_NAME, issue_number=10)
        resp = await _send_webhook(http_client, payload, _SECRET_A)
        assert resp.status_code in (200, 201)

        task = await get_by_repo_and_issue(session, _REPO_A_FULL, 10)
        assert task is not None
        assert task.repo == _REPO_A_FULL

    async def test_webhook_repo_b_accepted_and_creates_taskpacket(
        self,
        http_client: AsyncClient,
        registered_repos,
        session: AsyncSession,
    ) -> None:
        """A valid webhook for Repo B creates a TaskPacket with repo=Repo B."""
        payload = _make_issues_payload(_REPO_B_OWNER, _REPO_B_NAME, issue_number=20)
        resp = await _send_webhook(http_client, payload, _SECRET_B)
        assert resp.status_code in (200, 201)

        task = await get_by_repo_and_issue(session, _REPO_B_FULL, 20)
        assert task is not None
        assert task.repo == _REPO_B_FULL

    async def test_repo_a_secret_with_repo_b_payload_rejected(
        self,
        http_client: AsyncClient,
        registered_repos,
    ) -> None:
        """Signing Repo B's payload with Repo A's secret returns 401."""
        payload = _make_issues_payload(_REPO_B_OWNER, _REPO_B_NAME, issue_number=30)
        # Wrong: sign with Repo A's secret even though payload belongs to Repo B
        resp = await _send_webhook(http_client, payload, _SECRET_A)
        assert resp.status_code == 401

    async def test_unregistered_repo_returns_404(
        self,
        http_client: AsyncClient,
        registered_repos,
    ) -> None:
        """A webhook for a repo not in the database returns 404."""
        payload = _make_issues_payload("unregistered-org", "unknown-repo", issue_number=99)
        resp = await _send_webhook(http_client, payload, "any-secret")
        assert resp.status_code == 404

    async def test_no_cross_repo_taskpacket_contamination(
        self,
        http_client: AsyncClient,
        registered_repos,
        session: AsyncSession,
    ) -> None:
        """TaskPackets for Repo A and Repo B do not mix repos."""
        # Fire webhook for Repo A
        payload_a = _make_issues_payload(_REPO_A_OWNER, _REPO_A_NAME, issue_number=100)
        await _send_webhook(http_client, payload_a, _SECRET_A)

        # Fire webhook for Repo B
        payload_b = _make_issues_payload(_REPO_B_OWNER, _REPO_B_NAME, issue_number=200)
        await _send_webhook(http_client, payload_b, _SECRET_B)

        # Verify each task has the correct repo — no cross-contamination
        task_a = await get_by_repo_and_issue(session, _REPO_A_FULL, 100)
        task_b = await get_by_repo_and_issue(session, _REPO_B_FULL, 200)

        assert task_a is not None
        assert task_a.repo == _REPO_A_FULL
        assert task_b is not None
        assert task_b.repo == _REPO_B_FULL
        # Verify repo B's issue is NOT stored under repo A's full_name
        assert await get_by_repo_and_issue(session, _REPO_A_FULL, 200) is None

    async def test_missing_signature_header_rejected(
        self,
        http_client: AsyncClient,
        registered_repos,
    ) -> None:
        """A webhook without X-Hub-Signature-256 header returns 401."""
        payload = _make_issues_payload(_REPO_A_OWNER, _REPO_A_NAME)
        body = json.dumps(payload).encode()
        resp = await http_client.post(
            "/webhook/github",
            content=body,
            headers={
                "X-GitHub-Event": "issues",
                "X-GitHub-Delivery": f"delivery-{uuid4().hex}",
                # No X-Hub-Signature-256
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 401
