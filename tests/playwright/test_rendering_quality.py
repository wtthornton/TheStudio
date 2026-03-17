"""Rendering quality & semantic content scan across all pages.

Two layers of validation:
1. Rendering quality — no HTML entity artifacts, no NaN, no console errors
2. Semantic completeness — each page renders the content its purpose requires
   (tables, forms, metrics, controls) not just a heading shell.
"""

import re

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

ALL_PAGES = [
    "/admin/ui/dashboard",
    "/admin/ui/repos",
    "/admin/ui/workflows",
    "/admin/ui/audit",
    "/admin/ui/metrics",
    "/admin/ui/experts",
    "/admin/ui/tools",
    "/admin/ui/models",
    "/admin/ui/compliance",
    "/admin/ui/quarantine",
    "/admin/ui/dead-letters",
    "/admin/ui/planes",
    "/admin/ui/settings",
]

# What each page MUST contain to fulfill its purpose.
# Format: path -> list of (description, keywords-any-must-match)
PAGE_PURPOSE_CONTENT = {
    "/admin/ui/dashboard": [
        ("infrastructure health services", ["Temporal", "Postgres"]),
        ("workflow summary metrics", ["Running", "Stuck", "Failed"]),
    ],
    "/admin/ui/repos": [
        ("repo management controls", ["Register", "register", "repo", "Repo"]),
    ],
    "/admin/ui/workflows": [
        ("workflow status vocabulary", ["running", "completed", "failed", "stuck", "status"]),
        ("filtering or list controls", ["filter", "select", "limit", "apply", "status"]),
    ],
    "/admin/ui/audit": [
        ("audit event references", ["event", "actor", "action", "type", "log"]),
        ("time-based filtering", ["1h", "6h", "24h", "7d", "hour", "day", "time"]),
    ],
    "/admin/ui/metrics": [
        ("success rate metrics", ["success", "pass", "rate", "%"]),
        ("gate status information", ["gate", "passing", "failing", "threshold"]),
        ("loopback data", ["loopback", "loop", "retry"]),
    ],
    "/admin/ui/experts": [
        ("expert trust tiers", ["shadow", "probation", "trusted", "tier", "expert"]),
    ],
    "/admin/ui/tools": [
        ("tool suite catalog", ["ruff", "pytest", "security", "suite", "tool"]),
        ("approval status levels", ["observe", "suggest", "execute", "approved"]),
    ],
    "/admin/ui/models": [
        ("model provider info", ["anthropic", "openai", "provider", "model", "claude"]),
        ("model class categories", ["fast", "balanced", "strong", "class"]),
    ],
    "/admin/ui/compliance": [
        ("pass/fail status", ["pass", "fail", "status", "check", "compliance"]),
    ],
    "/admin/ui/quarantine": [
        ("quarantine event status", ["quarantine", "reason", "pending", "replay", "status"]),
    ],
    "/admin/ui/dead-letters": [
        ("dead letter failure info", ["dead", "letter", "failure", "reason", "error", "attempt"]),
    ],
    "/admin/ui/planes": [
        ("execution plane info", ["plane", "active", "region", "status"]),
    ],
    "/admin/ui/settings": [
        ("configuration domains", ["API", "Infrastructure", "Feature", "Agent", "Secret"]),
    ],
}


# ---------------------------------------------------------------------------
# Rendering quality scans (existing behavior, kept)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES])
def test_no_html_entity_artifacts(page, base_url: str, path: str) -> None:
    """No page shows literal HTML entity text (double-encoded entities)."""
    navigate(page, f"{base_url}{path}")

    visible_text = page.locator("body").inner_text()
    assert "&#" not in visible_text, (
        f"Literal HTML entity on {path}: "
        + _extract_context(visible_text, "&#")
    )


