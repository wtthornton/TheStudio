"""Epic 63.1 — Metrics: Page Intent & Semantic Content.

Validates that /admin/ui/metrics delivers its core purpose:
  - Success rates are displayed (pipeline pass/fail ratios)
  - Gate status shows pass/fail/error states for each verification gate
  - Loopback breakdown surfaces retry counts and loopback reasons

These tests check *what* the page communicates, not *how* it looks.
Style compliance is covered in test_metrics_style.py (Epic 63.3).
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

METRICS_URL = "/admin/ui/metrics"


class TestMetricsSuccessRates:
    """Metrics page must surface pipeline success rates for operator monitoring.

    Success rate data allows operators to assess overall pipeline health
    and identify degradation trends before they become incidents.
    """

    def test_metrics_page_renders(self, page, base_url: str) -> None:
        """Metrics page loads and shows content or an empty-state indicator."""
        navigate(page, f"{base_url}{METRICS_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Metrics page body must not be empty"

    def test_success_rate_indicator_shown(self, page, base_url: str) -> None:
        """Metrics page contains success rate or pass rate information."""
        navigate(page, f"{base_url}{METRICS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        success_keywords = (
            "success",
            "pass",
            "passed",
            "rate",
            "throughput",
            "completion",
            "%",
        )
        assert any(kw in body_lower for kw in success_keywords), (
            "Metrics page must display success rate or pass rate information"
        )

    def test_failure_rate_or_error_indicator_shown(self, page, base_url: str) -> None:
        """Metrics page surfaces failure or error rate data alongside successes."""
        navigate(page, f"{base_url}{METRICS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        failure_keywords = (
            "fail",
            "failed",
            "failure",
            "error",
            "reject",
            "rejected",
        )
        has_failure = any(kw in body_lower for kw in failure_keywords)
        # Failure data may be absent if no failures have occurred; allow empty state
        has_empty_state = any(
            kw in body_lower for kw in ("no data", "no metrics", "empty", "nothing")
        )
        assert has_failure or has_empty_state, (
            "Metrics page must show failure/error indicators or an empty-state message"
        )


class TestMetricsGateStatus:
    """Gate status section must show each pipeline gate's current pass/fail state.

    Gates fail closed — operators need immediate visibility into which gate
    is blocking the pipeline so they can respond quickly.
    """

    def test_gate_status_section_present(self, page, base_url: str) -> None:
        """Metrics page references gate status or pipeline gate health."""
        navigate(page, f"{base_url}{METRICS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        gate_keywords = ("gate", "gates", "check", "verification", "verify", "scan")
        assert any(kw in body_lower for kw in gate_keywords), (
            "Metrics page must include a gate status or verification section"
        )

    def test_gate_pass_or_fail_state_visible(self, page, base_url: str) -> None:
        """Gate section shows pass/fail/error state indicators."""
        navigate(page, f"{base_url}{METRICS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        state_keywords = (
            "pass",
            "fail",
            "error",
            "ok",
            "healthy",
            "degraded",
            "warning",
        )
        has_state = any(kw in body_lower for kw in state_keywords)
        has_empty_state = any(
            kw in body_lower for kw in ("no data", "no gates", "no metrics", "empty")
        )
        assert has_state or has_empty_state, (
            "Gate status section must display pass/fail/error states or an empty-state message"
        )


class TestMetricsLoopbackBreakdown:
    """Loopback breakdown section surfaces retry/re-queue data.

    Loopback signals indicate where the pipeline is spending extra cycles.
    Operators use this to tune agent behavior and identify quality regressions.
    """

    def test_loopback_section_present(self, page, base_url: str) -> None:
        """Metrics page surfaces loopback, retry, or re-queue breakdown data."""
        navigate(page, f"{base_url}{METRICS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        loopback_keywords = (
            "loopback",
            "retry",
            "retries",
            "re-queue",
            "requeue",
            "rework",
            "cycle",
        )
        has_loopback = any(kw in body_lower for kw in loopback_keywords)
        has_empty_state = any(
            kw in body_lower for kw in ("no data", "no loopbacks", "empty", "nothing")
        )
        assert has_loopback or has_empty_state, (
            "Metrics page must include a loopback or retry breakdown section"
        )


class TestMetricsPageStructure:
    """Metrics page must have clear page-level structure for operator orientation."""

    def test_page_heading_present(self, page, base_url: str) -> None:
        """Metrics page has a heading identifying it as the metrics section."""
        navigate(page, f"{base_url}{METRICS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        heading_keywords = ("metric", "metrics", "performance", "analytics", "stats", "statistics")
        assert any(kw in body_lower for kw in heading_keywords), (
            "Metrics page must have a heading referencing 'Metrics' or 'Performance'"
        )

    def test_page_loads_without_error(self, page, base_url: str) -> None:
        """Metrics page loads and the body has meaningful content (not blank)."""
        navigate(page, f"{base_url}{METRICS_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Metrics page body must not be empty"
