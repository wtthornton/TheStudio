"""Playwright fixtures: browser, page, base_url, console_errors, stack readiness.

Tests run against the same running app as tests/docker/ (e.g. Docker Compose).
"""

import os

import httpx
import pytest

DEFAULT_BASE_URL = "http://localhost:8000"  # matches docker-compose.dev.yml app port


def _stack_is_running(base_url: str = DEFAULT_BASE_URL) -> bool:
    """Return True if the app healthz endpoint is reachable."""
    try:
        r = httpx.get(f"{base_url.rstrip('/')}/healthz", timeout=3)
        return r.status_code == 200
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
        return False


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL for the app (e.g. http://localhost:8000). Configurable via PLAYWRIGHT_BASE_URL."""
    return os.environ.get("PLAYWRIGHT_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


@pytest.fixture(scope="session", autouse=True)
def _require_playwright_stack(base_url: str) -> None:
    """Skip all Playwright tests if the app stack is not reachable."""
    if not _stack_is_running(base_url):
        pytest.skip(
            "App stack is not running (healthz unreachable). "
            "Start the stack (e.g. docker compose -f docker-compose.dev.yml up -d) "
            "and ensure port 8000 is available (or set PLAYWRIGHT_BASE_URL)."
        )


def navigate(page, url: str) -> None:
    """Navigate to URL and assert response is valid. Waits for network idle."""
    response = page.goto(url)
    assert response is not None, f"No response from {url}"
    assert response.status == 200, f"{url} returned status {response.status}"
    page.wait_for_load_state("networkidle")


@pytest.fixture
def console_errors(page) -> list:
    """Capture console.error messages for the current page. Append to list as they occur."""
    errors: list = []

    def on_console(msg: object) -> None:
        if getattr(msg, "type", None) == "error":
            errors.append(getattr(msg, "text", str(msg)))

    page.on("console", on_console)
    return errors
