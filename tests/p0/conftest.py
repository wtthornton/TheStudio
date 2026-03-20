"""Shared fixtures for P0 deployment-mode tests.

All P0 tests hit the deployed Docker stack through Caddy (HTTPS, port 9443).
Admin endpoints require HTTP Basic Auth; webhook endpoints do not.

Fixtures provided:
  - ``require_healthy_docker_stack``: Session-scoped health gate (auto-use).
  - ``p0_client``: httpx client with Caddy base URL + Basic Auth.
  - ``p0_base_url``: The Caddy HTTPS base URL.
  - ``registered_test_repo``: Register a test repo via admin API.
  - ``webhook_headers``: Build HMAC-signed GitHub webhook headers.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import uuid

import httpx
import pytest

from tests.p0.health import check_stack_health

# ---------------------------------------------------------------------------
# Configuration from environment (sourced from infra/.env by runner script)
# ---------------------------------------------------------------------------
BASE_URL = os.environ.get("P0_BASE_URL", "https://localhost:9443")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
WEBHOOK_SECRET = os.environ.get("THESTUDIO_WEBHOOK_SECRET", "")


# ---------------------------------------------------------------------------
# Health gate — skip all P0 tests if stack is not healthy
# ---------------------------------------------------------------------------
_stack_healthy: bool | None = None


def _check_once() -> bool:
    """Lazy singleton: check stack health exactly once per session."""
    global _stack_healthy  # noqa: PLW0603
    if _stack_healthy is None:
        report = check_stack_health(
            base_url=BASE_URL,
            admin_user=ADMIN_USER,
            admin_password=ADMIN_PASSWORD,
        )
        _stack_healthy = report.all_healthy
        if not _stack_healthy:
            # Store summary for skip message
            _check_once.summary = report.summary()  # type: ignore[attr-defined]
    return _stack_healthy


@pytest.fixture(autouse=True)
def _skip_p0_if_stack_down(request: pytest.FixtureRequest) -> None:
    """Skip tests marked ``p0`` if the Docker stack is unhealthy.

    Pure unit tests (no ``p0`` mark) run regardless of stack state.
    """
    if "p0" in [m.name for m in request.node.iter_markers()]:
        if not _check_once():
            summary = getattr(_check_once, "summary", "unknown")
            pytest.skip(
                f"Docker stack not healthy — skipping P0 test.\n{summary}"
            )


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def p0_base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def p0_client() -> httpx.Client:
    """Session-scoped httpx client with Caddy base URL and Basic Auth."""
    with httpx.Client(
        base_url=BASE_URL,
        verify=False,
        timeout=30,
        auth=(ADMIN_USER, ADMIN_PASSWORD),
    ) as client:
        yield client  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Webhook helpers (reuses patterns from tests/docker/conftest.py)
# ---------------------------------------------------------------------------
def compute_signature(body: bytes, secret: str | None = None) -> str:
    """Compute GitHub-style HMAC-SHA256 signature for a payload."""
    secret = secret or WEBHOOK_SECRET
    mac = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={mac}"


def build_webhook_headers(
    body: bytes,
    event: str = "issues",
    delivery_id: str | None = None,
) -> dict[str, str]:
    """Build the full set of GitHub webhook headers for a payload."""
    return {
        "X-GitHub-Delivery": delivery_id or str(uuid.uuid4()),
        "X-GitHub-Event": event,
        "X-Hub-Signature-256": compute_signature(body),
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Repo registration
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def registered_test_repo(p0_client: httpx.Client) -> dict:
    """Register a test repo via admin API. Tolerates 409 (already registered)."""
    payload = {
        "owner": "p0-test-org",
        "repo": "p0-test-repo",
        "installation_id": 99999,
        "default_branch": "main",
    }
    r = p0_client.post("/admin/repos", json=payload)
    if r.status_code == 201:
        return r.json()
    if r.status_code == 409:
        return payload
    r.raise_for_status()
    return {}


def make_issue_payload(
    owner: str = "p0-test-org",
    repo: str = "p0-test-repo",
    issue_number: int | None = None,
    action: str = "opened",
    title: str = "P0 deployment test issue",
    body: str = "Created by P0 deployment test harness",
) -> dict:
    """Build a minimal but valid GitHub issues webhook payload."""
    return {
        "action": action,
        "repository": {
            "full_name": f"{owner}/{repo}",
            "name": repo,
            "owner": {"login": owner},
        },
        "issue": {
            "number": issue_number or int(uuid.uuid4().int % 90000 + 10000),
            "title": title,
            "body": body,
            "state": "open",
            "user": {"login": "p0-tester"},
            "labels": [{"name": "agent:run"}],
        },
        "sender": {"login": "p0-tester"},
    }
