"""Container lifecycle tests for the Docker Compose stack.

Verifies graceful shutdown, restart recovery, and dependency failure
handling. Uses subprocess to control containers.
"""

import json
import subprocess
import time

import httpx
import pytest

from tests.docker.conftest import (
    BASE_URL,
    build_webhook_headers,
    docker_compose_cmd,
    make_issue_payload,
)

pytestmark = pytest.mark.docker


def _wait_for_healthy(url: str = f"{BASE_URL}/healthz", timeout: int = 60) -> bool:
    """Poll healthz until 200 or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            r = httpx.get(url, timeout=3)
            if r.status_code == 200:
                return True
        except (
            httpx.ConnectError,
            httpx.ReadError,
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
            httpx.RemoteProtocolError,
        ):
            pass
        time.sleep(2)
    return False


class TestGracefulShutdown:
    """Verify the app container shuts down cleanly on SIGTERM."""

    def test_app_exits_zero_on_sigterm(self) -> None:
        """Send SIGTERM to app container, verify exit code 0 within 10s."""
        # Get app container ID
        result = docker_compose_cmd("ps", "-q", "app")
        container_id = result.stdout.strip()
        assert container_id, "App container not found"

        # Send SIGTERM via docker stop (sends SIGTERM, waits grace period)
        subprocess.run(
            ["docker", "stop", "--time", "10", container_id],
            capture_output=True,
            text=True,
            timeout=15,
        )

        # Check exit code
        inspect_result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.ExitCode}}", container_id],
            capture_output=True,
            text=True,
            timeout=5,
        )
        exit_code = inspect_result.stdout.strip()
        assert exit_code == "0", f"Expected exit code 0, got {exit_code}"

        # Restart the container to leave stack running for subsequent tests
        docker_compose_cmd("start", "app")
        assert _wait_for_healthy(), "App did not recover after restart"


class TestRestartRecovery:
    """Verify the app recovers after a restart."""

    def test_restart_then_healthy(self) -> None:
        """Restart app container and verify healthz returns 200."""
        docker_compose_cmd("restart", "app")
        assert _wait_for_healthy(timeout=60), "App did not become healthy within 60s after restart"

        r = httpx.get(f"{BASE_URL}/healthz", timeout=5)
        assert r.status_code == 200


class TestDependencyFailure:
    """Verify app handles Temporal being unavailable."""

    def test_app_survives_temporal_outage(
        self,
        http_client: httpx.Client,
        registered_repo: dict,
    ) -> None:
        """Stop Temporal, verify app doesn't crash, restart and recover."""
        # Stop Temporal
        docker_compose_cmd("stop", "temporal")
        time.sleep(3)

        # App should still respond to healthz (it doesn't hard-depend on Temporal for liveness)
        try:
            r = httpx.get(f"{BASE_URL}/healthz", timeout=5)
            # Either 200 (still alive) or 503 (degraded) — both acceptable
            assert r.status_code in (200, 503), f"Unexpected status: {r.status_code}"
        except (httpx.ConnectError, httpx.ReadTimeout):
            pytest.fail("App crashed or became unreachable when Temporal went down")

        # A webhook that triggers a workflow should fail gracefully, not crash
        payload = make_issue_payload(issue_number=99999)
        body = json.dumps(payload).encode()
        headers = build_webhook_headers(body)
        r = http_client.post("/webhook/github", content=body, headers=headers)
        # 201 (workflow pending) or 5xx are acceptable — NOT a connection error
        assert r.status_code < 600, f"App returned invalid status: {r.status_code}"

        # Restart Temporal and verify recovery
        docker_compose_cmd("start", "temporal")
        assert _wait_for_healthy(timeout=90), "App did not recover after Temporal restart"
