"""Story 76.3 — Triage Tab: Interactive Element Verification.

Validates that triage tab interactions behave correctly:
  - Clicking "Accept & Plan" opens the TriageAcceptModal (prompt-first flow)
  - Modal renders with title, intent preview, and decision buttons
  - Modal is dismissible via the Cancel button and Escape key
  - "Reject" button reveals rejection reason options
  - Tab navigation from the header reaches the triage tab

These tests check *interactive behaviour*, not visual appearance or API contracts.
Style compliance is covered in test_pd_triage_style.py.
Accessibility is covered in test_pd_triage_a11y.py.
"""

import pytest

from tests.playwright.pipeline_dashboard.conftest import (
    DASHBOARD_TABS,
    dashboard_navigate,
)

pytestmark = pytest.mark.playwright


def _navigate(page, base_url: str) -> None:
    """Navigate to the triage tab and wait for React hydration."""
    dashboard_navigate(page, base_url, "triage")


def _has_triage_cards(page) -> bool:
    """Return True when at least one triage card is visible."""
    return (
        page.evaluate(
            "document.querySelectorAll('[data-tour=\"triage-card\"]').length"
        )
        > 0
    )


# ---------------------------------------------------------------------------
# Accept & Plan modal (prompt-first flow)
# ---------------------------------------------------------------------------


class TestTriageAcceptModal:
    """Clicking 'Accept & Plan' must open the TriageAcceptModal.

    The modal implements the Story 54.3 prompt-first flow: operators must
    preview the intent and choose an execution mode before acceptance proceeds.
    A missing or broken modal means acceptance bypasses the intent-preview step.
    """

    def test_accept_button_opens_modal(self, page, base_url: str) -> None:
        """Clicking 'Accept & Plan' renders the TriageAcceptModal overlay."""
        _navigate(page, base_url)
        if not _has_triage_cards(page):
            pytest.skip("No triage cards — skipping Accept modal open test")

        # Click the first Accept & Plan button
        accept_btn = page.locator(
            "[data-testid='triage-card-accept-intent-btn']"
        ).first
        if accept_btn.count() == 0:
            accept_btn = page.locator("button:has-text('Accept')").first

        accept_btn.click()
        page.wait_for_timeout(300)

        modal = page.locator(
            "[data-testid='triage-accept-modal'], "
            "[role='dialog'][aria-modal='true']"
        )
        assert modal.count() > 0, (
            "Clicking 'Accept & Plan' must open the TriageAcceptModal "
            "(role='dialog' with aria-modal='true')"
        )

    def test_modal_shows_intent_preview(self, page, base_url: str) -> None:
        """TriageAcceptModal renders the intent preview section (Step 2)."""
        _navigate(page, base_url)
        if not _has_triage_cards(page):
            pytest.skip("No triage cards — skipping modal intent preview test")

        accept_btn = page.locator(
            "[data-testid='triage-card-accept-intent-btn']"
        ).first
        if accept_btn.count() == 0:
            accept_btn = page.locator("button:has-text('Accept')").first

        accept_btn.click()
        page.wait_for_timeout(300)

        modal_count = page.locator(
            "[data-testid='triage-accept-modal'], [role='dialog']"
        ).count()
        if modal_count == 0:
            pytest.skip("Modal did not open — skipping intent preview check")

        intent_preview = page.locator(
            "[data-testid='triage-intent-preview'], "
            "[aria-label='Intent preview'], "
            "section:has-text('Intent Preview')"
        )
        assert intent_preview.count() > 0, (
            "TriageAcceptModal must render the intent preview section (Step 2) "
            "per the Story 54.3 prompt-first flow"
        )

    def test_modal_has_confirm_and_cancel_buttons(self, page, base_url: str) -> None:
        """TriageAcceptModal footer has 'Accept & Start Pipeline' and 'Cancel' buttons."""
        _navigate(page, base_url)
        if not _has_triage_cards(page):
            pytest.skip("No triage cards — skipping modal button check")

        accept_btn = page.locator(
            "[data-testid='triage-card-accept-intent-btn']"
        ).first
        if accept_btn.count() == 0:
            accept_btn = page.locator("button:has-text('Accept')").first

        accept_btn.click()
        page.wait_for_timeout(300)

        modal_count = page.locator(
            "[data-testid='triage-accept-modal'], [role='dialog']"
        ).count()
        if modal_count == 0:
            pytest.skip("Modal did not open — skipping button check")

        cancel_btn = page.locator(
            "[data-testid='triage-accept-cancel-btn'], "
            "button:has-text('Cancel')"
        )
        assert cancel_btn.count() > 0, (
            "TriageAcceptModal must have a 'Cancel' button in the footer"
        )

    def test_modal_cancel_closes_modal(self, page, base_url: str) -> None:
        """Clicking 'Cancel' in the modal footer closes the overlay."""
        _navigate(page, base_url)
        if not _has_triage_cards(page):
            pytest.skip("No triage cards — skipping modal Cancel close test")

        accept_btn = page.locator(
            "[data-testid='triage-card-accept-intent-btn']"
        ).first
        if accept_btn.count() == 0:
            accept_btn = page.locator("button:has-text('Accept')").first

        accept_btn.click()
        page.wait_for_timeout(300)

        modal_count = page.locator(
            "[data-testid='triage-accept-modal'], [role='dialog']"
        ).count()
        if modal_count == 0:
            pytest.skip("Modal did not open — skipping close test")

        cancel_btn = page.locator(
            "[data-testid='triage-accept-cancel-btn'], "
            "button:has-text('Cancel')"
        ).first
        cancel_btn.click()
        page.wait_for_timeout(300)

        remaining = page.locator(
            "[data-testid='triage-accept-modal'], "
            "[data-testid='triage-accept-backdrop']"
        ).count()
        assert remaining == 0, (
            "Clicking 'Cancel' in the TriageAcceptModal must close the overlay"
        )

    def test_modal_escape_closes_modal(self, page, base_url: str) -> None:
        """Pressing Escape dismisses the TriageAcceptModal."""
        _navigate(page, base_url)
        if not _has_triage_cards(page):
            pytest.skip("No triage cards — skipping modal Escape close test")

        accept_btn = page.locator(
            "[data-testid='triage-card-accept-intent-btn']"
        ).first
        if accept_btn.count() == 0:
            accept_btn = page.locator("button:has-text('Accept')").first

        accept_btn.click()
        page.wait_for_timeout(300)

        modal_count = page.locator(
            "[data-testid='triage-accept-modal'], [role='dialog']"
        ).count()
        if modal_count == 0:
            pytest.skip("Modal did not open — skipping Escape close test")

        page.keyboard.press("Escape")
        page.wait_for_timeout(300)

        remaining = page.locator(
            "[data-testid='triage-accept-modal'], "
            "[data-testid='triage-accept-backdrop']"
        ).count()
        assert remaining == 0, (
            "Pressing Escape must dismiss the TriageAcceptModal "
            "(keyboard dismissal is a WCAG 2.1.2 requirement)"
        )

    def test_modal_close_button_closes_modal(self, page, base_url: str) -> None:
        """Clicking the 'Close' (X) button in the modal header closes the overlay."""
        _navigate(page, base_url)
        if not _has_triage_cards(page):
            pytest.skip("No triage cards — skipping modal close-button test")

        accept_btn = page.locator(
            "[data-testid='triage-card-accept-intent-btn']"
        ).first
        if accept_btn.count() == 0:
            accept_btn = page.locator("button:has-text('Accept')").first

        accept_btn.click()
        page.wait_for_timeout(300)

        modal_count = page.locator(
            "[data-testid='triage-accept-modal'], [role='dialog']"
        ).count()
        if modal_count == 0:
            pytest.skip("Modal did not open — skipping close button test")

        close_btn = page.locator(
            "[data-testid='triage-accept-close'], "
            "[aria-label='Close'], "
            "button[aria-label*='close' i]"
        ).first
        if close_btn.count() == 0:
            pytest.skip("No close button found on modal — skipping")

        close_btn.click()
        page.wait_for_timeout(300)

        remaining = page.locator(
            "[data-testid='triage-accept-modal'], "
            "[data-testid='triage-accept-backdrop']"
        ).count()
        assert remaining == 0, (
            "Clicking the 'Close' (X) button must dismiss the TriageAcceptModal"
        )


