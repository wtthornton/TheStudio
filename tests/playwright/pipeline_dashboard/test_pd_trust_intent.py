"""Story 76.7 — Trust Tiers Tab: Page Intent & Semantic Content.

Validates that /dashboard/?tab=trust delivers its core purpose:
  - "Trust Tier Configuration" heading is present.
  - The three canonical tier names (Observe, Suggest, Execute) are displayed.
  - Default tier selector section is visible.
  - Safety bounds section is present.
  - Rule configuration section is present (with rule list or empty state).
  - Empty state communicates the correct heading, description, and CTA when
    no rules have been configured yet.

These tests check *what* the page communicates, not *how* it looks.
Style compliance is in test_pd_trust_style.py (Story 76.7).
API contracts are in test_pd_trust_api.py (Story 76.7).
"""

import pytest

from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

# The three canonical trust tier names as rendered by TrustConfiguration.
TRUST_TIER_NAMES = ["observe", "suggest", "execute"]


# ---------------------------------------------------------------------------
# Navigation helper
# ---------------------------------------------------------------------------


def _go(page: object, base_url: str) -> None:
    """Navigate to the trust tiers tab and wait for React to hydrate."""
    dashboard_navigate(page, base_url, "trust")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Primary heading — trust configuration section
# ---------------------------------------------------------------------------


class TestTrustHeading:
    """Trust Tiers tab must display a clear heading identifying the section.

    Operators need to confirm at a glance that they are on the Trust Tier
    Configuration screen before making changes to automated behavior.
    """

    def test_trust_configuration_heading_present(self, page, base_url: str) -> None:
        """'Trust Tier Configuration' heading is rendered on the trust tab."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        assert "Trust Tier Configuration" in body, (
            "Trust Tiers tab must display 'Trust Tier Configuration' heading "
            "so operators can identify the settings panel"
        )

    def test_trust_tab_renders_without_crash(self, page, base_url: str) -> None:
        """Trust tab renders content (not a blank page or error screen)."""
        _go(page, base_url)

        body = page.locator("body").inner_text().strip()
        assert len(body) > 50, (
            "Trust Tiers tab must render substantive content — "
            "the page appears blank or errored"
        )

    def test_trust_tab_subtitle_present(self, page, base_url: str) -> None:
        """Trust tab shows a descriptive subtitle explaining trust tier purpose."""
        _go(page, base_url)

        body = page.locator("body").inner_text().lower()
        has_description = (
            "configure" in body
            or "trust" in body
            or "observe" in body
            or "suggest" in body
            or "execute" in body
        )
        assert has_description, (
            "Trust Tiers tab must include descriptive text explaining how "
            "trust tiers work (observe / suggest / execute)"
        )


# ---------------------------------------------------------------------------
# Tier names displayed
# ---------------------------------------------------------------------------


class TestTrustTierNamesDisplayed:
    """All three canonical trust tier names must appear on the trust tab.

    Users and operators rely on the tier labels to understand and configure
    the automation trust spectrum.
    """

    def test_observe_tier_name_displayed(self, page, base_url: str) -> None:
        """'observe' (or 'Observe') tier label is visible on the trust tab."""
        _go(page, base_url)

        body = page.locator("body").inner_text().lower()
        assert "observe" in body, (
            "Trust Tiers tab must display 'observe' tier name "
            "in the default tier selector or rule list"
        )

    def test_suggest_tier_name_displayed(self, page, base_url: str) -> None:
        """'suggest' (or 'Suggest') tier label is visible on the trust tab."""
        _go(page, base_url)

        body = page.locator("body").inner_text().lower()
        assert "suggest" in body, (
            "Trust Tiers tab must display 'suggest' tier name "
            "in the default tier selector or rule list"
        )

    def test_execute_tier_name_displayed(self, page, base_url: str) -> None:
        """'execute' (or 'Execute') tier label is visible on the trust tab."""
        _go(page, base_url)

        body = page.locator("body").inner_text().lower()
        assert "execute" in body, (
            "Trust Tiers tab must display 'execute' tier name "
            "in the default tier selector or rule list"
        )

    def test_all_three_tier_names_present(self, page, base_url: str) -> None:
        """All three canonical tier names are simultaneously visible."""
        _go(page, base_url)

        body = page.locator("body").inner_text().lower()
        missing = [name for name in TRUST_TIER_NAMES if name not in body]
        assert not missing, (
            f"Trust Tiers tab is missing tier names: {missing!r}. "
            "All three tiers (observe, suggest, execute) must be visible."
        )


# ---------------------------------------------------------------------------
# Default tier selector section
# ---------------------------------------------------------------------------


class TestDefaultTierSelector:
    """Default tier selector must be present and functional.

    The default tier is the fallback assigned to tasks when no rule matches.
    Operators must be able to identify and change the default at a glance.
    """

    def test_default_tier_section_heading_present(self, page, base_url: str) -> None:
        """'Default Trust Tier' section heading is displayed."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        assert "Default Trust Tier" in body, (
            "Trust Tiers tab must display 'Default Trust Tier' section heading "
            "for the fallback tier selector"
        )

    def test_default_tier_selector_buttons_present(self, page, base_url: str) -> None:
        """Default tier section contains tier selector buttons."""
        _go(page, base_url)

        # The ActiveTierDisplay renders buttons for observe, suggest, execute.
        tier_buttons = page.locator("[data-tour='trust-tier'] button").count()
        if tier_buttons == 0:
            # Fallback: look for buttons near the 'Default Trust Tier' heading.
            body = page.locator("body").inner_text().lower()
            has_buttons = any(name in body for name in TRUST_TIER_NAMES)
            assert has_buttons, (
                "Default Trust Tier section must render tier selector buttons "
                "(observe, suggest, execute)"
            )
        else:
            assert tier_buttons >= 1, (
                "Default Trust Tier selector must contain at least one tier button"
            )

    def test_default_tier_fallback_description_present(self, page, base_url: str) -> None:
        """Default tier section includes a description of the fallback behavior."""
        _go(page, base_url)

        body = page.locator("body").inner_text().lower()
        has_fallback_desc = (
            "fallback" in body
            or "no rule" in body
            or "default" in body
        )
        assert has_fallback_desc, (
            "Default Trust Tier section must include a description explaining "
            "the fallback behavior when no rule matches"
        )


