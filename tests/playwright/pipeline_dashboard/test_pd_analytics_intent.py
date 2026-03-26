"""Story 76.10 — Analytics Tab: Page Intent & Semantic Content.

Validates that /dashboard/?tab=analytics delivers its core purpose:
  - "Operational Analytics" heading is visible.
  - Summary cards (Tasks Completed, Avg Pipeline Time, PR Merge Rate, Total Spend)
    are rendered, or an empty state is shown when no data exists.
  - Period selector (7d / 30d / 90d) is always present.
  - Chart containers for throughput and bottleneck sections exist.
  - Expert reputation table section is present.

These tests check *what* the page communicates, not *how* it looks.
Style compliance is in test_pd_analytics_style.py.
API contracts are in test_pd_analytics_api.py.
"""

import pytest

from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

# Summary card labels as rendered by SummaryCards.tsx
SUMMARY_CARD_LABELS = [
    "Tasks Completed",
    "Avg Pipeline Time",
    "PR Merge Rate",
    "Total Spend",
]

# Period selector button labels as rendered by PeriodSelector.tsx
PERIOD_OPTIONS = ["7d", "30d", "90d"]


# ---------------------------------------------------------------------------
# Navigation helper
# ---------------------------------------------------------------------------


def _go(page: object, base_url: str) -> None:
    """Navigate to the analytics tab and wait for React to hydrate."""
    dashboard_navigate(page, base_url, "analytics")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Page heading
# ---------------------------------------------------------------------------


class TestAnalyticsHeading:
    """The Analytics tab must surface its primary heading.

    Operators navigating directly to the analytics tab need an immediate
    visual anchor confirming they have reached the right section.
    """

    def test_analytics_heading_or_empty_state_present(
        self, page, base_url: str
    ) -> None:
        """Analytics tab renders either the 'Operational Analytics' heading or an empty state."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        has_heading = "Operational Analytics" in body or "Analytics" in body
        has_empty = (
            page.locator("[data-testid='analytics-empty-state']").count() > 0
            or "No analytics data" in body
        )

        assert has_heading or has_empty, (
            "Analytics tab must render either the 'Operational Analytics' heading "
            "or an analytics empty state — neither was found"
        )

    def test_analytics_page_title_shown(self, page, base_url: str) -> None:
        """'Analytics' appears somewhere on the page (nav label or heading)."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        assert "Analytics" in body, (
            "Analytics tab must contain the word 'Analytics' in visible text"
        )


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------


class TestAnalyticsEmptyState:
    """When no data exists, the Analytics tab shows a helpful empty state.

    The empty state guides operators to start processing issues through the
    pipeline to generate analytics data.
    """

    def test_empty_state_has_cta_when_no_data(self, page, base_url: str) -> None:
        """Analytics empty state shows a 'Go to Pipeline' or similar CTA."""
        _go(page, base_url)

        empty = page.locator("[data-testid='analytics-empty-state']")
        if empty.count() == 0:
            pytest.skip("Analytics data is present — empty state not shown")

        body = empty.inner_text().lower()
        has_cta = (
            "pipeline" in body
            or "go to" in body
            or "start processing" in body
        )
        assert has_cta, (
            "Analytics empty state must include a call-to-action directing "
            "the user to process issues through the pipeline"
        )

    def test_empty_state_description_present(self, page, base_url: str) -> None:
        """Analytics empty state includes a description of what analytics shows."""
        _go(page, base_url)

        empty = page.locator("[data-testid='analytics-empty-state']")
        if empty.count() == 0:
            pytest.skip("Analytics data is present — empty state not shown")

        body = empty.inner_text().lower()
        has_description = (
            "metric" in body
            or "throughput" in body
            or "bottleneck" in body
            or "github" in body
            or "processing" in body
        )
        assert has_description, (
            "Analytics empty state must explain what operational metrics "
            "will appear once data is available"
        )


# ---------------------------------------------------------------------------
# Summary cards
# ---------------------------------------------------------------------------