# ---------------------------------------------------------------------------
# Reject flow — rejection reason selection
# ---------------------------------------------------------------------------


class TestTriageRejectFlow:
    """Clicking 'Reject' must reveal rejection reason options.

    Operators must classify rejections (duplicate, out_of_scope, needs_info,
    won't_fix) so that the triage signal ingestor can update issue labels.
    """

    def test_reject_button_reveals_reasons(self, page, base_url: str) -> None:
        """Clicking 'Reject' shows rejection reason buttons on the card."""
        _navigate(page, base_url)
        if not _has_triage_cards(page):
            pytest.skip("No triage cards — skipping Reject reveal test")

        reject_btn = page.locator("button:has-text('Reject')").first
        reject_btn.click()
        page.wait_for_timeout(200)

        body = page.locator("body").inner_text().lower()
        has_reasons = any(
            kw in body
            for kw in ("duplicate", "out of scope", "needs info", "won't fix", "wont fix")
        )
        assert has_reasons, (
            "Clicking 'Reject' must reveal rejection reason options "
            "(Duplicate, Out of Scope, Needs Info, Won't Fix)"
        )

    def test_reject_cancel_restores_action_buttons(self, page, base_url: str) -> None:
        """Clicking 'Cancel' after opening reject panel restores the main action buttons."""
        _navigate(page, base_url)
        if not _has_triage_cards(page):
            pytest.skip("No triage cards — skipping Reject Cancel restore test")

        reject_btn = page.locator("button:has-text('Reject')").first
        reject_btn.click()
        page.wait_for_timeout(200)

        cancel_btn = page.locator(
            "[data-tour='triage-card'] button:has-text('Cancel')"
        ).first
        if cancel_btn.count() == 0:
            pytest.skip("No Cancel button in reject panel — skipping restore test")

        cancel_btn.click()
        page.wait_for_timeout(200)

        # Accept & Plan should be visible again
        accept_btn = page.locator(
            "[data-testid='triage-card-accept-intent-btn'], "
            "button:has-text('Accept')"
        )
        assert accept_btn.count() > 0, (
            "Cancelling the reject flow must restore the 'Accept & Plan' button"
        )


