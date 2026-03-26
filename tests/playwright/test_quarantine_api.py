"""Epic 68.2 — Quarantine: API Endpoint Verification.

Validates that all backing endpoints for /admin/ui/quarantine return HTTP 200
with valid JSON schema.

Quarantine page backing endpoints:
  - GET /admin/quarantine          — List quarantined events with failure reasons
  - GET /admin/quarantine/{id}     — Quarantine event detail for a specific event
  - GET /healthz                   — Liveness probe (shared health gate)

These tests check *contract stability*, not visual presentation.
Style compliance is covered in test_quarantine_style.py (Epic 68.3).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
)

pytestmark = pytest.mark.playwright

# API routes relative to the base_url provided by the conftest fixture.
_QUARANTINE_LIST = "/admin/quarantine"
_HEALTHZ = "/healthz"


class TestQuarantineListEndpoint:
    """Quarantine list endpoint must return an array of quarantined event summaries.

    The Quarantine page is sourced from this endpoint; each item must carry
    the quarantine ID, failure reason, and event identity fields that operators
    rely on to review and replay held events.
    """

    def test_quarantine_list_returns_200(self, page, base_url: str) -> None:
        """GET /admin/quarantine returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/quarantine")
        assert_api_endpoint(page, "GET", _QUARANTINE_LIST, 200)

    def test_quarantine_list_returns_json_array(self, page, base_url: str) -> None:
        """GET /admin/quarantine returns a JSON array."""
        page.goto(f"{base_url}/admin/ui/quarantine")
        data = assert_api_endpoint(page, "GET", _QUARANTINE_LIST, 200)
        assert isinstance(data, list), (
            f"Expected JSON array from {_QUARANTINE_LIST}, got {type(data).__name__!r}"
        )

    def test_quarantine_list_items_have_quarantine_id(self, page, base_url: str) -> None:
        """Each quarantined event summary has a 'quarantine_id' or 'id' field."""
        page.goto(f"{base_url}/admin/ui/quarantine")
        data = assert_api_endpoint(page, "GET", _QUARANTINE_LIST, 200)
        assert isinstance(data, list), f"Expected JSON array from {_QUARANTINE_LIST}"
        if not data:
            pytest.skip("No quarantined events — schema check skipped (empty list is valid)")
        for item in data:
            has_id = "quarantine_id" in item or "id" in item
            assert has_id, (
                "Each quarantined event must contain a 'quarantine_id' or 'id' field"
            )

    def test_quarantine_list_items_have_reason(self, page, base_url: str) -> None:
        """Each quarantined event summary has a 'reason' or 'failure_reason' field."""
        page.goto(f"{base_url}/admin/ui/quarantine")
        data = assert_api_endpoint(page, "GET", _QUARANTINE_LIST, 200)
        assert isinstance(data, list), f"Expected JSON array from {_QUARANTINE_LIST}"
        if not data:
            pytest.skip("No quarantined events — reason check skipped")
        for item in data:
            has_reason = "reason" in item or "failure_reason" in item
            assert has_reason, (
                "Each quarantined event must contain a 'reason' or 'failure_reason' field"
            )

    def test_quarantine_list_items_have_event_identity(self, page, base_url: str) -> None:
        """Each quarantined event has an 'event_id', 'repo_id', or 'source' field."""
        page.goto(f"{base_url}/admin/ui/quarantine")
        data = assert_api_endpoint(page, "GET", _QUARANTINE_LIST, 200)
        assert isinstance(data, list), f"Expected JSON array from {_QUARANTINE_LIST}"
        if not data:
            pytest.skip("No quarantined events — event identity check skipped")
        for item in data:
            has_identity = (
                "event_id" in item
                or "repo_id" in item
                or "source" in item
                or "correlation_id" in item
            )
            assert has_identity, (
                "Each quarantined event must contain 'event_id', 'repo_id', "
                "'source', or 'correlation_id' field"
            )

    def test_quarantine_list_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/quarantine response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/quarantine")
        assert_api_no_error(page, _QUARANTINE_LIST)


