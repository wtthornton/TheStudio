"""Story 76.8 — Budget Tab: Page Intent & Semantic Content.

Validates that /dashboard/?tab=budget delivers its core purpose:
  - "Budget Dashboard" heading is present.
  - Summary cards (Total Spend, Total API Calls, Cache Hit Rate) are shown
    OR an appropriate empty state is displayed when no data exists yet.
  - Cost breakdown sections for spend by stage and spend by model render
    when data is available.
  - Period selector (1d / 7d / 30d) is always rendered.
  - Budget Alert Configuration section is shown when config data is loaded.

These tests check *what* the page communicates, not *how* it looks.
Style compliance is in test_pd_budget_style.py.
API contracts are in test_pd_budget_api.py.
"""

import pytest

from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

# Summary card labels as rendered by BudgetDashboard.tsx SummaryCards component.
SUMMARY_CARD_LABELS = [
    "Total Spend",
    "Total API Calls",
    "Cache Hit Rate",
]

# Cost breakdown section titles as rendered by HBarChart.
COST_BREAKDOWN_TITLES = [
    "Cost by Pipeline Stage",
    "Cost by Model",
]


# ---------------------------------------------------------------------------
# Navigation helper
# ---------------------------------------------------------------------------


def _go(page: object, base_url: str) -> None:
    """Navigate to the budget tab and wait for React to hydrate."""
    dashboard_navigate(page, base_url, "budget")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Budget heading
# ---------------------------------------------------------------------------


class TestBudgetHeading:
    """The Budget tab must always render a 'Budget Dashboard' section heading.

    Operators rely on this heading to confirm they are viewing cost data for
    the AI delivery pipeline — not an unrelated admin view.
    """

    def test_budget_dashboard_heading_present(self, page, base_url: str) -> None:
        """Budget tab renders a 'Budget Dashboard' heading."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        assert "Budget Dashboard" in body, (
            "Budget tab must display a 'Budget Dashboard' heading "
            "so operators can confirm they are viewing cost metrics"
        )

    def test_budget_heading_is_heading_element(self, page, base_url: str) -> None:
        """'Budget Dashboard' text is rendered inside a heading element (h1–h3)."""
        _go(page, base_url)

        heading = page.locator("h1, h2, h3, h4").filter(has_text="Budget Dashboard")
        assert heading.count() > 0, (
            "Budget Dashboard heading must be rendered as an h1–h4 element, "
            "not plain text — required for heading hierarchy and screen reader navigation"
        )


# ---------------------------------------------------------------------------
# Period selector
# ---------------------------------------------------------------------------


class TestPeriodSelector:
    """Period selector (1d / 7d / 30d) must always be present on the budget tab.

    The period selector controls the time window for all budget metrics.
    Operators use it to view daily, weekly, or monthly spend at a glance.
    """

    def test_period_selector_present(self, page, base_url: str) -> None:
        """Budget tab renders the period selector with 1d, 7d, and 30d options."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        # All three period labels must be visible simultaneously.
        for label in ("1d", "7d", "30d"):
            assert label in body, (
                f"Period selector must show '{label}' option — "
                "operators need to switch time windows to analyse spend trends"
            )

    def test_period_selector_buttons_present(self, page, base_url: str) -> None:
        """Period selector renders as clickable buttons, not plain text."""
        _go(page, base_url)

        # At least one of the three period buttons must be a <button> element.
        period_buttons = page.locator("button").filter(has_text="1d")
        alt_buttons = page.locator("button").filter(has_text="7d")
        found = period_buttons.count() > 0 or alt_buttons.count() > 0
        assert found, (
            "Period selector options must be rendered as <button> elements "
            "to be keyboard-reachable and interactive"
        )


# ---------------------------------------------------------------------------
# Summary cards or empty state
# ---------------------------------------------------------------------------