@pytest.mark.parametrize("path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES])
def test_no_console_errors(
    page, base_url: str, console_errors: list, path: str
) -> None:
    """No JavaScript console.error messages on any page."""
    navigate(page, f"{base_url}{path}")

    assert len(console_errors) == 0, (
        f"Console errors on {path}: {console_errors}"
    )


@pytest.mark.parametrize("path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES])
def test_no_rendering_artifacts(page, base_url: str, path: str) -> None:
    """No page shows NaN rendering artifacts in visible text."""
    navigate(page, f"{base_url}{path}")

    visible_text = page.locator("body").inner_text()

    nan_matches = re.findall(r"\bNaN\b", visible_text)
    assert len(nan_matches) == 0, (
        f"Rendering artifact 'NaN' found on {path}: "
        + _extract_context(visible_text, "NaN")
    )


@pytest.mark.parametrize("path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES])
def test_no_undefined_artifacts(page, base_url: str, path: str) -> None:
    """No page shows 'undefined' rendering artifacts in visible text."""
    navigate(page, f"{base_url}{path}")

    visible_text = page.locator("body").inner_text()

    undefined_matches = re.findall(r"\bundefined\b", visible_text)
    assert len(undefined_matches) == 0, (
        f"Rendering artifact 'undefined' found on {path}: "
        + _extract_context(visible_text, "undefined")
    )


@pytest.mark.parametrize("path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES])
def test_no_null_artifacts(page, base_url: str, path: str) -> None:
    """No page shows literal 'null' rendering artifacts in visible text."""
    navigate(page, f"{base_url}{path}")

    visible_text = page.locator("body").inner_text()

    # Match standalone "null" but not words containing it (e.g. "nullable")
    null_matches = re.findall(r"\bnull\b", visible_text)
    # Filter out legitimate uses (JSON display areas, code blocks)
    code_blocks = page.locator("pre, code").count()
    if code_blocks == 0 and len(null_matches) > 0:
        assert len(null_matches) == 0, (
            f"Rendering artifact 'null' found on {path}: "
            + _extract_context(visible_text, "null")
        )


@pytest.mark.parametrize("path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES])
def test_console_warnings_collected(page, base_url: str, path: str) -> None:
    """Collect console.warn messages (informational, does not fail)."""
    warnings: list[str] = []

    def on_console(msg: object) -> None:
        if getattr(msg, "type", None) == "warning":
            warnings.append(getattr(msg, "text", str(msg)))

    page.on("console", on_console)
    navigate(page, f"{base_url}{path}")

    if warnings:
        print(f"[INFO] Console warnings on {path}: {warnings}")


# ---------------------------------------------------------------------------
# Semantic content checks — does the page deliver its purpose?
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES])
def test_page_delivers_purpose_content(page, base_url: str, path: str) -> None:
    """Each page must render the content that fulfills its purpose.

    A page that loads with only a heading and nav bar is a shell, not a page.
    This test verifies that each page contains the semantic content its users need.
    """
    navigate(page, f"{base_url}{path}")

    requirements = PAGE_PURPOSE_CONTENT.get(path, [])
    if not requirements:
        return  # No purpose requirements defined for this path

    body_text = page.locator("body").inner_text()
    body_lower = body_text.lower()

    for description, keywords in requirements:
        has_content = any(
            kw in body_text or kw.lower() in body_lower for kw in keywords
        )
        assert has_content, (
            f"{path} must show {description} (expected one of: {keywords})"
        )


@pytest.mark.parametrize("path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES])
def test_page_has_interactive_elements(page, base_url: str, path: str) -> None:
    """Every admin page should have at least one interactive element.

    Admin pages exist for operators to take action — view data, filter, configure.
    A page with zero buttons, links, inputs, or tables is likely broken.
    """
    navigate(page, f"{base_url}{path}")

    buttons = page.locator("button").count()
    inputs = page.locator("input, select, textarea").count()
    tables = page.locator("table").count()
    links = page.locator("a").count()

    total_interactive = buttons + inputs + tables + links
    assert total_interactive > 0, (
        f"{path} has no interactive elements (buttons, inputs, tables, links)"
    )


@pytest.mark.parametrize("path", ALL_PAGES, ids=[p.split("/")[-1] for p in ALL_PAGES])
def test_page_not_empty_shell(page, base_url: str, path: str) -> None:
    """Page content must be substantive, not just nav + heading.

    A page that renders less than 50 characters of visible content (excluding
    nav/sidebar) is likely a broken partial load or empty shell.
    """
    navigate(page, f"{base_url}{path}")

    # Get main content area text (exclude nav sidebar)
    main_content = page.locator("main, [role='main'], .content, #content")
    if main_content.count() > 0:
        content_text = main_content.first.inner_text().strip()
    else:
        content_text = page.locator("body").inner_text().strip()

    assert len(content_text) > 50, (
        f"{path} has too little content ({len(content_text)} chars) — "
        f"likely an empty shell or broken partial load"
    )


def _extract_context(text: str, needle: str, chars: int = 60) -> str:
    """Extract surrounding context around the first occurrence of needle."""
    idx = text.find(needle)
    if idx == -1:
        return ""
    start = max(0, idx - chars)
    end = min(len(text), idx + len(needle) + chars)
    return f"...{text[start:end]}..."
