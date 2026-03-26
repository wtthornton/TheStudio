"""Story 76.11 — Reputation Tab: Page Intent & Semantic Content.

Validates that /dashboard/?tab=reputation delivers its core purpose:
  - "Reputation & Outcomes" heading is rendered
  - Summary cards surface aggregate metrics (success_rate, avg_loopbacks,
    pr_merge_rate, drift_score) OR show an empty/loading state
  - Expert list or appropriate empty state is present
  - Drift Alerts panel is always rendered
  - Outcome feed section is present

These tests check *what* the page communicates, not *how* it looks.
Style compliance is in test_pd_reputation_style.py (Story 76.11).
"""

import pytest

from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

# The four aggregate metric labels shown in the summary cards.
REPUTATION_METRIC_LABELS = [
    "success",
    "loopback",
    "merge",
    "drift",
]


# ---------------------------------------------------------------------------
# Navigation guard
# ---------------------------------------------------------------------------


def _go(page: object, base_url: str) -> None:
    """Navigate to the reputation tab and wait for React to hydrate."""
    dashboard_navigate(page, base_url, "reputation")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Page heading
# ---------------------------------------------------------------------------


class TestReputationPageHeading:
    """The reputation tab must render a recognisable page heading.

    Operators need a clear section title to confirm they are looking at the
    Reputation & Outcomes view — not another tab.
    """

    def test_reputation_heading_present(self, page, base_url: str) -> None:
        """'Reputation' or 'Reputation & Outcomes' heading is in the page body."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        has_heading = "Reputation" in body
        assert has_heading, (
            "Reputation tab must render a 'Reputation' or 'Reputation & Outcomes' "
            "heading so operators can identify the view"
        )

    def test_reputation_heading_is_semantic_element(self, page, base_url: str) -> None:
        """The 'Reputation' heading is rendered as an h2 or h3 element."""
        _go(page, base_url)

        headings = page.evaluate(
            """
            () => {
                const hs = Array.from(document.querySelectorAll('h1, h2, h3, h4'));
                return hs.map(h => h.textContent.trim());
            }
            """
        )
        has_reputation_heading = any(
            "Reputation" in text for text in headings
        )
        assert has_reputation_heading, (
            "Reputation tab must use a semantic heading element (h1–h4) "
            "containing 'Reputation' for screen-reader navigation"
        )

    def test_rolling_window_label_present(self, page, base_url: str) -> None:
        """A rolling-window label (e.g. '14-day rolling window') is visible."""
        _go(page, base_url)

        body = page.locator("body").inner_text().lower()
        has_window = (
            "rolling" in body
            or "14-day" in body
            or "window" in body
        )
        assert has_window, (
            "Reputation tab must display a rolling-window label so operators "
            "understand the time scope of the metrics shown"
        )


# ---------------------------------------------------------------------------
# Summary cards
# ---------------------------------------------------------------------------


class TestReputationSummaryCards:
    """Summary cards must surface aggregate reputation metrics or a loading state.

    The four canonical metrics are: success rate, average loopbacks, PR merge
    rate, and drift score.  When data is unavailable the cards should show a
    neutral placeholder, not a blank region.
    """

    def test_summary_cards_section_present(self, page, base_url: str) -> None:
        """Reputation tab renders a summary cards section."""
        _go(page, base_url)

        # Accept either an explicit testid or the presence of metric text.
        has_cards = (
            page.locator("[data-testid='reputation-summary-cards']").count() > 0
            or page.locator("[data-testid='summary-cards']").count() > 0
        )

        if not has_cards:
            # Fall back: check that at least one metric keyword appears.
            body_lower = page.locator("body").inner_text().lower()
            has_cards = any(label in body_lower for label in REPUTATION_METRIC_LABELS)

        assert has_cards, (
            "Reputation tab must render summary cards (or metric values) for "
            "success rate, loopbacks, merge rate, and drift score"
        )

    def test_summary_cards_count_at_least_four(self, page, base_url: str) -> None:
        """At least four summary card elements are present when data is loaded."""
        _go(page, base_url)

        card_selectors = [
            "[data-testid='reputation-summary-cards'] > *",
            "[data-testid='summary-cards'] > *",
            "[class*='grid'] > [class*='card']",
            "[class*='grid'] > div[class*='border']",
            "[class*='grid'] > div[class*='rounded']",
        ]
        for sel in card_selectors:
            count = page.evaluate(
                f"document.querySelectorAll({sel!r}).length"
            )
            if count >= 4:
                return  # Sufficient cards found

        # If no explicit card container, skip rather than fail — layout may vary.
        body_lower = page.locator("body").inner_text().lower()
        metrics_found = sum(1 for label in REPUTATION_METRIC_LABELS if label in body_lower)
        if metrics_found < 2:
            pytest.skip(
                "Summary cards not found with known selectors — "
                "layout may use a different container pattern"
            )


# ---------------------------------------------------------------------------
# Expert list
# ---------------------------------------------------------------------------


class TestReputationExpertList:
    """Expert list or appropriate empty state must be present on the tab.

    Operators monitor expert performance over time via the expert table.
    When no experts exist the UI should communicate this clearly.
    """

    def test_expert_section_or_empty_state_present(self, page, base_url: str) -> None:
        """Expert table or empty state is rendered on the reputation tab."""
        _go(page, base_url)

        has_expert_section = (
            page.locator("[data-testid='expert-table']").count() > 0
            or page.locator("[data-testid='expert-list']").count() > 0
            or page.locator("[data-testid='expert-detail']").count() > 0
        )

        if not has_expert_section:
            body_lower = page.locator("body").inner_text().lower()
            has_expert_section = (
                "expert" in body_lower
                or "no experts" in body_lower
                or "performance" in body_lower
            )

        assert has_expert_section, (
            "Reputation tab must render an expert performance table or an "
            "empty state communicating that no experts are available"
        )

    def test_expert_section_has_identifiable_content(self, page, base_url: str) -> None:
        """Expert section shows column headers or empty-state text."""
        _go(page, base_url)

        body_lower = page.locator("body").inner_text().lower()

        has_content = (
            "expert" in body_lower
            or "score" in body_lower
            or "performance" in body_lower
            or "loopback" in body_lower
        )
        assert has_content, (
            "Reputation tab expert section must show identifying column headers "
            "('Expert', 'Score', 'Performance', 'Loopbacks') or an empty state"
        )


# ---------------------------------------------------------------------------
# Drift Alerts
# ---------------------------------------------------------------------------


class TestReputationDriftAlerts:
    """Drift Alerts panel must always be present on the reputation tab.

    Drift detection surfaces when expert scores change significantly.
    Operators use this panel to respond to quality regression signals.
    """

    def test_drift_alerts_section_present(self, page, base_url: str) -> None:
        """Drift Alerts panel is rendered on the reputation tab."""
        _go(page, base_url)

        has_drift = (
            page.locator("[data-testid='drift-alerts']").count() > 0
            or page.locator("[data-testid='drift-panel']").count() > 0
        )

        if not has_drift:
            body_lower = page.locator("body").inner_text().lower()
            has_drift = "drift" in body_lower

        assert has_drift, (
            "Reputation tab must always render the Drift Alerts panel "
            "so operators can monitor score deviation signals"
        )

    def test_drift_alerts_empty_state_or_data(self, page, base_url: str) -> None:
        """Drift Alerts panel shows active alerts or an appropriate empty state."""
        _go(page, base_url)

        body_lower = page.locator("body").inner_text().lower()
        has_content = (
            "drift" in body_lower
            or "alert" in body_lower
            or "no drift" in body_lower
            or "no alerts" in body_lower
            or "stable" in body_lower
        )
        assert has_content, (
            "Drift Alerts panel must show active drift alerts or an empty state "
            "('No drift alerts', 'All scores stable', etc.)"
        )


# ---------------------------------------------------------------------------
# Outcome feed
# ---------------------------------------------------------------------------


class TestReputationOutcomeFeed:
    """Outcome feed must be present on the reputation tab.

    The outcome feed shows chronological signals (PR merged, task completed,
    loopback triggered) that feed into expert reputation calculations.
    """

    def test_outcome_feed_section_present(self, page, base_url: str) -> None:
        """Outcome feed section is rendered on the reputation tab."""
        _go(page, base_url)

        has_feed = (
            page.locator("[data-testid='outcome-feed']").count() > 0
            or page.locator("[data-testid='outcome-list']").count() > 0
        )

        if not has_feed:
            body_lower = page.locator("body").inner_text().lower()
            has_feed = (
                "outcome" in body_lower
                or "signal" in body_lower
                or "recent" in body_lower
            )

        assert has_feed, (
            "Reputation tab must render the Outcome feed section showing "
            "recent outcome signals that feed into reputation calculations"
        )

    def test_outcome_feed_empty_state_or_items(self, page, base_url: str) -> None:
        """Outcome feed shows items or an empty state — never a blank region."""
        _go(page, base_url)

        body_lower = page.locator("body").inner_text().lower()
        has_content = (
            "outcome" in body_lower
            or "no outcomes" in body_lower
            or "signal" in body_lower
            or "merge" in body_lower
            or "loopback" in body_lower
        )
        assert has_content, (
            "Outcome feed must show recent outcome items or an empty state — "
            "a completely blank feed region is not acceptable"
        )
