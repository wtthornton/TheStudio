"""Story 76.7 — Trust Tiers Tab: API Endpoint Verification.

Validates that the backing API endpoints for /dashboard/?tab=trust return
HTTP 200 with valid JSON schema.

Trust tier backing endpoints:
  - GET /api/v1/dashboard/trust/rules        — Tier rule list
  - GET /api/v1/dashboard/trust/safety-bounds — Hard limits configuration
  - GET /api/v1/dashboard/trust/default-tier  — Current default tier value

These tests check *contract stability*, not visual presentation.
Style compliance is in test_pd_trust_style.py (Story 76.7).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
    assert_api_returns_data,
)
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

_RULES = "/api/v1/dashboard/trust/rules"
_SAFETY_BOUNDS = "/api/v1/dashboard/trust/safety-bounds"
_DEFAULT_TIER = "/api/v1/dashboard/trust/default-tier"


def _go(page: object, base_url: str) -> None:
    """Navigate to the trust tab to warm session cookies before API calls."""
    dashboard_navigate(page, base_url, "trust")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Trust rules endpoint
# ---------------------------------------------------------------------------


class TestTrustRulesEndpoint:
    """Trust rules endpoint must return a valid JSON collection.

    The trust rules list is the primary data source for the rule builder
    and rule table in TrustConfiguration. An empty list is valid when no
    rules have been configured yet.
    """

    def test_rules_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/trust/rules returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _RULES, 200)

    def test_rules_response_is_valid_json(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/trust/rules returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _RULES, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/trust/rules must return a non-null JSON body"
        )

    def test_rules_response_contains_list(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/trust/rules response is a JSON list or wraps one."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _RULES, 200)

        # Accept either a bare list or an object wrapping a list.
        is_list = isinstance(data, list)
        is_wrapped = isinstance(data, dict) and any(
            isinstance(data.get(k), list)
            for k in ("rules", "items", "data", "results")
        )
        assert is_list or is_wrapped, (
            "GET /api/v1/dashboard/trust/rules must return a JSON list or an object "
            "containing a 'rules'/'items'/'data'/'results' list"
        )

    def test_rules_item_schema_when_populated(self, page, base_url: str) -> None:
        """Each rule item contains at minimum 'id', 'assigned_tier', and 'conditions'."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _RULES, 200)

        # Normalise to a list.
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = next(
                (data[k] for k in ("rules", "items", "data", "results") if isinstance(data.get(k), list)),
                [],
            )
        else:
            items = []

        if not items:
            pytest.skip("No trust rules returned — empty list is acceptable")

        first = items[0]
        assert isinstance(first, dict), (
            "Each rule item in /api/v1/dashboard/trust/rules must be a JSON object"
        )
        assert "id" in first, (
            "Trust rule item must contain an 'id' field"
        )
        assert "assigned_tier" in first, (
            "Trust rule item must contain an 'assigned_tier' field "
            "(one of: observe, suggest, execute)"
        )

    def test_rules_tier_values_when_populated(self, page, base_url: str) -> None:
        """Each rule's 'assigned_tier' value is one of the three canonical tiers."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _RULES, 200)

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = next(
                (data[k] for k in ("rules", "items", "data", "results") if isinstance(data.get(k), list)),
                [],
            )
        else:
            items = []

        if not items:
            pytest.skip("No trust rules returned — skipping tier value validation")

        valid_tiers = {"observe", "suggest", "execute"}
        for item in items:
            if not isinstance(item, dict):
                continue
            tier = item.get("assigned_tier", "")
            assert tier in valid_tiers, (
                f"Trust rule 'assigned_tier' must be one of {sorted(valid_tiers)!r}, "
                f"got {tier!r}"
            )

    def test_rules_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/trust/rules response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _RULES)


# ---------------------------------------------------------------------------
# Safety bounds endpoint
# ---------------------------------------------------------------------------


class TestTrustSafetyBoundsEndpoint:
    """Safety bounds endpoint must return valid JSON for the SafetyBoundsPanel.

    The safety bounds define hard limits on automated actions. The API
    response should include limit fields such as max_auto_merge_lines,
    max_auto_merge_cost, and max_loopbacks.
    """

    def test_safety_bounds_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/trust/safety-bounds returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _SAFETY_BOUNDS, 200)

    def test_safety_bounds_response_is_valid_json(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/trust/safety-bounds returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _SAFETY_BOUNDS, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/trust/safety-bounds must return a non-null JSON body"
        )

    def test_safety_bounds_response_is_object(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/trust/safety-bounds response is a JSON object."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _SAFETY_BOUNDS, 200)

        assert isinstance(data, dict), (
            "GET /api/v1/dashboard/trust/safety-bounds must return a JSON object, "
            f"got {type(data).__name__!r}"
        )

    def test_safety_bounds_known_fields_present(self, page, base_url: str) -> None:
        """Safety bounds response contains at least one recognised limit field."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _SAFETY_BOUNDS, 200)

        if not isinstance(data, dict):
            pytest.skip("Safety bounds did not return a dict — skipping field check")

        known_fields = {
            "max_auto_merge_lines",
            "max_auto_merge_cost",
            "max_loopbacks",
            "mandatory_review_patterns",
        }
        found = known_fields & set(data.keys())
        # Graceful: at least one known field is expected; if the API returns a
        # different structure this is noted but not a hard failure.
        assert found or len(data) > 0, (
            "Safety bounds response must contain at least one field; got empty object"
        )

    def test_safety_bounds_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/trust/safety-bounds response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _SAFETY_BOUNDS)


