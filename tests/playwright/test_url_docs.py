"""Verify documented URLs (docs/URLs.md) return expected status and content.

Run with dev stack: docker compose -f docker-compose.dev.yml up -d
Base URL default: http://localhost:8000 (PLAYWRIGHT_BASE_URL for prod).
"""

import pytest

pytestmark = pytest.mark.playwright

# Key URLs from docs/URLs.md — path -> (expected status, text or None)
DOCUMENTED_URLS = [
    ("/healthz", 200, "ok"),
    ("/readyz", 200, "ready"),
    ("/admin/ui/", 200, None),  # redirect or dashboard
    ("/admin/ui/dashboard", 200, "Fleet Dashboard"),
    ("/admin/ui/repos", 200, "Repo Management"),
    ("/admin/ui/settings", 200, "Settings"),
    ("/docs", 200, None),  # Swagger UI
]


@pytest.mark.parametrize("path", [p[0] for p in DOCUMENTED_URLS])
def test_documented_url_returns_200(page, base_url: str, path: str) -> None:
    """Each URL from docs/URLs.md returns 200."""
    url = f"{base_url}{path}"
    response = page.goto(url)
    assert response is not None, f"No response from {url}"
    assert response.status == 200, f"{url} returned {response.status}"


@pytest.mark.parametrize(("path", "expected_status", "expected_text"), DOCUMENTED_URLS)
def test_documented_url_content(
    page, base_url: str, path: str, expected_status: int, expected_text: str | None
) -> None:
    """Documented URLs return expected status and contain expected text when specified."""
    url = f"{base_url}{path}"
    response = page.goto(url)
    assert response is not None
    assert response.status == expected_status
    if expected_text:
        page.wait_for_load_state("domcontentloaded")
        body = page.locator("body").inner_text()
        assert expected_text in body, f"Expected '{expected_text}' in body of {url}"
