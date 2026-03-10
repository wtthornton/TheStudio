"""Story 12.6: Console error & entity scan across all pages.

Automated scan that visits every page and reports:
- console.error messages
- Literal HTML entities that weren't decoded
- Common rendering artifacts (NaN in visible text)
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
def test_console_warnings_collected(page, base_url: str, path: str) -> None:
    """Collect console.warn messages (informational, does not fail)."""
    warnings: list[str] = []

    def on_console(msg: object) -> None:
        if getattr(msg, "type", None) == "warning":
            warnings.append(getattr(msg, "text", str(msg)))

    page.on("console", on_console)
    navigate(page, f"{base_url}{path}")

    # Log warnings but don't fail — this is informational
    if warnings:
        print(f"[INFO] Console warnings on {path}: {warnings}")


def _extract_context(text: str, needle: str, chars: int = 60) -> str:
    """Extract surrounding context around the first occurrence of needle."""
    idx = text.find(needle)
    if idx == -1:
        return ""
    start = max(0, idx - chars)
    end = min(len(text), idx + len(needle) + chars)
    return f"...{text[start:end]}..."