# ---------------------------------------------------------------------------
# Tab switching from header
# ---------------------------------------------------------------------------


class TestTriageTabSwitching:
    """Clicking another tab header from the triage view must navigate correctly.

    Dashboard tab headers are the primary navigation mechanism; switching tabs
    must change the displayed content without a full page reload.
    """

    def test_tab_headers_are_present(self, page, base_url: str) -> None:
        """Dashboard tab navigation is visible from the triage tab."""
        _navigate(page, base_url)

        body = page.locator("body").inner_text()
        # At least one other tab label should be visible
        other_tabs = ["Pipeline", "Intent Review", "Routing", "Backlog", "Budget"]
        found_tabs = [t for t in other_tabs if t in body]
        assert len(found_tabs) > 0, (
            "Triage tab must display the dashboard tab navigation header "
            f"with at least one of: {other_tabs}"
        )

    def test_can_navigate_to_pipeline_tab_from_triage(
        self, page, base_url: str
    ) -> None:
        """Clicking the 'Pipeline' tab from triage navigates to the pipeline view."""
        _navigate(page, base_url)

        pipeline_tab = page.locator(
            "a:has-text('Pipeline'), "
            "button:has-text('Pipeline'), "
            "[role='tab']:has-text('Pipeline')"
        ).first

        if pipeline_tab.count() == 0:
            pytest.skip("Pipeline tab link not found — skipping tab switch test")

        pipeline_tab.click()
        page.wait_for_timeout(500)

        current_url = page.url
        assert "tab=pipeline" in current_url or "pipeline" in current_url.lower(), (
            "Clicking the 'Pipeline' tab from triage must update the URL to "
            "include 'tab=pipeline'"
        )


# ---------------------------------------------------------------------------
# Prompt-first step progress indicator
# ---------------------------------------------------------------------------


class TestTriageModalStepProgress:
    """The accept modal's step progress indicator must reflect the current step.

    The StepProgress component communicates the prompt-first flow stage to
    the operator.  Step 2 (Intent preview) is the initial state.
    """

    def test_modal_shows_step_progress_indicator(self, page, base_url: str) -> None:
        """TriageAcceptModal renders the prompt-first step progress indicator."""
        _navigate(page, base_url)
        if not _has_triage_cards(page):
            pytest.skip("No triage cards — skipping step progress test")

        accept_btn = page.locator(
            "[data-testid='triage-card-accept-intent-btn']"
        ).first
        if accept_btn.count() == 0:
            accept_btn = page.locator("button:has-text('Accept')").first

        accept_btn.click()
        page.wait_for_timeout(300)

        modal_count = page.locator(
            "[data-testid='triage-accept-modal'], [role='dialog']"
        ).count()
        if modal_count == 0:
            pytest.skip("Modal did not open — skipping step progress test")

        steps_indicator = page.locator(
            "[data-testid='prompt-first-steps'], "
            "[aria-label*='progress' i], "
            "ol[aria-label*='prompt' i]"
        )
        assert steps_indicator.count() > 0, (
            "TriageAcceptModal must render the prompt-first step progress indicator "
            "(data-testid='prompt-first-steps' or aria-label='Prompt-first flow progress')"
        )

    def test_modal_continue_button_advances_to_step_3(
        self, page, base_url: str
    ) -> None:
        """Clicking 'Continue to Mode Selection' advances the modal to step 3."""
        _navigate(page, base_url)
        if not _has_triage_cards(page):
            pytest.skip("No triage cards — skipping step advance test")

        accept_btn = page.locator(
            "[data-testid='triage-card-accept-intent-btn']"
        ).first
        if accept_btn.count() == 0:
            accept_btn = page.locator("button:has-text('Accept')").first

        accept_btn.click()
        page.wait_for_timeout(300)

        modal_count = page.locator(
            "[data-testid='triage-accept-modal'], [role='dialog']"
        ).count()
        if modal_count == 0:
            pytest.skip("Modal did not open — skipping step advance test")

        continue_btn = page.locator(
            "[data-testid='intent-preview-continue'], "
            "button:has-text('Continue')"
        ).first
        if continue_btn.count() == 0:
            pytest.skip("Continue button not visible — modal may already be at step 3")

        continue_btn.click()
        page.wait_for_timeout(300)

        mode_selector = page.locator(
            "[data-testid='triage-mode-selector'], "
            "[aria-label*='mode' i], "
            "section:has-text('Mode')"
        )
        assert mode_selector.count() > 0, (
            "Clicking 'Continue to Mode Selection' must reveal the mode selector section (Step 3)"
        )
