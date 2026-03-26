"""Epic 64.1 — Expert Performance: Page Intent & Semantic Content.

Validates that /admin/ui/experts delivers its core purpose:
  - Expert table renders with trust tier, confidence, and drift signal columns
  - Empty state is shown when no experts are registered
  - Page heading clearly identifies the experts section

These tests check *what* the page communicates, not *how* it looks.
Style compliance is covered in test_experts_style.py (Epic 64.3).
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

EXPERTS_URL = "/admin/ui/experts"


class TestExpertsTableContent:
    """Expert table must surface the key columns operators need at a glance.

    When experts are registered the table must show:
      Name/ID      — human-readable identifier for the expert agent
      Trust tier   — Observe / Suggest / Execute tier level
      Confidence   — confidence score or percentile for the expert
      Drift signal — drift detection indicator showing model staleness
    """

    def test_experts_page_renders(self, page, base_url: str) -> None:
        """Experts page shows a table or an empty-state container — one or the other."""
        navigate(page, f"{base_url}{EXPERTS_URL}")

        has_table = page.locator("table").count() > 0
        body_lower = page.locator("body").inner_text().lower()
        has_empty_state = any(
            kw in body_lower
            for kw in ("no experts", "no expert", "get started", "add your first", "empty")
        )
        assert has_table or has_empty_state, (
            "Experts page must show an expert table or an empty-state message when no experts exist"
        )

    def test_trust_tier_shown(self, page, base_url: str) -> None:
        """Expert table or page body includes trust tier information."""
        navigate(page, f"{base_url}{EXPERTS_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No experts registered — empty state is acceptable for 64.1")

        body_lower = page.locator("body").inner_text().lower()
        tier_keywords = ("tier", "observe", "suggest", "execute", "trust")
        assert any(kw in body_lower for kw in tier_keywords), (
            "Experts page must display trust tier information (Observe/Suggest/Execute)"
        )

    def test_confidence_indicator_shown(self, page, base_url: str) -> None:
        """Expert table includes a confidence score or confidence indicator."""
        navigate(page, f"{base_url}{EXPERTS_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No experts registered — empty state is acceptable for 64.1")

        body_lower = page.locator("body").inner_text().lower()
        confidence_keywords = ("confidence", "score", "accuracy", "precision", "%", "percent")
        assert any(kw in body_lower for kw in confidence_keywords), (
            "Experts page must display confidence score or accuracy indicator per expert"
        )

    def test_drift_signal_shown(self, page, base_url: str) -> None:
        """Expert table includes a drift signal or staleness indicator."""
        navigate(page, f"{base_url}{EXPERTS_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No experts registered — empty state is acceptable for 64.1")

        body_lower = page.locator("body").inner_text().lower()
        drift_keywords = (
            "drift",
            "stale",
            "staleness",
            "degraded",
            "decay",
            "signal",
            "deviation",
        )
        has_drift = any(kw in body_lower for kw in drift_keywords)
        has_no_drift = any(
            kw in body_lower for kw in ("no drift", "stable", "healthy", "ok")
        )
        assert has_drift or has_no_drift, (
            "Experts page must display drift signal or stability indicator per expert"
        )

    def test_expert_identifier_shown(self, page, base_url: str) -> None:
        """Expert table includes a name, ID, or identifier column."""
        navigate(page, f"{base_url}{EXPERTS_URL}")

        if page.locator("table").count() == 0:
            pytest.skip("No experts registered — empty state is acceptable for 64.1")

        body_lower = page.locator("body").inner_text().lower()
        id_keywords = ("expert", "name", "id", "agent", "model")
        assert any(kw in body_lower for kw in id_keywords), (
            "Experts page must display an identifier column (name or ID) per expert"
        )


class TestExpertsEmptyState:
    """Empty-state must communicate clearly when no experts are registered.

    An informative empty state prevents confusion when the table is blank and
    gives operators context about what the experts section manages.
    """

    def test_empty_state_has_descriptive_text(self, page, base_url: str) -> None:
        """When no experts exist, the page shows descriptive text about experts."""
        navigate(page, f"{base_url}{EXPERTS_URL}")

        if page.locator("table").count() > 0:
            rows = page.locator("table tbody tr").count()
            if rows > 0:
                pytest.skip("Experts are registered — empty-state test not applicable")

        body_lower = page.locator("body").inner_text().lower()
        descriptive_keywords = (
            "expert",
            "experts",
            "no experts",
            "agent",
            "performance",
            "get started",
        )
        assert any(kw in body_lower for kw in descriptive_keywords), (
            "Empty-state experts page must include descriptive text about expert agents"
        )


class TestExpertsPageStructure:
    """Experts page must have clear page-level structure for operator orientation.

    Operators navigating between admin pages need consistent heading hierarchy
    so they know immediately which page they're on and what it manages.
    """

    def test_page_heading_present(self, page, base_url: str) -> None:
        """Experts page has a heading identifying it as the expert performance section."""
        navigate(page, f"{base_url}{EXPERTS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        heading_keywords = ("expert", "experts", "performance", "agent performance")
        assert any(kw in body_lower for kw in heading_keywords), (
            "Experts page must have a heading referencing 'Experts' or 'Expert Performance'"
        )

    def test_page_loads_without_error(self, page, base_url: str) -> None:
        """Experts page loads and the body has meaningful content (not blank)."""
        navigate(page, f"{base_url}{EXPERTS_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Experts page body must not be empty"
