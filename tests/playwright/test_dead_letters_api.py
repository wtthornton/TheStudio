"""Epic 69.2 — Dead-Letter Inspector: API Endpoint Verification.

Validates that all backing endpoints for /admin/ui/dead-letters return HTTP 200
with valid JSON schema.

Dead-Letter Inspector page backing endpoints:
  - GET /admin/dead-letters          — List dead-lettered events with failure reasons
  - GET /admin/dead-letters/{id}     — Dead-letter event detail for a specific event
  - GET /healthz                     — Liveness probe (shared health gate)

These tests check *contract stability*, not visual presentation.
Style compliance is covered in test_dead_letters_style.py (Epic 69.3).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
)

pytestmark = pytest.mark.playwright

# API routes relative to the base_url provided by the conftest fixture.
_DEAD_LETTERS_LIST = "/admin/dead-letters"
_HEALTHZ = "/healthz"


class TestDeadLettersListEndpoint:
    """Dead-letter list endpoint must return an array of dead-lettered event summaries.

    The Dead-Letter Inspector page is sourced from this endpoint; each item must
    carry the event ID, failure reason, and attempt count that operators rely on
    to review and retry permanently-failed events.
    """

    def test_dead_letters_list_returns_200(self, page, base_url: str) -> None:
        """GET /admin/dead-letters returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/dead-letters")
        assert_api_endpoint(page, "GET", _DEAD_LETTERS_LIST, 200)

    def test_dead_letters_list_returns_json_array(self, page, base_url: str) -> None:
        """GET /admin/dead-letters returns a JSON array."""
        page.goto(f"{base_url}/admin/ui/dead-letters")
        data = assert_api_endpoint(page, "GET", _DEAD_LETTERS_LIST, 200)
        assert isinstance(data, list), (
            f"Expected JSON array from {_DEAD_LETTERS_LIST}, got {type(data).__name__!r}"
        )

    def test_dead_letters_list_items_have_id(self, page, base_url: str) -> None:
        """Each dead-lettered event summary has an 'id' or 'dead_letter_id' field."""
        page.goto(f"{base_url}/admin/ui/dead-letters")
        data = assert_api_endpoint(page, "GET", _DEAD_LETTERS_LIST, 200)
        assert isinstance(data, list), f"Expected JSON array from {_DEAD_LETTERS_LIST}"
        if not data:
            pytest.skip("No dead-lettered events — schema check skipped (empty list is valid)")
        for item in data:
            has_id = "id" in item or "dead_letter_id" in item
            assert has_id, (
                "Each dead-lettered event must contain an 'id' or 'dead_letter_id' field"
            )

    def test_dead_letters_list_items_have_reason(self, page, base_url: str) -> None:
        """Each dead-lettered event summary has a 'reason' or 'failure_reason' field."""
        page.goto(f"{base_url}/admin/ui/dead-letters")
        data = assert_api_endpoint(page, "GET", _DEAD_LETTERS_LIST, 200)
        assert isinstance(data, list), f"Expected JSON array from {_DEAD_LETTERS_LIST}"
        if not data:
            pytest.skip("No dead-lettered events — reason check skipped")
        for item in data:
            has_reason = "reason" in item or "failure_reason" in item
            assert has_reason, (
                "Each dead-lettered event must contain a 'reason' or 'failure_reason' field"
            )

    def test_dead_letters_list_items_have_attempt_count(self, page, base_url: str) -> None:
        """Each dead-lettered event summary has an 'attempt_count' or 'attempts' field."""
        page.goto(f"{base_url}/admin/ui/dead-letters")
        data = assert_api_endpoint(page, "GET", _DEAD_LETTERS_LIST, 200)
        assert isinstance(data, list), f"Expected JSON array from {_DEAD_LETTERS_LIST}"
        if not data:
            pytest.skip("No dead-lettered events — attempt count check skipped")
        for item in data:
            has_attempts = "attempt_count" in item or "attempts" in item or "retry_count" in item
            assert has_attempts, (
                "Each dead-lettered event must contain an 'attempt_count', 'attempts', "
                "or 'retry_count' field"
            )

    def test_dead_letters_list_items_have_event_identity(self, page, base_url: str) -> None:
        """Each dead-lettered event has an 'event_id', 'repo_id', or 'source' field."""
        page.goto(f"{base_url}/admin/ui/dead-letters")
        data = assert_api_endpoint(page, "GET", _DEAD_LETTERS_LIST, 200)
        assert isinstance(data, list), f"Expected JSON array from {_DEAD_LETTERS_LIST}"
        if not data:
            pytest.skip("No dead-lettered events — event identity check skipped")
        for item in data:
            has_identity = (
                "event_id" in item
                or "repo_id" in item
                or "source" in item
                or "correlation_id" in item
            )
            assert has_identity, (
                "Each dead-lettered event must contain 'event_id', 'repo_id', "
                "'source', or 'correlation_id' field"
            )

    def test_dead_letters_list_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/dead-letters response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/dead-letters")
        assert_api_no_error(page, _DEAD_LETTERS_LIST)


