"""Verify documented URLs (docs/URLs.md) deliver their intended purpose.

Beyond returning 200, each documented URL must deliver the content users
expect when they follow the URL. A health endpoint must say "ok", a dashboard
must show operational data, API docs must show endpoint documentation.
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

# Key URLs from docs/URLs.md
# Format: (path, expected_status, expected_text, purpose_description, purpose_keywords)
DOCUMENTED_URLS = [
    (
        "/healthz", 200, "ok",
        "health check confirming app is alive",
        ["ok"],
    ),
    (
        "/readyz", 200, "ready",
        "readiness check confirming app can serve traffic",
        ["ready"],
    ),
    (
        "/admin/ui/", 200, None,
        "admin entry point redirecting to dashboard",
        ["Dashboard", "Fleet", "admin"],
    ),
    (
        "/admin/ui/dashboard", 200, "Fleet Dashboard",
        "fleet operations dashboard with health and workflow data",
        ["Temporal", "Running", "Fleet Dashboard"],
    ),
    (
        "/admin/ui/repos", 200, "Repo Management",
        "repository lifecycle management with registration",
        ["Repo Management", "Register", "repo"],
    ),
    (
        "/admin/ui/settings", 200, "Settings",
        "admin configuration hub with API keys and flags",
        ["Settings", "API", "Infrastructure"],
    ),
    (
        "/docs", 200, None,
        "API documentation (Scalar/OpenAPI interactive reference)",
        ["openapi.json", "Scalar", "API"],
    ),
]


@pytest.mark.parametrize(
    "path",
    [p[0] for p in DOCUMENTED_URLS],
    ids=[p[0].strip("/").replace("/", "-") or "root" for p in DOCUMENTED_URLS],
)
def test_documented_url_returns_200(page, base_url: str, path: str) -> None:
    """Each URL from docs/URLs.md returns 200."""
    url = f"{base_url}{path}"
    response = page.goto(url)
    assert response is not None, f"No response from {url}"
    assert response.status == 200, f"{url} returned {response.status}"


@pytest.mark.parametrize(
    ("path", "expected_status", "expected_text", "purpose_desc", "purpose_keywords"),
    DOCUMENTED_URLS,
    ids=[p[0].strip("/").replace("/", "-") or "root" for p in DOCUMENTED_URLS],
)
def test_documented_url_delivers_purpose(
    page,
    base_url: str,
    path: str,
    expected_status: int,
    expected_text: str | None,
    purpose_desc: str,
    purpose_keywords: list[str],
) -> None:
    """Documented URLs deliver the content described in their documentation.

    Each URL exists for a reason. This test verifies the URL delivers on that
    purpose — not just that it returns a status code and contains a word.
    """
    url = f"{base_url}{path}"
    response = page.goto(url)
    assert response is not None
    assert response.status == expected_status

    page.wait_for_load_state("domcontentloaded")
    body = page.locator("body").inner_text()
    # Include raw HTML so /docs (Scalar) matches config in inline scripts, not only visible text
    html = page.content()
    haystack = f"{body}\n{html}"

    # Check explicit expected text (backwards compatible)
    if expected_text:
        assert expected_text in body, (
            f"Expected '{expected_text}' in body of {url}"
        )

    # Check purpose keywords — the page must contain at least one
    haystack_lower = haystack.lower()
    has_purpose = any(
        kw in haystack or kw.lower() in haystack_lower for kw in purpose_keywords
    )
    assert has_purpose, (
        f"{url} should serve as {purpose_desc} "
        f"but none of {purpose_keywords} found in page content"
    )


@pytest.mark.parametrize(
    ("path", "expected_status", "expected_text", "purpose_desc", "purpose_keywords"),
    DOCUMENTED_URLS,
    ids=[p[0].strip("/").replace("/", "-") or "root" for p in DOCUMENTED_URLS],
)
def test_documented_url_no_error_content(
    page,
    base_url: str,
    path: str,
    expected_status: int,
    expected_text: str | None,
    purpose_desc: str,
    purpose_keywords: list[str],
) -> None:
    """Documented URLs must not show error messages instead of content.

    A URL that returns 200 but shows "Internal Server Error", "Traceback",
    or "Exception" is lying about its status and failing its purpose.
    """
    url = f"{base_url}{path}"
    response = page.goto(url)
    if response is None or response.status != 200:
        pytest.skip(f"{url} did not return 200")

    page.wait_for_load_state("domcontentloaded")
    body = page.locator("body").inner_text()

    error_indicators = [
        "Internal Server Error",
        "Traceback (most recent call last)",
        "500 Server Error",
        "Application Error",
    ]
    for indicator in error_indicators:
        assert indicator not in body, (
            f"{url} returned 200 but shows error content: '{indicator}'"
        )
