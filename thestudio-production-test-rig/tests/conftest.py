"""Fixtures for production test rig.

Loads config from environment (or .env). Skips all tests if the deployment
is unreachable. Provides HTTP client.
"""

import os

import httpx
import pytest
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.environ.get("THESTUDIO_BASE_URL", "https://localhost:9443").rstrip("/")
INSECURE_TLS = os.environ.get("THESTUDIO_INSECURE_TLS", "").strip() == "1"
# Must match TheStudio's DEV_MODE_USER_ID when deployment uses mock provider (for auto-provision).
ADMIN_USER = os.environ.get("THESTUDIO_ADMIN_USER", "dev-admin@localhost")


def _stack_is_running() -> bool:
    try:
        r = httpx.get(
            f"{BASE_URL}/healthz",
            timeout=5,
            verify=not INSECURE_TLS,
        )
        return r.status_code == 200
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout):
        return False


@pytest.fixture(scope="session", autouse=True)
def require_deployment() -> None:
    if not _stack_is_running():
        pytest.skip(
            f"Deployment not reachable at {BASE_URL}. "
            "Set THESTUDIO_BASE_URL and ensure the deployment is running."
        )


@pytest.fixture(scope="session")
def http_client() -> httpx.Client:
    headers = {"X-User-ID": ADMIN_USER}
    with httpx.Client(
        base_url=BASE_URL,
        timeout=15,
        verify=not INSECURE_TLS,
        headers=headers,
    ) as client:
        yield client