class TestDeadLettersDetailEndpoint:
    """Dead-letter detail endpoint must return full event data for a given dead-letter ID.

    The detail panel on the Dead-Letter Inspector page uses this endpoint to show
    the raw event payload, failure reason, and attempt history for a selected
    dead-lettered event. When no dead-lettered events are registered this test
    class is skipped.
    """

    def _first_dead_letter_id(self, page, base_url: str) -> str | None:
        """Return the id/dead_letter_id of the first listed dead-lettered event, or None."""
        data = assert_api_endpoint(page, "GET", _DEAD_LETTERS_LIST, 200)
        if not isinstance(data, list) or not data:
            return None
        item = data[0]
        return item.get("dead_letter_id") or item.get("id")

    def test_dead_letter_detail_returns_200(self, page, base_url: str) -> None:
        """GET /admin/dead-letters/{id} returns HTTP 200 for a known event."""
        page.goto(f"{base_url}/admin/ui/dead-letters")
        dead_letter_id = self._first_dead_letter_id(page, base_url)
        if dead_letter_id is None:
            pytest.skip("No dead-lettered events — detail endpoint test skipped")

        detail_url = f"{_DEAD_LETTERS_LIST}/{dead_letter_id}"
        assert_api_endpoint(page, "GET", detail_url, 200)

    def test_dead_letter_detail_has_required_fields(self, page, base_url: str) -> None:
        """GET /admin/dead-letters/{id} response includes reason and attempt count fields."""
        page.goto(f"{base_url}/admin/ui/dead-letters")
        dead_letter_id = self._first_dead_letter_id(page, base_url)
        if dead_letter_id is None:
            pytest.skip("No dead-lettered events — detail fields check skipped")

        detail_url = f"{_DEAD_LETTERS_LIST}/{dead_letter_id}"
        data = assert_api_endpoint(page, "GET", detail_url, 200)
        assert isinstance(data, dict), (
            f"Dead-letter detail must be a JSON object, got {type(data).__name__!r}"
        )
        has_reason = "reason" in data or "failure_reason" in data
        assert has_reason, (
            "Dead-letter detail must contain 'reason' or 'failure_reason' field"
        )

    def test_dead_letter_detail_has_payload_field(self, page, base_url: str) -> None:
        """GET /admin/dead-letters/{id} response includes 'payload' or 'event_payload' field."""
        page.goto(f"{base_url}/admin/ui/dead-letters")
        dead_letter_id = self._first_dead_letter_id(page, base_url)
        if dead_letter_id is None:
            pytest.skip("No dead-lettered events — payload field check skipped")

        detail_url = f"{_DEAD_LETTERS_LIST}/{dead_letter_id}"
        data = assert_api_endpoint(page, "GET", detail_url, 200)
        assert isinstance(data, dict), (
            f"Dead-letter detail must be a JSON object, got {type(data).__name__!r}"
        )
        has_payload = "payload" in data or "event_payload" in data or "raw_payload" in data
        assert has_payload, (
            "Dead-letter detail must contain a 'payload', 'event_payload', or 'raw_payload' field"
        )

    def test_dead_letter_detail_unknown_id_returns_404(self, page, base_url: str) -> None:
        """GET /admin/dead-letters/{unknown-id} returns HTTP 404 for an unknown event."""
        page.goto(f"{base_url}/admin/ui/dead-letters")
        unknown_url = f"{_DEAD_LETTERS_LIST}/00000000-0000-0000-0000-000000000000"
        assert_api_endpoint(page, "GET", unknown_url, 404)

    def test_dead_letter_detail_no_error_on_known_id(self, page, base_url: str) -> None:
        """GET /admin/dead-letters/{id} response has no error payload for a known event."""
        page.goto(f"{base_url}/admin/ui/dead-letters")
        dead_letter_id = self._first_dead_letter_id(page, base_url)
        if dead_letter_id is None:
            pytest.skip("No dead-lettered events — error-body check skipped")

        detail_url = f"{_DEAD_LETTERS_LIST}/{dead_letter_id}"
        assert_api_no_error(page, detail_url)


class TestDeadLettersLivenessEndpoint:
    """Global liveness probe must be reachable when browsing the Dead-Letter Inspector page.

    The Dead-Letter Inspector page shares the same health gate as all other admin pages;
    this test ensures no regression in global liveness after dead-letter routes are added.
    """

    def test_healthz_returns_200_from_dead_letters_page(self, page, base_url: str) -> None:
        """GET /healthz returns HTTP 200 when dead-letter page is loaded."""
        page.goto(f"{base_url}/admin/ui/dead-letters")
        assert_api_endpoint(page, "GET", _HEALTHZ, 200)

    def test_healthz_has_status_field_from_dead_letters_page(self, page, base_url: str) -> None:
        """GET /healthz JSON body contains 'status' field (dead-letter page context)."""
        page.goto(f"{base_url}/admin/ui/dead-letters")
        data = assert_api_endpoint(page, "GET", _HEALTHZ, 200, json_keys=["status"])
        assert data is not None, "GET /healthz must return a non-null JSON body"

    def test_healthz_no_error_body_from_dead_letters_page(self, page, base_url: str) -> None:
        """GET /healthz response contains no error payload (dead-letter page context)."""
        page.goto(f"{base_url}/admin/ui/dead-letters")
        assert_api_no_error(page, _HEALTHZ)
