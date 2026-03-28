"""Playwright fixtures: browser, page, base_url, console_errors, stack readiness.

Tests run against the same running app as tests/docker/ (e.g. Docker Compose).
"""

import os
from pathlib import Path

import httpx
import pytest

DEFAULT_BASE_URL = "http://localhost:9080"  # default to theStudio-prod local endpoint


def _load_infra_env() -> dict[str, str]:
    """Best-effort loader for infra/.env values used by local prod test runs."""
    repo_root = Path(__file__).resolve().parents[2]
    env_path = repo_root / "infra" / ".env"
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


_INFRA_ENV = _load_infra_env()


def _get_env(name: str) -> str | None:
    """Get env var from process, then infra/.env fallback."""
    return os.environ.get(name) or _INFRA_ENV.get(name)


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


@pytest.fixture(scope="session")
def playwright_user_id() -> str:
    """User identity header for admin UI auth.

    Most admin UI routes require X-User-ID. Override with PLAYWRIGHT_USER_ID.
    """
    return _get_env("PLAYWRIGHT_USER_ID") or "admin"


@pytest.fixture(scope="session")
def browser_context_args(
    browser_context_args: dict, playwright_user_id: str
) -> dict:
    """Provide auth defaults for Playwright browser contexts.

    - Adds X-User-ID header for app-level admin auth.
    - Adds optional HTTP Basic credentials for reverse-proxy auth.
      Uses PLAYWRIGHT_HTTP_USER / PLAYWRIGHT_HTTP_PASSWORD first, then
      ADMIN_USER / ADMIN_PASSWORD as fallback.
    """
    context_args = dict(browser_context_args)

    # App-level auth expected by /admin/ui routes.
    extra_headers = dict(context_args.get("extra_http_headers", {}))
    extra_headers["X-User-ID"] = playwright_user_id
    context_args["extra_http_headers"] = extra_headers

    # Optional front-door auth (e.g. Caddy basic_auth on prod stack).
    http_user = _get_env("PLAYWRIGHT_HTTP_USER") or _get_env("ADMIN_USER")
    http_password = _get_env("PLAYWRIGHT_HTTP_PASSWORD") or _get_env("ADMIN_PASSWORD")
    if http_user and http_password:
        context_args["http_credentials"] = {
            "username": http_user,
            "password": http_password,
        }

    return context_args


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
    """Navigate to URL and assert response is valid.

    Uses ``load`` (not ``networkidle``): React/HTMX SPAs and long-lived connections
    often prevent *networkidle* from ever firing, which caused 30s timeouts.
    """
    response = page.goto(url, wait_until="load")
    assert response is not None, f"No response from {url}"
    assert response.status == 200, f"{url} returned status {response.status}"
    page.wait_for_load_state("load")


@pytest.fixture
def console_errors(page) -> list:
    """Capture console.error messages for the current page. Append to list as they occur."""
    errors: list = []

    def on_console(msg: object) -> None:
        if getattr(msg, "type", None) == "error":
            errors.append(getattr(msg, "text", str(msg)))

    page.on("console", on_console)
    return errors
