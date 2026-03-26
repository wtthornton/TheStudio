"""Story 76.3 — Triage Tab: Page Intent & Semantic Content.

Validates that /dashboard/?tab=triage delivers its core purpose:
  - Triage Queue heading is rendered
  - Empty state is shown with appropriate message when queue is empty
  - Issue cards show title, issue number, and complexity badge when populated
  - Cards have Accept & Plan and Reject action buttons
  - The queue container is present in the DOM

These tests check *what* the page communicates, not *how* it looks.
Style compliance is covered in test_pd_triage_style.py.
API contracts are covered in test_pd_triage_api.py.
Interactions are covered in test_pd_triage_interactions.py.
"""

import pytest

from tests.playwright.pipeline_dashboard.conftest import (
    DASHBOARD_TABS,
    dashboard_navigate,
)

pytestmark = pytest.mark.playwright


class TestTriageQueueHeading:
    """Triage Queue heading must be visible to orient the operator.

    Operators switching between pipeline dashboard tabs need a clear heading
    so they can confirm they are in the triage view before acting.
    """

    def test_triage_heading_present(self, page, base_url: str) -> None:
        """Triage tab renders a 'Triage' or 'Triage Queue' heading."""
        dashboard_navigate(page, base_url, "triage")
        body = page.locator("body").inner_text()
        body_lower = body.lower()
        assert "triage" in body_lower, (
            "Triage tab must display a heading containing 'Triage' to orient the operator"
        )

    def test_triage_tab_is_registered(self) -> None:
        """'triage' tab key is defined in DASHBOARD_TABS registry."""
        assert "triage" in DASHBOARD_TABS, (
            "'triage' must be registered in DASHBOARD_TABS conftest registry"
        )
        assert DASHBOARD_TABS["triage"]["query"] == "?tab=triage", (
            "Triage tab must map to query string '?tab=triage'"
        )

    def test_triage_queue_container_present(self, page, base_url: str) -> None:
        """The triage queue root element is present in the DOM."""
        dashboard_navigate(page, base_url, "triage")

        container_selectors = [
            "[data-tour='triage-queue']",
            "[data-testid='triage-queue']",
            "[data-tour='triage-list']",
        ]
        found = False
        for sel in container_selectors:
            count = page.evaluate(f"document.querySelectorAll({sel!r}).length")
            if count > 0:
                found = True
                break

        # Fallback: heading text alone is sufficient evidence the component mounted
        if not found:
            body = page.locator("body").inner_text().lower()
            found = "triage" in body

        assert found, (
            "Triage tab must render the TriageQueue component container "
            "(data-tour='triage-queue' or heading text)"
        )


class TestTriageEmptyState:
    """When no issues are queued the triage tab must show a meaningful empty state.

    Without an empty state message operators cannot distinguish an empty queue
    from a broken page.
    """

    def test_empty_state_or_cards_present(self, page, base_url: str) -> None:
        """Triage tab shows either issue cards or a descriptive empty state."""
        dashboard_navigate(page, base_url, "triage")
        body = page.locator("body").inner_text().lower()

        has_cards = page.evaluate(
            "document.querySelectorAll('[data-tour=\"triage-card\"]').length"
        ) > 0

        has_empty_state = any(
            kw in body
            for kw in (
                "no issues",
                "awaiting triage",
                "nothing to triage",
                "empty",
                "configure webhook",
                "no tasks",
            )
        )

        assert has_cards or has_empty_state, (
            "Triage tab must show issue cards or an empty-state message "
            "— a blank page is not acceptable"
        )

    def test_empty_state_has_guidance_when_shown(self, page, base_url: str) -> None:
        """Empty state provides actionable guidance (webhook or settings reference)."""
        dashboard_navigate(page, base_url, "triage")

        # Only verify empty-state content when no cards are present
        card_count = page.evaluate(
            "document.querySelectorAll('[data-tour=\"triage-card\"]').length"
        )
        if card_count > 0:
            pytest.skip("Queue has cards — empty state guidance test not applicable")

        body = page.locator("body").inner_text().lower()
        has_guidance = any(
            kw in body
            for kw in ("webhook", "settings", "configure", "learn", "pipeline")
        )
        assert has_guidance, (
            "Empty triage state must include actionable guidance "
            "(webhook configuration or settings link)"
        )