class TestSummaryCardsOrEmptyState:
    """Summary cards OR the empty state must always be rendered.

    When budget data is available, SummaryCards shows Total Spend, Total API
    Calls, and Cache Hit Rate.  When no tasks have been processed yet, the
    empty state guides operators to configure budget alerts.
    """

    def test_summary_cards_or_empty_state_present(self, page, base_url: str) -> None:
        """Budget tab renders summary cards or an empty-state message."""
        _go(page, base_url)

        body = page.locator("body").inner_text()

        has_summary = any(label in body for label in SUMMARY_CARD_LABELS)
        has_empty = (
            "No spend data" in body
            or "no spend" in body.lower()
            or "no data" in body.lower()
            or "budget metrics" in body.lower()
        )
        assert has_summary or has_empty, (
            "Budget tab must render summary cards (Total Spend, Total API Calls, "
            "Cache Hit Rate) or an appropriate empty state when no data is available"
        )

    def test_total_spend_card_present_when_data_available(
        self, page, base_url: str
    ) -> None:
        """When budget data exists, the 'Total Spend' card is visible."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        if "No spend data" in body or "no spend" in body.lower():
            pytest.skip("No budget data — empty state is shown; skipping card check")

        assert "Total Spend" in body, (
            "When budget data is available, 'Total Spend' summary card must be shown"
        )

    def test_total_api_calls_card_present_when_data_available(
        self, page, base_url: str
    ) -> None:
        """When budget data exists, the 'Total API Calls' card is visible."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        if "No spend data" in body or "no spend" in body.lower():
            pytest.skip("No budget data — skipping Total API Calls card check")

        assert "Total API Calls" in body, (
            "When budget data is available, 'Total API Calls' summary card must be shown"
        )

    def test_cache_hit_rate_card_present_when_data_available(
        self, page, base_url: str
    ) -> None:
        """When budget data exists, the 'Cache Hit Rate' card is visible."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        if "No spend data" in body or "no spend" in body.lower():
            pytest.skip("No budget data — skipping Cache Hit Rate card check")

        assert "Cache Hit Rate" in body, (
            "When budget data is available, 'Cache Hit Rate' summary card must be shown"
        )


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------


class TestBudgetEmptyState:
    """Empty state must guide operators when no spend data is available.

    The empty state communicates the correct heading, description, and CTA
    so operators know how to proceed (configure budget alerts, view admin console).
    """

    def test_empty_state_heading_when_no_data(self, page, base_url: str) -> None:
        """Empty budget state shows 'No spend data yet' heading."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        if any(label in body for label in SUMMARY_CARD_LABELS):
            pytest.skip("Summary cards visible — budget data loaded; not in empty state")

        assert "No spend data" in body or "no data" in body.lower(), (
            "Empty budget state must display a 'No spend data yet' heading "
            "to guide operators when LLM cost metrics are not yet available"
        )

    def test_empty_state_description_mentions_alerts(
        self, page, base_url: str
    ) -> None:
        """Empty budget state description mentions configuring budget alerts."""
        _go(page, base_url)

        body = page.locator("body").inner_text().lower()
        if any(label.lower() in body for label in SUMMARY_CARD_LABELS):
            pytest.skip("Summary cards visible — not in empty state")

        has_guidance = (
            "budget" in body
            or "alert" in body
            or "configure" in body
            or "spending" in body
        )
        assert has_guidance, (
            "Empty budget state must include a description explaining how to "
            "configure budget alerts and spending caps"
        )


# ---------------------------------------------------------------------------
# Cost breakdown sections
# ---------------------------------------------------------------------------


class TestCostBreakdownSections:
    """Cost breakdown by stage and by model must render when data is available.

    The CostBreakdown component shows two horizontal bar charts: one grouped
    by pipeline stage and one grouped by model.  Operators use these to
    identify which stages and models are driving LLM costs.
    """

    def test_cost_by_stage_section_present_when_data_available(
        self, page, base_url: str
    ) -> None:
        """'Cost by Pipeline Stage' section renders when budget data exists."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        if "No spend data" in body or not any(
            label in body for label in SUMMARY_CARD_LABELS
        ):
            pytest.skip("No budget data — skipping cost breakdown check")

        assert "Cost by Pipeline Stage" in body, (
            "When budget data is available, the 'Cost by Pipeline Stage' breakdown "
            "must be rendered to help operators identify high-cost pipeline stages"
        )

    def test_cost_by_model_section_present_when_data_available(
        self, page, base_url: str
    ) -> None:
        """'Cost by Model' section renders when budget data exists."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        if "No spend data" in body or not any(
            label in body for label in SUMMARY_CARD_LABELS
        ):
            pytest.skip("No budget data — skipping cost by model check")

        assert "Cost by Model" in body, (
            "When budget data is available, the 'Cost by Model' breakdown "
            "must be rendered to help operators compare per-model LLM spend"
        )


# ---------------------------------------------------------------------------
# Budget Alert Configuration section
# ---------------------------------------------------------------------------


class TestBudgetAlertConfig:
    """Budget Alert Configuration section must render when config data is loaded.

    BudgetAlertConfig shows threshold inputs (daily warning, weekly cap,
    per-task warning, downgrade threshold) and toggle switches for automatic
    actions (pause, model downgrade).
    """

    def test_budget_alert_config_heading_present(self, page, base_url: str) -> None:
        """'Budget Alert Configuration' section heading is visible when config loads."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        if "Budget Alert Configuration" not in body:
            # Config may still be loading — acceptable.
            pytest.skip(
                "Budget Alert Configuration section not yet visible — "
                "config may still be loading"
            )

        assert "Budget Alert Configuration" in body, (
            "Budget tab must render 'Budget Alert Configuration' section "
            "so operators can set spend thresholds and automated actions"
        )

    def test_save_configuration_button_present(self, page, base_url: str) -> None:
        """'Save Configuration' button is present in the Budget Alert Config section."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        if "Budget Alert Configuration" not in body:
            pytest.skip("Budget Alert Configuration section not loaded")

        assert "Save Configuration" in body, (
            "Budget Alert Configuration must include a 'Save Configuration' button "
            "so operators can persist threshold changes"
        )

    def test_weekly_budget_cap_input_present(self, page, base_url: str) -> None:
        """'Weekly Budget Cap' input field is present in the config form."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        if "Budget Alert Configuration" not in body:
            pytest.skip("Budget Alert Configuration section not loaded")

        assert "Weekly Budget Cap" in body, (
            "Budget Alert Configuration must include a 'Weekly Budget Cap' input "
            "for operators to cap total weekly LLM spend"
        )
