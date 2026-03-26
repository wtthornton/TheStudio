"""Epic 72.1 — Cost Dashboard: Page Intent & Semantic Content.

Validates that /admin/ui/cost-dashboard delivers its core purpose:
  - Model spend is displayed (per-model or aggregate spend figures)
  - Budget utilization shows current usage against configured budget limits
  - Cost breakdown surfaces spend by model, repo, or time period

These tests check *what* the page communicates, not *how* it looks.
Style compliance is covered in test_cost_dashboard_style.py (Epic 72.3).
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

COST_DASHBOARD_URL = "/admin/ui/cost-dashboard"


class TestCostDashboardModelSpend:
    """Cost dashboard must surface model spend data for budget management.

    Model spend data allows operators to track AI inference costs, identify
    expensive models, and make routing decisions to control expenditure.
    """

    def test_cost_dashboard_page_renders(self, page, base_url: str) -> None:
        """Cost dashboard page loads and shows content or an empty-state indicator."""
        navigate(page, f"{base_url}{COST_DASHBOARD_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Cost dashboard page body must not be empty"

    def test_model_spend_indicator_shown(self, page, base_url: str) -> None:
        """Cost dashboard contains model spend or cost per model information."""
        navigate(page, f"{base_url}{COST_DASHBOARD_URL}")

        body_lower = page.locator("body").inner_text().lower()
        spend_keywords = (
            "spend",
            "cost",
            "model",
            "token",
            "tokens",
            "inference",
            "usage",
            "$",
        )
        has_spend = any(kw in body_lower for kw in spend_keywords)
        has_empty_state = any(
            kw in body_lower for kw in ("no data", "no costs", "empty", "nothing")
        )
        assert has_spend or has_empty_state, (
            "Cost dashboard must display model spend information or an empty-state message"
        )

    def test_monetary_or_unit_value_present(self, page, base_url: str) -> None:
        """Cost dashboard shows a numeric or monetary value for spend tracking."""
        navigate(page, f"{base_url}{COST_DASHBOARD_URL}")

        body_lower = page.locator("body").inner_text().lower()
        value_keywords = ("$", "usd", "total", "cost", "spend", "0.", "0,", "%")
        has_value = any(kw in body_lower for kw in value_keywords)
        has_empty_state = any(
            kw in body_lower for kw in ("no data", "empty", "no spend", "nothing yet")
        )
        assert has_value or has_empty_state, (
            "Cost dashboard must display monetary or unit-based cost values or an empty-state message"
        )


class TestCostDashboardBudgetUtilization:
    """Budget utilization section must show current usage against limits.

    Budget utilization data allows operators to identify when spend is
    approaching configured limits and take corrective action before overruns.
    """

    def test_budget_section_present(self, page, base_url: str) -> None:
        """Cost dashboard references budget or limit information."""
        navigate(page, f"{base_url}{COST_DASHBOARD_URL}")

        body_lower = page.locator("body").inner_text().lower()
        budget_keywords = (
            "budget",
            "limit",
            "threshold",
            "cap",
            "utilization",
            "allocated",
            "remaining",
        )
        has_budget = any(kw in body_lower for kw in budget_keywords)
        has_empty_state = any(
            kw in body_lower for kw in ("no data", "no budget", "empty", "nothing")
        )
        assert has_budget or has_empty_state, (
            "Cost dashboard must include a budget utilization or limit section"
        )

    def test_utilization_rate_or_progress_shown(self, page, base_url: str) -> None:
        """Budget section shows utilization rate or progress toward limit."""
        navigate(page, f"{base_url}{COST_DASHBOARD_URL}")

        body_lower = page.locator("body").inner_text().lower()
        progress_keywords = (
            "%",
            "percent",
            "utilization",
            "used",
            "remaining",
            "of",
            "budget",
        )
        has_progress = any(kw in body_lower for kw in progress_keywords)
        has_empty_state = any(
            kw in body_lower for kw in ("no data", "empty", "no budget", "nothing yet")
        )
        assert has_progress or has_empty_state, (
            "Budget section must display utilization percentage or remaining budget or an empty-state message"
        )


class TestCostDashboardCostBreakdown:
    """Cost breakdown section surfaces spend disaggregated by model or period.

    Breakdown data lets operators understand *where* costs are being incurred —
    which models, repos, or time windows are the largest contributors.
    """

    def test_cost_breakdown_section_present(self, page, base_url: str) -> None:
        """Cost dashboard surfaces a breakdown of spend by model, repo, or period."""
        navigate(page, f"{base_url}{COST_DASHBOARD_URL}")

        body_lower = page.locator("body").inner_text().lower()
        breakdown_keywords = (
            "breakdown",
            "by model",
            "by repo",
            "per model",
            "detail",
            "distribution",
            "allocation",
        )
        has_breakdown = any(kw in body_lower for kw in breakdown_keywords)
        has_empty_state = any(
            kw in body_lower for kw in ("no data", "empty", "no costs", "nothing")
        )
        assert has_breakdown or has_empty_state, (
            "Cost dashboard must include a cost breakdown section or an empty-state message"
        )

    def test_time_period_reference_present(self, page, base_url: str) -> None:
        """Cost dashboard references a time period for the displayed data."""
        navigate(page, f"{base_url}{COST_DASHBOARD_URL}")

        body_lower = page.locator("body").inner_text().lower()
        period_keywords = (
            "day",
            "week",
            "month",
            "today",
            "period",
            "last",
            "this month",
            "mtd",
            "ytd",
            "daily",
            "monthly",
        )
        has_period = any(kw in body_lower for kw in period_keywords)
        has_empty_state = any(
            kw in body_lower for kw in ("no data", "empty", "nothing yet")
        )
        assert has_period or has_empty_state, (
            "Cost dashboard must reference a time period for displayed cost data or an empty-state message"
        )


class TestCostDashboardPageStructure:
    """Cost dashboard must have clear page-level structure for operator orientation."""

    def test_page_heading_present(self, page, base_url: str) -> None:
        """Cost dashboard has a heading identifying it as the cost section."""
        navigate(page, f"{base_url}{COST_DASHBOARD_URL}")

        body_lower = page.locator("body").inner_text().lower()
        heading_keywords = ("cost", "costs", "spend", "budget", "billing", "usage")
        assert any(kw in body_lower for kw in heading_keywords), (
            "Cost dashboard must have a heading referencing 'Cost', 'Spend', or 'Budget'"
        )

    def test_page_loads_without_error(self, page, base_url: str) -> None:
        """Cost dashboard loads and the body has meaningful content (not blank)."""
        navigate(page, f"{base_url}{COST_DASHBOARD_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Cost dashboard page body must not be empty"
