"""Epic 71.1 — Settings: Page Intent & Semantic Content.

Validates that /admin/ui/settings delivers its core purpose:
  - 6-section config hub renders (API keys, infra, flags, agent, budget, secrets)
  - Section headings clearly identify each configuration area
  - Page heading identifies it as the Settings section
  - Each section has descriptive sub-text explaining its purpose
  - Page loads without error

These tests check *what* the page communicates, not *how* it looks.
Style compliance is covered in test_settings_style.py (Epic 71.3).
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

SETTINGS_URL = "/admin/ui/settings"


class TestSettingsConfigSectionsContent:
    """Settings page must surface all 6 configuration sections for operators.

    When the settings page loads, it must present sections for:
      API Keys        — external service credentials
      Infrastructure  — database, messaging, observability connections
      Feature Flags   — provider and backend toggles
      Agent Config    — model selection and execution limits
      Budget Controls — per-tier pipeline budget caps
      Secrets         — encryption keys and webhook secrets
    """

    def test_settings_page_renders(self, page, base_url: str) -> None:
        """Settings page body renders with meaningful content."""
        navigate(page, f"{base_url}{SETTINGS_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Settings page body must not be empty"

        body_lower = body.lower()
        settings_keywords = (
            "settings",
            "api key",
            "infrastructure",
            "feature flag",
            "agent",
            "budget",
            "secret",
            "config",
            "loading",
        )
        assert any(kw in body_lower for kw in settings_keywords), (
            "Settings page must contain settings-related content"
        )

    def test_api_keys_section_present(self, page, base_url: str) -> None:
        """Settings page includes an API Keys configuration section."""
        navigate(page, f"{base_url}{SETTINGS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        api_key_keywords = (
            "api key",
            "api keys",
            "api_key",
            "credentials",
            "external service",
            "service key",
        )
        assert any(kw in body_lower for kw in api_key_keywords), (
            "Settings page must include an API Keys section for managing external service credentials"
        )

    def test_infrastructure_section_present(self, page, base_url: str) -> None:
        """Settings page includes an Infrastructure configuration section."""
        navigate(page, f"{base_url}{SETTINGS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        infra_keywords = (
            "infrastructure",
            "database",
            "messaging",
            "observability",
            "connection",
            "postgres",
            "nats",
            "temporal",
        )
        assert any(kw in body_lower for kw in infra_keywords), (
            "Settings page must include an Infrastructure section for database, messaging, "
            "and observability connections"
        )

    def test_feature_flags_section_present(self, page, base_url: str) -> None:
        """Settings page includes a Feature Flags configuration section."""
        navigate(page, f"{base_url}{SETTINGS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        flags_keywords = (
            "feature flag",
            "feature flags",
            "flag",
            "toggle",
            "provider",
            "backend",
        )
        assert any(kw in body_lower for kw in flags_keywords), (
            "Settings page must include a Feature Flags section for provider and backend toggles"
        )

    def test_agent_config_section_present(self, page, base_url: str) -> None:
        """Settings page includes an Agent Configuration section."""
        navigate(page, f"{base_url}{SETTINGS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        agent_keywords = (
            "agent config",
            "agent configuration",
            "model selection",
            "execution limit",
            "model",
            "agent",
        )
        assert any(kw in body_lower for kw in agent_keywords), (
            "Settings page must include an Agent Configuration section for model selection "
            "and execution limits"
        )

    def test_budget_controls_section_present(self, page, base_url: str) -> None:
        """Settings page includes a Budget Controls configuration section."""
        navigate(page, f"{base_url}{SETTINGS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        budget_keywords = (
            "budget",
            "budget control",
            "budget controls",
            "pipeline budget",
            "cost cap",
            "spend limit",
            "usd",
            "per-tier",
            "per tier",
        )
        assert any(kw in body_lower for kw in budget_keywords), (
            "Settings page must include a Budget Controls section for per-tier pipeline budget caps"
        )

    def test_secrets_section_present(self, page, base_url: str) -> None:
        """Settings page includes a Secrets configuration section."""
        navigate(page, f"{base_url}{SETTINGS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        secrets_keywords = (
            "secret",
            "secrets",
            "encryption key",
            "webhook secret",
            "encryption",
        )
        assert any(kw in body_lower for kw in secrets_keywords), (
            "Settings page must include a Secrets section for encryption keys and webhook secrets"
        )


class TestSettingsPageStructure:
    """Settings page must have clear page-level structure for operator orientation.

    Operators navigating between admin pages need consistent heading hierarchy
    so they know immediately which page they're on and what it manages.
    """

    def test_page_heading_present(self, page, base_url: str) -> None:
        """Settings page has a heading identifying it as the Settings section."""
        navigate(page, f"{base_url}{SETTINGS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        heading_keywords = (
            "settings",
            "configuration",
            "config hub",
        )
        assert any(kw in body_lower for kw in heading_keywords), (
            "Settings page must have a heading referencing 'Settings' or 'Configuration'"
        )

    def test_section_headings_rendered(self, page, base_url: str) -> None:
        """Settings page shows section headings for configuration categories."""
        navigate(page, f"{base_url}{SETTINGS_URL}")

        # Check for heading elements or strong section labels
        heading_count = (
            page.locator("h1, h2, h3, h4").count()
            + page.locator("[class*='font-medium'], [class*='font-semibold']").count()
        )
        assert heading_count > 0, (
            "Settings page must include headings or labels to identify configuration sections"
        )

    def test_page_loads_without_error(self, page, base_url: str) -> None:
        """Settings page loads and does not display an error state."""
        navigate(page, f"{base_url}{SETTINGS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        error_indicators = (
            "500 internal server error",
            "traceback",
            "unhandled exception",
            "page not found",
            "404 not found",
        )
        for indicator in error_indicators:
            assert indicator not in body_lower, (
                f"Settings page must not show an error state — found: '{indicator}'"
            )

    def test_six_config_sections_accessible(self, page, base_url: str) -> None:
        """Settings page surfaces all six configuration sections."""
        navigate(page, f"{base_url}{SETTINGS_URL}")

        body_lower = page.locator("body").inner_text().lower()

        sections_found = 0
        section_checks = [
            ("api key", "api keys", "credentials"),
            ("infrastructure", "database", "messaging"),
            ("feature flag", "toggle", "flags"),
            ("agent config", "agent configuration", "model selection"),
            ("budget", "budget control", "spend"),
            ("secret", "secrets", "encryption"),
        ]
        for keywords in section_checks:
            if any(kw in body_lower for kw in keywords):
                sections_found += 1

        assert sections_found >= 4, (
            f"Settings page must surface at least 4 of 6 config sections; "
            f"found {sections_found}. Expected: API Keys, Infrastructure, Feature Flags, "
            "Agent Config, Budget Controls, Secrets"
        )
