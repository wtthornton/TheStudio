"""Shared fixtures for Docker stack smoke tests.

Session-scoped readiness gate: skips all docker-marked tests if the
stack is not running. Also provides helpers for webhook HMAC signing
and repo registration via the admin API.
"""

import hashlib
import hmac
import os
import pathlib
import subprocess
import uuid

import httpx
import pytest

BASE_URL = "http://localhost:8000"
WEBHOOK_SECRET = "test-webhook-secret"


def _stack_is_running() -> bool:
    """Quick check: can we reach the app healthz endpoint?"""
    try:
        r = httpx.get(f"{BASE_URL}/healthz", timeout=3)
        return r.status_code == 200
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
        return False


@pytest.fixture(scope="session", autouse=True)
def require_docker_stack(request: pytest.FixtureRequest) -> None:
    """Skip all docker-marked tests if the stack is not reachable."""
    if not _stack_is_running():
        pytest.skip("Docker Compose stack is not running (healthz unreachable)")


@pytest.fixture(scope="session")
def http_client() -> httpx.Client:
    """Session-scoped httpx client pointed at the running stack."""
    with httpx.Client(base_url=BASE_URL, timeout=10) as client:
        yield client  # type: ignore[misc]


def compute_signature(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    """Compute GitHub-style HMAC-SHA256 signature for a payload."""
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


def make_issue_payload(
    owner: str = "test-org",
    repo: str = "test-repo",
    issue_number: int = 1,
    action: str = "opened",
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
            "number": issue_number,
            "title": "Smoke test issue",
            "body": "Created by Docker smoke test",
            "state": "open",
            "user": {"login": "smoke-tester"},
        },
        "sender": {"login": "smoke-tester"},
    }


@pytest.fixture(scope="session")
def registered_repo(http_client: httpx.Client) -> dict:
    """Register a test repo via admin API (dev-mode auto-auth, no headers needed).

    Returns the registration response dict. Tolerates 409 (already registered).
    """
    payload = {
        "owner": "test-org",
        "repo": "test-repo",
        "installation_id": 12345,
        "default_branch": "main",
    }
    r = http_client.post("/admin/repos", json=payload)
    if r.status_code == 201:
        return r.json()
    if r.status_code == 409:
        # Already registered from a previous run — that's fine
        return payload
    r.raise_for_status()
    return {}  # unreachable, keeps type checker happy


COMPOSE_PROJECT = os.environ.get("COMPOSE_PROJECT_NAME", "")


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def docker_compose_cmd(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a docker compose command against the dev stack.

    Uses COMPOSE_PROJECT_NAME env var if set (CI sets 'thestudio-smoke'),
    otherwise uses the default project name derived from the directory.
    Always runs from the repository root so docker-compose.dev.yml is found
    regardless of the caller's working directory.
    """
    cmd = ["docker", "compose", "-f", "docker-compose.dev.yml"]
    if COMPOSE_PROJECT:
        cmd.extend(["-p", COMPOSE_PROJECT])
    cmd.extend(args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(REPO_ROOT),
    )