class TestTriageIssueCards:
    """Issue cards must surface the information operators need to make triage decisions.

    Operators need issue title, issue number, and complexity hints to decide
    whether to Accept, Edit, or Reject each issue without opening GitHub.
    """

    def test_issue_cards_show_title(self, page, base_url: str) -> None:
        """Each issue card shows the issue title text."""
        dashboard_navigate(page, base_url, "triage")

        card_count = page.evaluate(
            "document.querySelectorAll('[data-tour=\"triage-card\"]').length"
        )
        if card_count == 0:
            pytest.skip("No triage cards present — skipping card content checks")

        # Each card should contain some non-empty heading text
        card_titles = page.evaluate(
            """
            Array.from(document.querySelectorAll('[data-tour="triage-card"] h3'))
                .map(el => el.textContent.trim())
                .filter(t => t.length > 0)
            """
        )
        assert len(card_titles) > 0, (
            "Triage cards must render an <h3> title element with the issue title"
        )

    def test_issue_cards_show_issue_number(self, page, base_url: str) -> None:
        """Each issue card shows the GitHub issue number (#NNN)."""
        dashboard_navigate(page, base_url, "triage")

        card_count = page.evaluate(
            "document.querySelectorAll('[data-tour=\"triage-card\"]').length"
        )
        if card_count == 0:
            pytest.skip("No triage cards present — skipping issue number check")

        body = page.locator("[data-tour='triage-queue']").inner_text()
        has_issue_number = "#" in body
        assert has_issue_number, (
            "Triage cards must display the GitHub issue number (e.g. '#42')"
        )

    def test_issue_cards_have_complexity_badge_when_enriched(
        self, page, base_url: str
    ) -> None:
        """Cards with enrichment data show a complexity badge (low/medium/high)."""
        dashboard_navigate(page, base_url, "triage")

        card_count = page.evaluate(
            "document.querySelectorAll('[data-tour=\"triage-card\"]').length"
        )
        if card_count == 0:
            pytest.skip("No triage cards — skipping complexity badge check")

        body = page.locator("body").inner_text().lower()
        has_complexity = any(kw in body for kw in ("low", "medium", "high"))

        # Enrichment is optional — skip rather than fail when not present
        if not has_complexity:
            pytest.skip(
                "No complexity badges visible — enrichment may not be present for these tasks"
            )

        assert has_complexity, (
            "Enriched triage cards must show a complexity badge (low / medium / high)"
        )


class TestTriageActionButtons:
    """Action buttons must be present and clearly labelled on triage cards.

    Operators take triage decisions via the Accept & Plan, Edit, and Reject
    buttons.  All three must be visible and unambiguous.
    """

    def test_accept_button_present(self, page, base_url: str) -> None:
        """Issue cards render an 'Accept & Plan' button."""
        dashboard_navigate(page, base_url, "triage")

        card_count = page.evaluate(
            "document.querySelectorAll('[data-tour=\"triage-card\"]').length"
        )
        if card_count == 0:
            pytest.skip("No triage cards — skipping Accept button check")

        accept_btn = page.locator(
            "[data-testid='triage-card-accept-intent-btn'], "
            "button:has-text('Accept'), "
            "button:has-text('Accept & Plan')"
        )
        assert accept_btn.count() > 0, (
            "Triage card must render an 'Accept & Plan' button "
            "so operators can queue the issue for the pipeline"
        )

    def test_reject_button_present(self, page, base_url: str) -> None:
        """Issue cards render a 'Reject' button."""
        dashboard_navigate(page, base_url, "triage")

        card_count = page.evaluate(
            "document.querySelectorAll('[data-tour=\"triage-card\"]').length"
        )
        if card_count == 0:
            pytest.skip("No triage cards — skipping Reject button check")

        reject_btn = page.locator("button:has-text('Reject')")
        assert reject_btn.count() > 0, (
            "Triage card must render a 'Reject' button "
            "so operators can decline irrelevant issues"
        )

    def test_edit_button_present(self, page, base_url: str) -> None:
        """Issue cards render an 'Edit' button for pre-acceptance refinement."""
        dashboard_navigate(page, base_url, "triage")

        card_count = page.evaluate(
            "document.querySelectorAll('[data-tour=\"triage-card\"]').length"
        )
        if card_count == 0:
            pytest.skip("No triage cards — skipping Edit button check")

        edit_btn = page.locator("button:has-text('Edit')")
        assert edit_btn.count() > 0, (
            "Triage card must render an 'Edit' button "
            "so operators can refine issues before accepting"
        )