class TestQuarantineDetailEndpoint:
    """Quarantine detail endpoint must return full event data for a given quarantine ID.

    The detail panel on the Quarantine page uses this endpoint to show
    the raw event payload, failure reason, and replay history for a selected
    quarantined event. When no quarantined events are registered this test class is skipped.
    """

    def _first_quarantine_id(self, page, base_url: str) -> str | None:
        """Return the quarantine_id/id of the first listed quarantined event, or None."""
        data = assert_api_endpoint(page, "GET", _QUARANTINE_LIST, 200)
        if not isinstance(data, list) or not data:
            return None
        item = data[0]
        return item.get("quarantine_id") or item.get("id")

    def test_quarantine_detail_returns_200(self, page, base_url: str) -> None:
        """GET /admin/quarantine/{id} returns HTTP 200 for a known event."""
        page.goto(f"{base_url}/admin/ui/quarantine")
        quarantine_id = self._first_quarantine_id(page, base_url)
        if quarantine_id is None:
            pytest.skip("No quarantined events — detail endpoint test skipped")

        detail_url = f"{_QUARANTINE_LIST}/{quarantine_id}"
        assert_api_endpoint(page, "GET", detail_url, 200)

    def test_quarantine_detail_has_required_fields(self, page, base_url: str) -> None:
        """GET /admin/quarantine/{id} response includes reason and event payload fields."""
        page.goto(f"{base_url}/admin/ui/quarantine")
        quarantine_id = self._first_quarantine_id(page, base_url)
        if quarantine_id is None:
            pytest.skip("No quarantined events — detail fields check skipped")

        detail_url = f"{_QUARANTINE_LIST}/{quarantine_id}"
        data = assert_api_endpoint(page, "GET", detail_url, 200)
        assert isinstance(data, dict), (
            f"Quarantine detail must be a JSON object, got {type(data).__name__!r}"
        )
        has_reason = "reason" in data or "failure_reason" in data
        assert has_reason, (
            "Quarantine detail must contain 'reason' or 'failure_reason' field"
        )

    def test_quarantine_detail_has_payload_field(self, page, base_url: str) -> None:
        """GET /admin/quarantine/{id} response includes 'payload' or 'event_payload' field."""
        page.goto(f"{base_url}/admin/ui/quarantine")
        quarantine_id = self._first_quarantine_id(page, base_url)
        if quarantine_id is None:
            pytest.skip("No quarantined events — payload field check skipped")

        detail_url = f"{_QUARANTINE_LIST}/{quarantine_id}"
        data = assert_api_endpoint(page, "GET", detail_url, 200)
        assert isinstance(data, dict), (
            f"Quarantine detail must be a JSON object, got {type(data).__name__!r}"
        )
        has_payload = "payload" in data or "event_payload" in data or "raw_payload" in data
        assert has_payload, (
            "Quarantine detail must contain a 'payload', 'event_payload', or 'raw_payload' field"
        )

    def test_quarantine_detail_unknown_id_returns_404(self, page, base_url: str) -> None:
        """GET /admin/quarantine/{unknown-id} returns HTTP 404 for an unknown event."""
        page.goto(f"{base_url}/admin/ui/quarantine")
        unknown_url = f"{_QUARANTINE_LIST}/00000000-0000-0000-0000-000000000000"
        assert_api_endpoint(page, "GET", unknown_url, 404)

    def test_quarantine_detail_no_error_on_known_id(self, page, base_url: str) -> None:
        """GET /admin/quarantine/{id} response has no error payload for a known event."""
        page.goto(f"{base_url}/admin/ui/quarantine")
        quarantine_id = self._first_quarantine_id(page, base_url)
        if quarantine_id is None:
            pytest.skip("No quarantined events — error-body check skipped")

        detail_url = f"{_QUARANTINE_LIST}/{quarantine_id}"
        assert_api_no_error(page, detail_url)


class TestQuarantineLivenessEndpoint:
    """Global liveness probe must be reachable when browsing the Quarantine page.

    The Quarantine page shares the same health gate as all other admin pages;
    this test ensures no regression in global liveness after quarantine routes are added.
    """

    def test_healthz_returns_200_from_quarantine_page(self, page, base_url: str) -> None:
        """GET /healthz returns HTTP 200 when quarantine page is loaded."""
        page.goto(f"{base_url}/admin/ui/quarantine")
        assert_api_endpoint(page, "GET", _HEALTHZ, 200)

    def test_healthz_has_status_field_from_quarantine_page(self, page, base_url: str) -> None:
        """GET /healthz JSON body contains 'status' field (quarantine page context)."""
        page.goto(f"{base_url}/admin/ui/quarantine")
        data = assert_api_endpoint(page, "GET", _HEALTHZ, 200, json_keys=["status"])
        assert data is not None, "GET /healthz must return a non-null JSON body"

    def test_healthz_no_error_body_from_quarantine_page(self, page, base_url: str) -> None:
        """GET /healthz response contains no error payload (quarantine page context)."""
        page.goto(f"{base_url}/admin/ui/quarantine")
        assert_api_no_error(page, _HEALTHZ)