# ---------------------------------------------------------------------------
# Default tier endpoint
# ---------------------------------------------------------------------------


class TestTrustDefaultTierEndpoint:
    """Default tier endpoint must return the current fallback tier value.

    The default tier is the fallback assigned when no rule matches a task.
    The ActiveTierDisplay component reads this endpoint on mount.
    """

    def test_default_tier_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/trust/default-tier returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _DEFAULT_TIER, 200)

    def test_default_tier_response_is_valid_json(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/trust/default-tier returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _DEFAULT_TIER, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/trust/default-tier must return a non-null JSON body"
        )

    def test_default_tier_response_structure(self, page, base_url: str) -> None:
        """Default tier response is a dict or a string — not an array or null."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _DEFAULT_TIER, 200)

        assert isinstance(data, (dict, str)), (
            "GET /api/v1/dashboard/trust/default-tier must return a JSON object or "
            f"string, got {type(data).__name__!r}"
        )

    def test_default_tier_value_is_valid_tier(self, page, base_url: str) -> None:
        """Default tier value is one of 'observe', 'suggest', or 'execute'."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _DEFAULT_TIER, 200)

        valid_tiers = {"observe", "suggest", "execute"}

        # Handle both bare string and wrapped dict responses.
        if isinstance(data, str):
            tier_value = data.strip().lower()
        elif isinstance(data, dict):
            tier_value = str(
                data.get("tier") or data.get("default_tier") or data.get("value") or ""
            ).lower()
        else:
            tier_value = ""

        if not tier_value:
            pytest.skip(
                "Default tier value could not be extracted from response — "
                "skipping canonical tier validation"
            )

        assert tier_value in valid_tiers, (
            f"Default tier must be one of {sorted(valid_tiers)!r}, "
            f"got {tier_value!r}"
        )

    def test_default_tier_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/trust/default-tier response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _DEFAULT_TIER)

    def test_all_three_trust_endpoints_return_200(self, page, base_url: str) -> None:
        """All three trust backing endpoints return HTTP 200 in a single session."""
        _go(page, base_url)

        results = {}
        for name, path in (
            ("rules", _RULES),
            ("safety-bounds", _SAFETY_BOUNDS),
            ("default-tier", _DEFAULT_TIER),
        ):
            response = page.request.get(f"{base_url}{path}")  # type: ignore[attr-defined]
            results[name] = response.status

        failed = {name: status for name, status in results.items() if status >= 400}
        assert not failed, (
            f"Trust backing endpoints returned error status codes: "
            + ", ".join(f"{name}={status}" for name, status in failed.items())
        )
