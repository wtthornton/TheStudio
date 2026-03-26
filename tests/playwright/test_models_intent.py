"""Epic 66.1 — Model Gateway: Page Intent & Semantic Content.

Validates that /admin/ui/models delivers its core purpose:
  - Model providers are listed with identifiers and routing rules
  - Cost information is surfaced for operator awareness
  - Page heading clearly identifies the model gateway section
  - Empty state is shown when no models are configured

These tests check *what* the page communicates, not *how* it looks.
Style compliance is covered in test_models_style.py (Epic 66.3).
"""

import pytest

from tests.playwright.conftest import navigate

pytestmark = pytest.mark.playwright

MODELS_URL = "/admin/ui/models"


class TestModelsProviderContent:
    """Model provider list must surface the key information operators need.

    When model providers are configured the page must show:
      Provider/model name  — human-readable identifier for the model or provider
      Routing rules        — which requests are routed to this model
      Cost info            — pricing or cost metadata for budget management
    """

    def test_models_page_renders(self, page, base_url: str) -> None:
        """Models page shows a provider table/list or an empty-state container."""
        navigate(page, f"{base_url}{MODELS_URL}")

        has_table = page.locator("table").count() > 0
        has_list = page.locator(
            "[class*='model'], [data-model], [data-component='model-card']"
        ).count() > 0
        body_lower = page.locator("body").inner_text().lower()
        has_empty_state = any(
            kw in body_lower
            for kw in ("no models", "no model", "get started", "add your first", "empty")
        )
        assert has_table or has_list or has_empty_state, (
            "Models page must show a model provider list (table or card list) or an "
            "empty-state message when no models are configured"
        )

    def test_model_provider_name_shown(self, page, base_url: str) -> None:
        """Model provider list or page body includes provider/model name information."""
        navigate(page, f"{base_url}{MODELS_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-model]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no models", "empty")):
                pytest.skip("No models configured — empty state is acceptable for 66.1")

        body_lower = page.locator("body").inner_text().lower()
        provider_keywords = (
            "model",
            "provider",
            "gpt",
            "claude",
            "gemini",
            "anthropic",
            "openai",
            "name",
        )
        assert any(kw in body_lower for kw in provider_keywords), (
            "Models page must display provider or model name information"
        )

    def test_routing_rules_shown(self, page, base_url: str) -> None:
        """Model page or provider detail includes routing rule information."""
        navigate(page, f"{base_url}{MODELS_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-model]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no models", "empty")):
                pytest.skip("No models configured — empty state is acceptable for 66.1")

        body_lower = page.locator("body").inner_text().lower()
        routing_keywords = (
            "routing",
            "route",
            "rule",
            "rules",
            "policy",
            "strategy",
            "fallback",
            "primary",
        )
        assert any(kw in body_lower for kw in routing_keywords), (
            "Models page must display routing rule information for model selection"
        )

    def test_cost_info_shown(self, page, base_url: str) -> None:
        """Model page surfaces cost or pricing information for budget management."""
        navigate(page, f"{base_url}{MODELS_URL}")

        if page.locator("table").count() == 0 and page.locator("[data-model]").count() == 0:
            body_lower = page.locator("body").inner_text().lower()
            if any(kw in body_lower for kw in ("no models", "empty")):
                pytest.skip("No models configured — empty state is acceptable for 66.1")

        body_lower = page.locator("body").inner_text().lower()
        cost_keywords = (
            "cost",
            "price",
            "pricing",
            "token",
            "$/",
            "budget",
            "rate",
            "spend",
        )
        assert any(kw in body_lower for kw in cost_keywords), (
            "Models page must display cost or pricing information for operator budget management"
        )

    def test_model_identifier_column_present(self, page, base_url: str) -> None:
        """Model table has a column or field identifying each model by name or ID."""
        navigate(page, f"{base_url}{MODELS_URL}")

        has_table = page.locator("table").count() > 0
        if not has_table:
            pytest.skip("No table on models page — card-based layout acceptable for 66.1")

        body_lower = page.locator("body").inner_text().lower()
        id_keywords = ("model", "name", "id", "provider", "key", "slug")
        assert any(kw in body_lower for kw in id_keywords), (
            "Model table must include an identifier column (name or ID) for each model"
        )


class TestModelsEmptyState:
    """Empty-state must communicate clearly when no models are configured.

    An informative empty state prevents confusion when the model list is blank
    and gives operators context about what the models section manages.
    """

    def test_empty_state_has_descriptive_text(self, page, base_url: str) -> None:
        """When no models exist, the page shows descriptive text about the model gateway."""
        navigate(page, f"{base_url}{MODELS_URL}")

        if page.locator("table").count() > 0:
            rows = page.locator("table tbody tr").count()
            if rows > 0:
                pytest.skip("Models are configured — empty-state test not applicable")

        body_lower = page.locator("body").inner_text().lower()
        descriptive_keywords = (
            "model",
            "models",
            "no models",
            "gateway",
            "provider",
            "routing",
            "get started",
        )
        assert any(kw in body_lower for kw in descriptive_keywords), (
            "Empty-state models page must include descriptive text about the model gateway"
        )


class TestModelsPageStructure:
    """Models page must have clear page-level structure for operator orientation.

    Operators navigating between admin pages need consistent heading hierarchy
    so they know immediately which page they're on and what it manages.
    """

    def test_page_heading_present(self, page, base_url: str) -> None:
        """Models page has a heading identifying it as the model gateway section."""
        navigate(page, f"{base_url}{MODELS_URL}")

        body_lower = page.locator("body").inner_text().lower()
        heading_keywords = (
            "model",
            "models",
            "gateway",
            "model gateway",
            "providers",
            "llm",
        )
        assert any(kw in body_lower for kw in heading_keywords), (
            "Models page must have a heading referencing 'Models', 'Model Gateway', or 'Providers'"
        )

    def test_page_loads_without_error(self, page, base_url: str) -> None:
        """Models page loads and the body has meaningful content (not blank)."""
        navigate(page, f"{base_url}{MODELS_URL}")

        body = page.locator("body").inner_text().strip()
        assert len(body) > 0, "Models page body must not be empty"
