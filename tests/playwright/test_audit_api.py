"""Epic 62.2 — Audit Log: API Endpoint Verification.

Validates that all backing endpoints for /admin/ui/audit return HTTP 200
with valid JSON schema.

Audit Log backing endpoints:
  - GET /admin/audit           — paginated list of audit events (AuditListResponse)
  - GET /admin/audit/{id}      — single event detail (AuditEventDetail)

These tests check *contract stability*, not visual presentation.
Style compliance is covered in test_audit_style.py (Epic 62.3).
"""

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_no_error,
    assert_api_returns_data,
)

pytestmark = pytest.mark.playwright

_AUDIT = "/admin/audit"


class TestAuditListEndpoint:
    """Audit list endpoint must return a valid paginated JSON collection.

    The /admin/ui/audit page renders its event table from this endpoint; any
    schema regression here breaks the operator's primary audit surface.
    """

    def test_audit_list_returns_200(self, page, base_url: str) -> None:
        """GET /admin/audit returns HTTP 200."""
        page.goto(f"{base_url}/admin/ui/audit")
        assert_api_endpoint(page, "GET", _AUDIT, 200)

    def test_audit_list_response_is_valid_json(self, page, base_url: str) -> None:
        """GET /admin/audit returns a non-null JSON body."""
        page.goto(f"{base_url}/admin/ui/audit")
        data = assert_api_endpoint(page, "GET", _AUDIT, 200)
        assert data is not None, "GET /admin/audit must return a non-null JSON body"

    def test_audit_list_contains_events_field(self, page, base_url: str) -> None:
        """GET /admin/audit response contains an 'events' list field."""
        page.goto(f"{base_url}/admin/ui/audit")
        assert_api_returns_data(page, _AUDIT, list_key="events", allow_empty=True)

    def test_audit_list_contains_total_field(self, page, base_url: str) -> None:
        """GET /admin/audit response contains a numeric 'total' field."""
        page.goto(f"{base_url}/admin/ui/audit")
        data = assert_api_endpoint(page, "GET", _AUDIT, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/audit"
        assert "total" in data, "GET /admin/audit must contain a 'total' field"
        assert isinstance(data["total"], int), (
            f"Field 'total' must be an integer, got {type(data['total']).__name__!r}"
        )

    def test_audit_list_contains_pagination_field(self, page, base_url: str) -> None:
        """GET /admin/audit response contains pagination metadata."""
        page.goto(f"{base_url}/admin/ui/audit")
        data = assert_api_endpoint(page, "GET", _AUDIT, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/audit"

        # Accept either a 'pagination' object or separate page/page_size fields
        has_pagination_obj = "pagination" in data
        has_page_fields = "page" in data or "page_size" in data or "limit" in data
        assert has_pagination_obj or has_page_fields, (
            "GET /admin/audit must contain pagination metadata "
            "('pagination' object or 'page'/'page_size'/'limit' fields)"
        )

    def test_audit_total_is_non_negative(self, page, base_url: str) -> None:
        """GET /admin/audit 'total' field is a non-negative integer."""
        page.goto(f"{base_url}/admin/ui/audit")
        data = assert_api_endpoint(page, "GET", _AUDIT, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/audit"
        total = data.get("total", -1)
        assert total >= 0, f"GET /admin/audit 'total' must be >= 0, got {total}"

    def test_audit_list_item_schema_when_populated(self, page, base_url: str) -> None:
        """Each item in the events list contains required fields."""
        page.goto(f"{base_url}/admin/ui/audit")
        data = assert_api_endpoint(page, "GET", _AUDIT, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/audit"
        events = data.get("events", [])

        if not events:
            pytest.skip("No audit events registered — empty list is acceptable for 62.2")

        first = events[0]
        assert isinstance(first, dict), "Each item in events list must be a JSON object"

        for field in ("event_id", "timestamp", "actor", "action", "target"):
            assert field in first, (
                f"Audit event list item must contain '{field}' field"
            )

    def test_audit_list_no_error_body(self, page, base_url: str) -> None:
        """GET /admin/audit response contains no error payload."""
        page.goto(f"{base_url}/admin/ui/audit")
        assert_api_no_error(page, _AUDIT)


class TestAuditDetailEndpoint:
    """Audit event detail endpoint must return the full AuditEventDetail for a given ID.

    The row-expansion panel on /admin/ui/audit populates from this endpoint.
    Without it the operator cannot view full event metadata or context.
    """

    def test_audit_detail_returns_200_when_event_exists(
        self, page, base_url: str
    ) -> None:
        """GET /admin/audit/{id} returns HTTP 200 for a valid event ID."""
        page.goto(f"{base_url}/admin/ui/audit")
        data = assert_api_endpoint(page, "GET", _AUDIT, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/audit"
        events = data.get("events", [])

        if not events:
            pytest.skip(
                "No audit events registered — detail endpoint test requires at least one event"
            )

        event_id = events[0]["event_id"]
        assert_api_endpoint(page, "GET", f"{_AUDIT}/{event_id}", 200)

    def test_audit_detail_schema_when_populated(self, page, base_url: str) -> None:
        """GET /admin/audit/{id} response contains all AuditEventDetail fields."""
        page.goto(f"{base_url}/admin/ui/audit")
        data = assert_api_endpoint(page, "GET", _AUDIT, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/audit"
        events = data.get("events", [])

        if not events:
            pytest.skip(
                "No audit events registered — detail schema test requires at least one event"
            )

        event_id = events[0]["event_id"]
        detail = assert_api_endpoint(page, "GET", f"{_AUDIT}/{event_id}", 200)

        assert isinstance(detail, dict), (
            f"GET /admin/audit/{{id}} must return a JSON object, got {type(detail)!r}"
        )

        expected_fields = ("event_id", "timestamp", "actor", "action", "target")
        for field in expected_fields:
            assert field in detail, (
                f"AuditEventDetail must contain '{field}' field"
            )

    def test_audit_detail_returns_404_for_unknown_id(self, page, base_url: str) -> None:
        """GET /admin/audit/{id} returns 404 for a non-existent event ID."""
        page.goto(f"{base_url}/admin/ui/audit")
        unknown_id = "nonexistent-audit-event-00000000"
        assert_api_endpoint(page, "GET", f"{_AUDIT}/{unknown_id}", 404)

    def test_audit_detail_no_error_body_for_valid_id(self, page, base_url: str) -> None:
        """GET /admin/audit/{id} for a valid ID contains no error payload."""
        page.goto(f"{base_url}/admin/ui/audit")
        data = assert_api_endpoint(page, "GET", _AUDIT, 200)
        assert isinstance(data, dict), "Expected JSON object from GET /admin/audit"
        events = data.get("events", [])

        if not events:
            pytest.skip(
                "No audit events registered — error-body test requires at least one event"
            )

        event_id = events[0]["event_id"]
        assert_api_no_error(page, f"{_AUDIT}/{event_id}")
