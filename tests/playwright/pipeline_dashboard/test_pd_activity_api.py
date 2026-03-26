"""Story 76.9 — Pipeline Dashboard: Activity Log API Endpoint Verification.

Validates that the backing API endpoints for /dashboard/?tab=activity return
HTTP 200 with valid JSON schema.

Activity backing endpoints:
  - GET /api/v1/dashboard/steering/audit?limit=50&offset=0
                                  — Paginated audit entries for the activity log
  - GET /api/v1/dashboard/steering/audit?limit=50&offset=0&action=pause
                                  — Filtered by action type

These tests check *contract stability*, not visual presentation.
Style compliance is in test_pd_activity_style.py.
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
    assert_api_returns_data,
)
from tests.playwright.pipeline_dashboard.conftest import dashboard_navigate

pytestmark = pytest.mark.playwright

_AUDIT_BASE = "/api/v1/dashboard/steering/audit"
_AUDIT_DEFAULT = "/api/v1/dashboard/steering/audit?limit=50&offset=0"
_AUDIT_PAGE2 = "/api/v1/dashboard/steering/audit?limit=50&offset=50"
_AUDIT_FILTERED = "/api/v1/dashboard/steering/audit?limit=50&offset=0&action=pause"


def _go(page: object, base_url: str) -> None:
    """Navigate to the activity tab to warm session cookies before API calls."""
    dashboard_navigate(page, base_url, "activity")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Primary audit endpoint — default pagination
# ---------------------------------------------------------------------------


class TestActivityAuditEndpoint:
    """Audit endpoint must return a valid JSON list for the activity log table.

    The SteeringActivityLog component fetches from this endpoint with
    limit=50 and offset=0 on mount. An empty list is valid — the empty
    state handles the zero-entry case gracefully.
    """

    def test_audit_endpoint_returns_200(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/steering/audit?limit=50&offset=0 returns HTTP 200."""
        _go(page, base_url)
        assert_api_endpoint(page, "GET", _AUDIT_DEFAULT, 200)

    def test_audit_response_is_valid_json(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/steering/audit returns a parseable JSON body."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _AUDIT_DEFAULT, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/steering/audit must return a non-null JSON body"
        )

    def test_audit_response_contains_list(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/steering/audit response is a JSON list or wraps one."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _AUDIT_DEFAULT, 200)

        # Accept either a bare list or an object wrapping a list under common keys.
        is_list = isinstance(data, list)
        is_wrapped = isinstance(data, dict) and any(
            isinstance(data.get(k), list)
            for k in ("entries", "items", "data", "results", "audit")
        )
        assert is_list or is_wrapped, (
            "GET /api/v1/dashboard/steering/audit must return a JSON list or an object "
            "containing an 'entries'/'items'/'data'/'results'/'audit' list"
        )

    def test_audit_entry_schema_when_populated(self, page, base_url: str) -> None:
        """Each audit entry contains at minimum 'id', 'action', and 'actor' fields."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _AUDIT_DEFAULT, 200)

        # Normalise to a list.
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = next(
                (
                    data[k]
                    for k in ("entries", "items", "data", "results", "audit")
                    if isinstance(data.get(k), list)
                ),
                [],
            )
        else:
            items = []

        if not items:
            pytest.skip("No audit entries returned — empty list is acceptable")

        first = items[0]
        assert isinstance(first, dict), (
            "Each audit entry in /api/v1/dashboard/steering/audit must be a JSON object"
        )
        assert "id" in first, (
            "Audit entry must contain an 'id' field"
        )

    def test_audit_entry_has_action_field(self, page, base_url: str) -> None:
        """Each audit entry contains an 'action' field identifying the steering type."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _AUDIT_DEFAULT, 200)

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = next(
                (
                    data[k]
                    for k in ("entries", "items", "data", "results", "audit")
                    if isinstance(data.get(k), list)
                ),
                [],
            )
        else:
            items = []

        if not items:
            pytest.skip("No audit entries returned — empty list is acceptable")

        first = items[0]
        assert "action" in first, (
            "Audit entry must contain an 'action' field "
            "(pause, resume, abort, redirect, retry, trust_tier_assigned, trust_tier_overridden)"
        )

    def test_audit_entry_has_timestamp_field(self, page, base_url: str) -> None:
        """Each audit entry contains a 'timestamp' field for the time column."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _AUDIT_DEFAULT, 200)

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = next(
                (
                    data[k]
                    for k in ("entries", "items", "data", "results", "audit")
                    if isinstance(data.get(k), list)
                ),
                [],
            )
        else:
            items = []

        if not items:
            pytest.skip("No audit entries returned — empty list is acceptable")

        first = items[0]
        assert "timestamp" in first, (
            "Audit entry must contain a 'timestamp' field "
            "so the Time column can display when the action occurred"
        )

    def test_audit_entry_has_actor_field(self, page, base_url: str) -> None:
        """Each audit entry contains an 'actor' field for the Actor column."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _AUDIT_DEFAULT, 200)

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = next(
                (
                    data[k]
                    for k in ("entries", "items", "data", "results", "audit")
                    if isinstance(data.get(k), list)
                ),
                [],
            )
        else:
            items = []

        if not items:
            pytest.skip("No audit entries returned — empty list is acceptable")

        first = items[0]
        assert "actor" in first, (
            "Audit entry must contain an 'actor' field "
            "showing who initiated the steering action"
        )

    def test_audit_no_error_body(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/steering/audit response contains no error payload."""
        _go(page, base_url)
        assert_api_no_error(page, _AUDIT_DEFAULT)


# ---------------------------------------------------------------------------
# Pagination — limit/offset query params
# ---------------------------------------------------------------------------


class TestActivityAuditPagination:
    """Audit endpoint must honour limit and offset pagination parameters.

    The SteeringActivityLog component sends limit=50, offset=n*50 for each
    page.  The endpoint must accept these without returning a 4xx error.
    """

    def test_limit_param_accepted(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/steering/audit?limit=50 accepts the limit param."""
        _go(page, base_url)

        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_AUDIT_DEFAULT}"
        )
        assert response.status < 400, (
            f"GET {_AUDIT_DEFAULT} returned {response.status} — "
            "expected 2xx; limit param must be accepted"
        )

    def test_offset_param_accepted(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/steering/audit?offset=50 accepts the offset param."""
        _go(page, base_url)

        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_AUDIT_PAGE2}"
        )
        assert response.status < 400, (
            f"GET {_AUDIT_PAGE2} returned {response.status} — "
            "expected 2xx; offset param must be accepted"
        )

    def test_offset_zero_and_nonzero_both_return_200(
        self, page, base_url: str
    ) -> None:
        """Audit endpoint returns 200 for both offset=0 and offset=50."""
        _go(page, base_url)

        for url in (_AUDIT_DEFAULT, _AUDIT_PAGE2):
            response = page.request.get(f"{base_url}{url}")  # type: ignore[attr-defined]
            assert response.status < 400, (
                f"GET {url} returned {response.status} — "
                f"expected 2xx for pagination offset"
            )

    def test_page2_returns_list(self, page, base_url: str) -> None:
        """Page 2 (offset=50) returns a list (possibly empty)."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _AUDIT_PAGE2, 200)

        is_list = isinstance(data, list)
        is_wrapped = isinstance(data, dict) and any(
            isinstance(data.get(k), list)
            for k in ("entries", "items", "data", "results", "audit")
        )
        assert is_list or is_wrapped, (
            f"GET {_AUDIT_PAGE2} must return a JSON list or wrapped list "
            "— empty list is valid when there are fewer than 50 entries"
        )


# ---------------------------------------------------------------------------
# Action filter query param
# ---------------------------------------------------------------------------


class TestActivityAuditFilter:
    """Audit endpoint must honour the action query param for filtering.

    The SteeringActivityLog FilterBar sends ?action=<type> when the operator
    selects a specific action type from the dropdown.
    """

    KNOWN_ACTIONS = [
        "pause",
        "resume",
        "abort",
        "redirect",
        "retry",
        "trust_tier_assigned",
        "trust_tier_overridden",
    ]

    def test_action_filter_accepted(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/steering/audit?action=pause accepts action param."""
        _go(page, base_url)

        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_AUDIT_FILTERED}"
        )
        assert response.status < 400, (
            f"GET {_AUDIT_FILTERED} returned {response.status} — "
            "expected 2xx; action filter param must be accepted"
        )

    def test_action_filter_returns_valid_json(self, page, base_url: str) -> None:
        """Filtered audit endpoint returns parseable JSON."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _AUDIT_FILTERED, 200)
        assert data is not None, (
            f"GET {_AUDIT_FILTERED} must return a non-null JSON body"
        )

    def test_action_filter_returns_list(self, page, base_url: str) -> None:
        """Filtered audit endpoint returns a list (possibly empty if no pause actions)."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _AUDIT_FILTERED, 200)

        is_list = isinstance(data, list)
        is_wrapped = isinstance(data, dict) and any(
            isinstance(data.get(k), list)
            for k in ("entries", "items", "data", "results", "audit")
        )
        assert is_list or is_wrapped, (
            f"GET {_AUDIT_FILTERED} must return a JSON list or wrapped list"
        )

    def test_filtered_entries_match_action_when_populated(
        self, page, base_url: str
    ) -> None:
        """When action=pause is set, all returned entries must have action='pause'."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _AUDIT_FILTERED, 200)

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = next(
                (
                    data[k]
                    for k in ("entries", "items", "data", "results", "audit")
                    if isinstance(data.get(k), list)
                ),
                [],
            )
        else:
            items = []

        if not items:
            pytest.skip(
                "No 'pause' audit entries returned — empty list is acceptable"
            )

        non_pause = [e for e in items if e.get("action") != "pause"]
        assert not non_pause, (
            f"Filtered endpoint ?action=pause returned {len(non_pause)} entries "
            "with action != 'pause' — filter must be applied server-side"
        )


# ---------------------------------------------------------------------------
# Base URL (no query params)
# ---------------------------------------------------------------------------


class TestActivityAuditBaseUrl:
    """Audit endpoint base URL (no params) must also return a usable response.

    Some HTTP clients call the base URL; the endpoint should handle the
    absence of limit/offset gracefully.
    """

    def test_base_audit_url_not_404(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/steering/audit (no params) returns non-4xx."""
        _go(page, base_url)

        response = page.request.get(  # type: ignore[attr-defined]
            f"{base_url}{_AUDIT_BASE}"
        )
        assert response.status < 400, (
            f"GET {_AUDIT_BASE} returned {response.status} — "
            "endpoint must respond to requests without query params"
        )

    def test_base_audit_url_returns_json(self, page, base_url: str) -> None:
        """GET /api/v1/dashboard/steering/audit (no params) returns JSON."""
        _go(page, base_url)
        data = assert_api_endpoint(page, "GET", _AUDIT_BASE, 200)
        assert data is not None, (
            "GET /api/v1/dashboard/steering/audit must return a non-null JSON body "
            "even without query parameters"
        )
