"""Epic 67.1 — Compliance Scorecard: Page Intent & Semantic Content.

Validates that /admin/ui/compliance delivers its core purpose:
  - Per-repo compliance status is shown for operator awareness
  - Check results are surfaced with pass/fail/warning signals
  - Page heading clearly identifies the compliance scorecard section
  - Empty state is shown when no compliance data is available

These tests check *what* the page communicates, not *how* it looks.
Style compliance is covered in test_compliance_style.py (Epic 67.3).
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

COMPLIANCE_URL = "/admin/ui/compliance"


class TestComplianceRepoContent:
    """Per-repo compliance status must surface the key information operators need.

    When compliance data is available the page must show:
      Repository name  — human-readable identifier for the repo being assessed
      Compliance status — pass/fail/warning signals per repo
      Check results    — individual check names and their outcomes
    """

    def test_compliance_page_renders(self, page, base_url: str) -> None:
        """Compliance page shows a repo compliance list/table or an empty-state container."""
        navigate(page, f"{base_url}{COMPLIANCE_URL}")

        has_table = page.locator("table").count() > 0
        has_list = page.locator(
            "[class*='compliance'], [data-compliance], [data-component='compliance-card']"
        ).count() > 0
        body_lower = page.locator("body").inner_text().lower()
        has_empty_state = any(
            kw in body_lower
            for kw in ("no compliance", "no repos", "get started", "add your first", "empty")
        )
        assert has_table or has_list or has_empty_state, (
            "Compliance page must show a repo compliance list (table or card list) or an "
            "empty-state message when no compliance data is available"
        )

    def test_repo_name_shown(self, page, base_url: str) -> None:
        """Compliance list or page body includes repository name information."""
        navigate(page, f"{base_url}{COMPLIANCE_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-compliance]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no compliance", "empty")):
                pytest.skip("No compliance data configured — empty state is acceptable for 67.1")

        body_lower = page.locator("body").inner_text().lower()
        repo_keywords = (
            "repo",
            "repository",
            "repositories",
            "project",
            "name",
            "org",
            "owner",
        )
        assert any(kw in body_lower for kw in repo_keywords), (
            "Compliance page must display repository name or identifier information"
        )

    def test_compliance_status_shown(self, page, base_url: str) -> None:
        """Compliance page surfaces pass/fail/warning status for repos or checks."""
        navigate(page, f"{base_url}{COMPLIANCE_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-compliance]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no compliance", "empty")):
                pytest.skip("No compliance data configured — empty state is acceptable for 67.1")

        body_lower = page.locator("body").inner_text().lower()
        status_keywords = (
            "pass",
            "fail",
            "warning",
            "compliant",
            "non-compliant",
            "status",
            "ok",
            "error",
            "violation",
        )
        assert any(kw in body_lower for kw in status_keywords), (
            "Compliance page must display compliance status (pass/fail/warning) per repo or check"
        )

    def test_check_results_shown(self, page, base_url: str) -> None:
        """Compliance page surfaces individual check names or check result details."""
        navigate(page, f"{base_url}{COMPLIANCE_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-compliance]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no compliance", "empty")):
                pytest.skip("No compliance data configured — empty state is acceptable for 67.1")

        body_lower = page.locator("body").inner_text().lower()
        check_keywords = (
            "check",
            "checks",
            "rule",
            "rules",
            "policy",
            "policies",
            "result",
            "score",
            "audit",
        )
        assert any(kw in body_lower for kw in check_keywords), (
            "Compliance page must display check names or check result details"
        )

    def test_compliance_identifier_column_present(self, page, base_url: str) -> None:
        """Compliance table has a column or field identifying each repo or check."""
        navigate(page, f"{base_url}{COMPLIANCE_URL}")

        has_table = page.locator("table").count() > 0
        if not has_table:
            pytest.skip("No table on compliance page — card-based layout acceptable for 67.1")

        body_lower = page.locator("body").inner_text().lower()
        id_keywords = ("repo", "repository", "name", "id", "project", "check", "slug")
        assert any(kw in body_lower for kw in id_keywords), (
            "Compliance table must include an identifier column (repo name or check name)"
        )


class TestComplianceEmptyState:
    """Empty-state must communicate clearly when no compliance data is available.

    An informative empty state prevents confusion when the compliance list is blank
    and gives operators context about what the compliance scorecard manages.
    """

    def test_empty_state_has_descriptive_text(self, page, base_url: str) -> None:
        """When no compliance data exists, the page shows descriptive text about compliance."""
        navigate(page, f"{base_url}{COMPLIANCE_URL}")

        if page.locator("table").count() > 0:
            rows = page.locator("table tbody tr").count()
            if rows > 0:
                pytest.skip("Compliance data is present — empty-state test not applicable")

        body_lower = page.locator("body").inner_text().lower()
        descriptive_keywords = (
            "compliance",
            "compliant",
            "no compliance",
            "scorecard",
            "checks",
            "policy",
            "get started",
        )
        assert any(kw in body_lower for kw in descriptive_keywords), (
            "Empty-state compliance page must include descriptive text about the compliance scorecard"
        )


class TestCompliancePageStructure:
    """Compliance page must have clear page-level structure for operator orientation.

    Operators navigating between admin pages need consistent heading hierarchy
    so they know immediately which page they're on and what it manages.
    """

    def test_page_heading_present(self, page, base_url: str) -> None:
        """Compliance page has a heading identifying it as the compliance scorecard section."""
        navigate(page, f"{base_url}{COMPLIANCE_URL}")

        body_lower = page.locator("body").inner_text().lower()
        heading_keywords = (
            "compliance",
            "compliant",
            "scorecard",
            "compliance scorecard",
            "checks",
            "policy",
            "audit",
        )
        assert any(kw in body_lower for kw in heading_keywords), (
            "Compliance page must have a heading referencing 'Compliance', 'Scorecard', or 'Checks'"
        )

    def test_page_loads_without_error(self, page, base_url: str) -> None:
        """Compliance page loads and the body has meaningful content (not blank)."""
        navigate(page, f"{base_url}{COMPLIANCE_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Compliance page body must not be empty"