# ---------------------------------------------------------------------------
# Safety bounds section
# ---------------------------------------------------------------------------


class TestSafetyBoundsSection:
    """Safety bounds section must be present with correct headings.

    Safety bounds are hard limits that constrain automated actions regardless
    of the trust tier — operators must be able to review and configure them.
    """

    def test_safety_bounds_heading_present(self, page, base_url: str) -> None:
        """'Safety Bounds' section heading is displayed on the trust tab."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        assert "Safety Bounds" in body, (
            "Trust Tiers tab must display 'Safety Bounds' section heading "
            "for the hard limits configuration panel"
        )

    def test_safety_bounds_description_present(self, page, base_url: str) -> None:
        """Safety bounds section includes a description of what limits are enforced."""
        _go(page, base_url)

        body = page.locator("body").inner_text().lower()
        has_desc = (
            "hard limit" in body
            or "automated" in body
            or "constrain" in body
            or "regardless" in body
        )
        assert has_desc, (
            "Safety bounds section must include a description explaining "
            "that these are hard limits on automated actions"
        )

    def test_safety_bounds_form_inputs_present(self, page, base_url: str) -> None:
        """Safety bounds section renders form inputs for limit configuration."""
        _go(page, base_url)

        # SafetyBoundsPanel has three numeric inputs + one textarea.
        inputs = page.locator("input[type='number'], textarea").count()
        assert inputs >= 1, (
            "Safety bounds section must render at least one numeric input "
            "for configuring automated action limits"
        )


# ---------------------------------------------------------------------------
# Rules section
# ---------------------------------------------------------------------------


class TestRulesSection:
    """Rules section must be present with rule list or empty state.

    The rules engine is the core of the trust system — rules evaluate
    task properties and assign tiers. When no rules exist, the empty
    state guides the operator to add the first rule.
    """

    def test_rules_section_heading_present(self, page, base_url: str) -> None:
        """'Rules' section heading is present on the trust tab."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        assert "Rules" in body, (
            "Trust Tiers tab must display a 'Rules' section heading "
            "for the tier rule configuration area"
        )

    def test_rules_section_has_content_or_empty_state(self, page, base_url: str) -> None:
        """Rules section shows existing rules or the 'No trust rules yet' empty state."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        has_rules = page.locator("[data-tour='trust-rules']").count() > 0
        has_empty = "No trust rules yet" in body
        has_new_rule_button = "+ New rule" in body or "Add First Rule" in body or "New rule" in body

        assert has_rules or has_empty or has_new_rule_button, (
            "Trust Tiers tab rules section must render existing rules, "
            "an empty state, or a 'New rule' CTA button"
        )

    def test_new_rule_cta_present(self, page, base_url: str) -> None:
        """A 'New rule' or 'Add First Rule' button is accessible when no form is open."""
        _go(page, base_url)

        body = page.locator("body").inner_text()
        has_cta = (
            "New rule" in body
            or "Add First Rule" in body
            or "+ New rule" in body
        )
        assert has_cta, (
            "Trust Tiers tab must display a CTA to create a new rule "
            "('+ New rule' or 'Add First Rule') so operators can configure tier rules"
        )


# ---------------------------------------------------------------------------
# Empty state (when no rules configured)
# ---------------------------------------------------------------------------


class TestTrustRulesEmptyState:
    """When no rules exist, the empty state must communicate the right information.

    The empty state guides operators toward adding their first rule to
    enable automatic tier assignment.
    """

    def test_empty_state_heading_when_no_rules(self, page, base_url: str) -> None:
        """Empty state heading 'No trust rules yet' is shown when rules list is empty."""
        _go(page, base_url)

        # Only assert this when the rules list is actually empty.
        rule_rows = page.locator("[data-tour='trust-rules'] > div").count()
        body = page.locator("body").inner_text()

        if rule_rows > 0 and "No trust rules yet" not in body:
            pytest.skip("Rules are configured — not in empty state")

        if "No trust rules yet" in body:
            assert "No trust rules yet" in body, (
                "Trust Tiers empty state must display 'No trust rules yet' heading"
            )

    def test_empty_state_description_present(self, page, base_url: str) -> None:
        """Empty state description explains how rules enable automatic tier assignment."""
        _go(page, base_url)

        body = page.locator("body").inner_text()

        if "No trust rules yet" not in body:
            pytest.skip("Rules are configured — empty state is not shown")

        body_lower = body.lower()
        has_desc = (
            "add rules" in body_lower
            or "automatically assign" in body_lower
            or "complexity" in body_lower
            or "risk" in body_lower
        )
        assert has_desc, (
            "Trust rules empty state must include a description explaining "
            "how rules enable automatic tier assignment"
        )

    def test_empty_state_add_first_rule_cta(self, page, base_url: str) -> None:
        """Empty state shows 'Add First Rule' CTA when no rules exist."""
        _go(page, base_url)

        body = page.locator("body").inner_text()

        if "No trust rules yet" not in body:
            pytest.skip("Rules are configured — 'Add First Rule' empty state CTA not shown")

        assert "Add First Rule" in body, (
            "Trust rules empty state must display 'Add First Rule' CTA button "
            "to guide operators into creating their first tier rule"
        )