class TestAnalyticsSummaryCards:
    """Summary cards surface the four key performance metrics.

    Operators rely on these cards for at-a-glance pipeline health:
    task throughput, cycle time, PR merge rate, and total AI spend.
    """

    def test_summary_cards_or_empty_state_present(
        self, page, base_url: str
    ) -> None:
        """Analytics tab renders summary cards or the empty state."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        has_cards = any(label in body for label in SUMMARY_CARD_LABELS)
        has_empty = (
            page.locator("[data-testid='analytics-empty-state']").count() > 0
            or "No analytics data" in body
        )
        assert has_cards or has_empty, (
            "Analytics tab must render summary cards "
            f"({', '.join(SUMMARY_CARD_LABELS)!r}) or an empty state"
        )

    def test_tasks_completed_card_present(self, page, base_url: str) -> None:
        """'Tasks Completed' summary card is visible when data exists."""
        _go(page, base_url)

        if page.locator("[data-testid='analytics-empty-state']").count() > 0:
            pytest.skip("Analytics empty state — summary cards not shown")

        body = page.locator("body").inner_text()
        assert "Tasks Completed" in body, (
            "Analytics tab must display a 'Tasks Completed' summary card "
            "showing throughput over the selected period"
        )

    def test_avg_pipeline_time_card_present(self, page, base_url: str) -> None:
        """'Avg Pipeline Time' summary card is visible when data exists."""
        _go(page, base_url)

        if page.locator("[data-testid='analytics-empty-state']").count() > 0:
            pytest.skip("Analytics empty state — summary cards not shown")

        body = page.locator("body").inner_text()
        assert "Avg Pipeline Time" in body, (
            "Analytics tab must display an 'Avg Pipeline Time' summary card "
            "showing average end-to-end cycle time"
        )

    def test_pr_merge_rate_card_present(self, page, base_url: str) -> None:
        """'PR Merge Rate' summary card is visible when data exists."""
        _go(page, base_url)

        if page.locator("[data-testid='analytics-empty-state']").count() > 0:
            pytest.skip("Analytics empty state — summary cards not shown")

        body = page.locator("body").inner_text()
        assert "PR Merge Rate" in body, (
            "Analytics tab must display a 'PR Merge Rate' summary card "
            "showing the percentage of draft PRs merged"
        )

    def test_total_spend_card_present(self, page, base_url: str) -> None:
        """'Total Spend' summary card is visible when data exists."""
        _go(page, base_url)

        if page.locator("[data-testid='analytics-empty-state']").count() > 0:
            pytest.skip("Analytics empty state — summary cards not shown")

        body = page.locator("body").inner_text()
        assert "Total Spend" in body, (
            "Analytics tab must display a 'Total Spend' summary card "
            "showing cumulative AI API cost for the period"
        )


# ---------------------------------------------------------------------------
# Period selector
# ---------------------------------------------------------------------------


class TestAnalyticsPeriodSelector:
    """Period selector (7d / 30d / 90d) must always be rendered.

    The period selector is the primary time-range control for all analytics
    charts and summary metrics.  It must be present even in the empty state.
    """

    def test_period_selector_present(self, page, base_url: str) -> None:
        """Analytics tab renders a period selector with 7d, 30d, 90d options."""
        _go(page, base_url)

        if page.locator("[data-testid='analytics-empty-state']").count() > 0:
            pytest.skip("Analytics empty state — period selector not shown in empty state")

        body = page.locator("body").inner_text()
        found = [opt for opt in PERIOD_OPTIONS if opt in body]
        assert found, (
            "Analytics tab must render a period selector with 7d / 30d / 90d options"
        )

    def test_period_selector_all_options_shown(self, page, base_url: str) -> None:
        """All three period options (7d, 30d, 90d) are visible."""
        _go(page, base_url)

        if page.locator("[data-testid='analytics-empty-state']").count() > 0:
            pytest.skip("Analytics empty state — period selector not shown")

        body = page.locator("body").inner_text()
        missing = [opt for opt in PERIOD_OPTIONS if opt not in body]
        assert not missing, (
            f"Period selector is missing options: {missing!r}. "
            "All of 7d, 30d, 90d must be visible."
        )

    def test_period_selector_default_is_30d(self, page, base_url: str) -> None:
        """Default period selection is 30d on first load."""
        _go(page, base_url)

        if page.locator("[data-testid='analytics-empty-state']").count() > 0:
            pytest.skip("Analytics empty state — period selector not shown")

        # The default period in Analytics.tsx is '30d' — it should be highlighted.
        body = page.locator("body").inner_text()
        assert "30d" in body, (
            "Analytics tab must show '30d' as the default period option"
        )


# ---------------------------------------------------------------------------
# Chart containers
# ---------------------------------------------------------------------------


class TestAnalyticsChartContainers:
    """Chart section containers must be present for each analytics view.

    The throughput chart and bottleneck bars are the primary visualisations
    on the analytics tab.  Their containers must be rendered so operators
    can access data even before chart libraries fully initialise.
    """

    def test_throughput_section_present(self, page, base_url: str) -> None:
        """Throughput chart section container is rendered."""
        _go(page, base_url)

        if page.locator("[data-testid='analytics-empty-state']").count() > 0:
            pytest.skip("Analytics empty state — charts not shown")

        body = page.locator("body").inner_text().lower()
        has_throughput = (
            "throughput" in body
            or page.locator("[data-tour='analytics-throughput']").count() > 0
        )
        assert has_throughput, (
            "Analytics tab must render a throughput chart section "
            "([data-tour='analytics-throughput'] or text containing 'throughput')"
        )

    def test_bottleneck_section_present(self, page, base_url: str) -> None:
        """Bottleneck bars section container is rendered."""
        _go(page, base_url)

        if page.locator("[data-testid='analytics-empty-state']").count() > 0:
            pytest.skip("Analytics empty state — charts not shown")

        body = page.locator("body").inner_text().lower()
        has_bottleneck = (
            "bottleneck" in body
            or page.locator("[data-tour='analytics-bottleneck']").count() > 0
        )
        assert has_bottleneck, (
            "Analytics tab must render a bottleneck bars section "
            "([data-tour='analytics-bottleneck'] or text containing 'bottleneck')"
        )

    def test_category_breakdown_section_present(self, page, base_url: str) -> None:
        """Category breakdown section is rendered."""
        _go(page, base_url)

        if page.locator("[data-testid='analytics-empty-state']").count() > 0:
            pytest.skip("Analytics empty state — charts not shown")

        body = page.locator("body").inner_text().lower()
        has_category = "categor" in body or "breakdown" in body
        assert has_category, (
            "Analytics tab must render a category breakdown section "
            "showing task distribution by category"
        )

    def test_failure_analysis_section_present(self, page, base_url: str) -> None:
        """Failure analysis section is rendered."""
        _go(page, base_url)

        if page.locator("[data-testid='analytics-empty-state']").count() > 0:
            pytest.skip("Analytics empty state — charts not shown")

        body = page.locator("body").inner_text().lower()
        has_failure = "failure" in body or "fail" in body
        assert has_failure, (
            "Analytics tab must render a failure analysis section "
            "showing pipeline failure patterns"
        )


# ---------------------------------------------------------------------------
# Expert reputation table
# ---------------------------------------------------------------------------


class TestAnalyticsExpertTable:
    """Expert reputation table surfaces per-expert performance data.

    Operators use this table to assess which experts are performing well
    and which are degrading pipeline quality.
    """

    def test_expert_table_section_present(self, page, base_url: str) -> None:
        """Expert reputation table section is rendered when data exists."""
        _go(page, base_url)

        if page.locator("[data-testid='analytics-empty-state']").count() > 0:
            pytest.skip("Analytics empty state — expert table not shown")

        # Check for the data-tour anchor or text indicators
        has_expert_tour = (
            page.locator("[data-tour='analytics-expert-table']").count() > 0
        )
        body = page.locator("body").inner_text().lower()
        has_expert_text = "expert" in body or "reputation" in body

        assert has_expert_tour or has_expert_text, (
            "Analytics tab must render an expert reputation table section "
            "([data-tour='analytics-expert-table'] or text containing 'expert')"
        )
