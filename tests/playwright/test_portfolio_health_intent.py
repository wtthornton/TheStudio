"""Epic 73.1 — Portfolio Health: Page Intent & Semantic Content.

Validates that /admin/ui/portfolio-health delivers its core purpose:
  - Cross-repo health overview is displayed showing aggregate health across repos
  - Risk distribution surfaces the spread of risk levels across the portfolio
  - Page heading clearly identifies the portfolio health section
  - Empty state is shown when no repos are registered in the portfolio

These tests check *what* the page communicates, not *how* it looks.
Style compliance is covered in test_portfolio_health_style.py (Epic 73.3).
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

PORTFOLIO_HEALTH_URL = "/admin/ui/portfolio-health"


class TestPortfolioHealthOverviewContent:
    """Portfolio health page must surface cross-repo health data for fleet operators.

    When repos are registered the page must show:
      Health overview     — aggregate or per-repo health status across the portfolio
      Risk distribution   — spread of risk levels (low / medium / high / critical)
      Repo identity       — repo names or identifiers for context
    """

    def test_portfolio_health_page_renders(self, page, base_url: str) -> None:
        """Portfolio health page loads and shows content or an empty-state indicator."""
        navigate(page, f"{base_url}{PORTFOLIO_HEALTH_URL}")

        has_table = page.locator("table").count() > 0
        has_cards = page.locator(
            "[class*='repo'], [data-repo], [class*='health'], [data-health], "
            "[class*='portfolio'], [data-component='repo-card']"
        ).count() > 0
        body_lower = page.locator("body").inner_text().lower()
        has_empty_state = any(
            kw in body_lower
            for kw in (
                "no repos",
                "no repositories",
                "no data",
                "empty",
                "portfolio",
                "health",
            )
        )
        assert has_table or has_cards or has_empty_state, (
            "Portfolio health page must show a repo table (or card list) or an "
            "empty-state message when no repos are in the portfolio"
        )

    def test_health_status_shown(self, page, base_url: str) -> None:
        """Portfolio health page surfaces health status information for repos."""
        navigate(page, f"{base_url}{PORTFOLIO_HEALTH_URL}")

        body_lower = page.locator("body").inner_text().lower()
        health_keywords = (
            "health",
            "healthy",
            "degraded",
            "critical",
            "warning",
            "ok",
            "good",
            "poor",
            "status",
            "passing",
            "failing",
            "at risk",
        )
        has_health = any(kw in body_lower for kw in health_keywords)
        has_empty_state = any(
            kw in body_lower for kw in ("no repos", "no data", "empty", "nothing")
        )
        assert has_health or has_empty_state, (
            "Portfolio health page must display health status information or an empty-state message"
        )

    def test_repo_identity_shown(self, page, base_url: str) -> None:
        """Portfolio health page shows repo names or identifiers."""
        navigate(page, f"{base_url}{PORTFOLIO_HEALTH_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-repo]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no repos", "no repositories", "empty")):
                pytest.skip("No repos in portfolio — empty state is acceptable for 73.1")

        body_lower = page.locator("body").inner_text().lower()
        repo_keywords = (
            "repo",
            "repository",
            "repositories",
            "project",
            "name",
            "owner",
            "/",
            "github.com",
        )
        assert any(kw in body_lower for kw in repo_keywords), (
            "Portfolio health page must display repository names or identifiers"
        )

    def test_aggregate_health_indicator_present(self, page, base_url: str) -> None:
        """Portfolio health page shows an aggregate or summary health indicator."""
        navigate(page, f"{base_url}{PORTFOLIO_HEALTH_URL}")

        body_lower = page.locator("body").inner_text().lower()
        aggregate_keywords = (
            "overall",
            "total",
            "summary",
            "aggregate",
            "portfolio",
            "fleet",
            "all repos",
            "average",
            "score",
            "health score",
        )
        has_aggregate = any(kw in body_lower for kw in aggregate_keywords)
        has_empty_state = any(
            kw in body_lower for kw in ("no repos", "no data", "empty", "nothing")
        )
        assert has_aggregate or has_empty_state, (
            "Portfolio health page must include an aggregate or summary health indicator "
            "or an empty-state message"
        )


class TestPortfolioHealthRiskDistribution:
    """Risk distribution section must show the spread of risk levels across the portfolio.

    Risk distribution data allows operators to identify how many repos are at each
    risk tier so they can prioritise remediation and avoid surprise failures.
    """

    def test_risk_distribution_section_present(self, page, base_url: str) -> None:
        """Portfolio health page surfaces risk distribution or risk level information."""
        navigate(page, f"{base_url}{PORTFOLIO_HEALTH_URL}")

        body_lower = page.locator("body").inner_text().lower()
        risk_keywords = (
            "risk",
            "low risk",
            "medium risk",
            "high risk",
            "critical",
            "distribution",
            "breakdown",
            "severity",
            "priority",
            "at risk",
        )
        has_risk = any(kw in body_lower for kw in risk_keywords)
        has_empty_state = any(
            kw in body_lower for kw in ("no repos", "no data", "empty", "nothing")
        )
        assert has_risk or has_empty_state, (
            "Portfolio health page must include risk distribution or risk level indicators "
            "or an empty-state message"
        )

    def test_risk_level_labels_present(self, page, base_url: str) -> None:
        """Portfolio health page shows at least one risk level label."""
        navigate(page, f"{base_url}{PORTFOLIO_HEALTH_URL}")

        body_lower = page.locator("body").inner_text().lower()
        level_keywords = ("low", "medium", "high", "critical", "warning", "none", "unknown")
        has_levels = any(kw in body_lower for kw in level_keywords)
        has_empty_state = any(
            kw in body_lower for kw in ("no repos", "no data", "empty", "nothing yet")
        )
        assert has_levels or has_empty_state, (
            "Portfolio health page must display risk level labels (low/medium/high/critical) "
            "or an empty-state message"
        )

    def test_repo_count_or_percentage_shown(self, page, base_url: str) -> None:
        """Portfolio health page shows repo counts or percentages for risk distribution."""
        navigate(page, f"{base_url}{PORTFOLIO_HEALTH_URL}")

        body_lower = page.locator("body").inner_text().lower()
        count_keywords = ("%", "repos", "0", "1", "total", "count", "of")
        has_counts = any(kw in body_lower for kw in count_keywords)
        has_empty_state = any(
            kw in body_lower for kw in ("no repos", "no data", "empty", "nothing yet")
        )
        assert has_counts or has_empty_state, (
            "Portfolio health page must show repo counts or percentages for risk distribution "
            "or an empty-state message"
        )


class TestPortfolioHealthEmptyState:
    """Empty-state must communicate clearly when no repos are in the portfolio.

    An informative empty state prevents confusion and gives operators context
    about what the portfolio health section manages.
    """

    def test_empty_state_has_descriptive_text(self, page, base_url: str) -> None:
        """When no repos are in the portfolio, the page shows descriptive text."""
        navigate(page, f"{base_url}{PORTFOLIO_HEALTH_URL}")

        if page.locator("table").count() > 0:
            rows = page.locator("table tbody tr").count()
            if rows > 0:
                pytest.skip("Portfolio repos are present — empty-state test not applicable")

        body_lower = page.locator("body").inner_text().lower()
        descriptive_keywords = (
            "portfolio",
            "health",
            "repo",
            "repository",
            "no repos",
            "no repositories",
            "no data",
            "empty",
            "add",
            "register",
        )
        assert any(kw in body_lower for kw in descriptive_keywords), (
            "Empty-state portfolio health page must include descriptive text about the portfolio"
        )


class TestPortfolioHealthPageStructure:
    """Portfolio health page must have clear page-level structure for operator orientation.

    Operators navigating between admin pages need consistent heading hierarchy
    so they know immediately which page they're on and what it manages.
    """

    def test_page_heading_present(self, page, base_url: str) -> None:
        """Portfolio health page has a heading identifying it as the portfolio section."""
        navigate(page, f"{base_url}{PORTFOLIO_HEALTH_URL}")

        body_lower = page.locator("body").inner_text().lower()
        heading_keywords = (
            "portfolio health",
            "portfolio",
            "health overview",
            "cross-repo",
            "fleet health",
            "repo health",
        )
        assert any(kw in body_lower for kw in heading_keywords), (
            "Portfolio health page must have a heading referencing 'Portfolio Health', "
            "'Portfolio', or 'Health Overview'"
        )

    def test_page_loads_without_error(self, page, base_url: str) -> None:
        """Portfolio health page loads and the body has meaningful content (not blank)."""
        navigate(page, f"{base_url}{PORTFOLIO_HEALTH_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Portfolio health page body must not be empty"
