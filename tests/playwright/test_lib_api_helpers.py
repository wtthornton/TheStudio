"""Unit tests for api_helpers.py (Epic 58, Story 58.4).

Tests use ``unittest.mock.MagicMock`` to simulate Playwright ``Page`` /
``APIRequestContext`` objects so they run without a live server — matching the
pattern from the 58.1–58.3 test suites.

Each helper is tested with:
- A *passing* scenario (correct status, correct JSON shape).
- A *failing* scenario (wrong status, missing keys, error body).
- Edge cases (non-JSON body, nested keys, empty lists, auth headers).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from tests.playwright.lib.api_helpers import (
    assert_api_endpoint,
    assert_api_fields,
    assert_api_no_error,
    assert_api_returns_data,
    build_auth_headers,
)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_response(
    status: int,
    body: dict | list | None = None,
    text: str | None = None,
) -> MagicMock:
    """Return a MagicMock that behaves like a Playwright APIResponse."""
    resp = MagicMock()
    resp.status = status

    if body is not None:
        resp.json.return_value = body
        resp.text.return_value = json.dumps(body)
    elif text is not None:
        resp.json.side_effect = ValueError("not JSON")
        resp.text.return_value = text
    else:
        resp.json.return_value = {}
        resp.text.return_value = "{}"

    return resp


def _make_page(method: str = "GET", response: MagicMock | None = None) -> MagicMock:
    """Return a MagicMock page with a request context that returns ``response``."""
    if response is None:
        response = _make_response(200)

    request_ctx = MagicMock()
    # Playwright APIRequestContext methods: get, post, put, patch, delete, head, options
    for m in ("get", "post", "put", "patch", "delete", "head", "options"):
        getattr(request_ctx, m).return_value = response

    page = MagicMock()
    page.request = request_ctx
    return page


# ---------------------------------------------------------------------------
# assert_api_endpoint
# ---------------------------------------------------------------------------


class TestAssertApiEndpoint:
    def test_passing_status_no_keys(self) -> None:
        resp = _make_response(200, {"status": "ok"})
        page = _make_page(response=resp)
        result = assert_api_endpoint(page, "GET", "/healthz", 200)
        assert result == {"status": "ok"}

    def test_passing_with_json_keys(self) -> None:
        resp = _make_response(200, {"status": "ok", "version": "1.0"})
        page = _make_page(response=resp)
        result = assert_api_endpoint(
            page, "GET", "/healthz", 200, json_keys=["status", "version"]
        )
        assert isinstance(result, dict)
        assert result["status"] == "ok"

    def test_wrong_status_raises(self) -> None:
        resp = _make_response(404, {"error": "not found"})
        page = _make_page(response=resp)
        with pytest.raises(AssertionError, match="expected status 200, got 404"):
            assert_api_endpoint(page, "GET", "/missing", 200)

    def test_missing_json_key_raises(self) -> None:
        resp = _make_response(200, {"data": []})
        page = _make_page(response=resp)
        with pytest.raises(AssertionError, match="missing expected JSON keys"):
            assert_api_endpoint(page, "GET", "/api/data", 200, json_keys=["status"])

    def test_non_json_body_with_json_keys_raises(self) -> None:
        resp = _make_response(200, text="OK")
        page = _make_page(response=resp)
        with pytest.raises(AssertionError, match="expected JSON object"):
            assert_api_endpoint(page, "GET", "/text-endpoint", 200, json_keys=["status"])

    def test_post_method(self) -> None:
        resp = _make_response(201, {"id": "abc"})
        page = _make_page(response=resp)
        result = assert_api_endpoint(
            page, "POST", "/api/v1/tasks", 201, body={"repo": "org/repo"}
        )
        assert result == {"id": "abc"}

    def test_extra_headers_forwarded(self) -> None:
        """Verify headers dict is passed through to the request context."""
        resp = _make_response(200, {"status": "ok"})
        page = _make_page(response=resp)
        result = assert_api_endpoint(
            page,
            "GET",
            "/admin/health",
            200,
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        # Verify .get() was called on the request context
        page.request.get.assert_called_once()
        call_kwargs = page.request.get.call_args[1]
        assert "headers" in call_kwargs
        assert call_kwargs["headers"]["Authorization"] == "Basic dXNlcjpwYXNz"
        assert result == {"status": "ok"}

    def test_invalid_method_raises(self) -> None:
        resp = _make_response(200)
        page = _make_page(response=resp)
        with pytest.raises(ValueError, match="Unsupported HTTP method"):
            assert_api_endpoint(page, "BREW", "/healthz", 200)

    def test_error_message_includes_path(self) -> None:
        resp = _make_response(500, {"error": "server error"})
        page = _make_page(response=resp)
        with pytest.raises(AssertionError, match="/api/v1/tasks"):
            assert_api_endpoint(page, "GET", "/api/v1/tasks", 200)


# ---------------------------------------------------------------------------
# assert_api_returns_data
# ---------------------------------------------------------------------------


class TestAssertApiReturnsData:
    def test_list_response_no_key(self) -> None:
        resp = _make_response(200, [{"id": 1}, {"id": 2}])
        page = _make_page(response=resp)
        result = assert_api_returns_data(page, "/api/items")
        assert result == [{"id": 1}, {"id": 2}]

    def test_list_under_key(self) -> None:
        resp = _make_response(200, {"repos": [{"name": "foo"}, {"name": "bar"}], "total": 2})
        page = _make_page(response=resp)
        result = assert_api_returns_data(page, "/api/v1/repos", list_key="repos")
        assert len(result) == 2  # type: ignore[arg-type]

    def test_empty_list_allowed_by_default(self) -> None:
        resp = _make_response(200, {"repos": [], "total": 0})
        page = _make_page(response=resp)
        result = assert_api_returns_data(page, "/api/v1/repos", list_key="repos")
        assert result == []

    def test_empty_list_raises_when_not_allowed(self) -> None:
        resp = _make_response(200, {"repos": []})
        page = _make_page(response=resp)
        with pytest.raises(AssertionError, match="expected non-empty list"):
            assert_api_returns_data(page, "/api/v1/repos", list_key="repos", allow_empty=False)

    def test_4xx_status_raises(self) -> None:
        resp = _make_response(403, {"error": "Forbidden"})
        page = _make_page(response=resp)
        with pytest.raises(AssertionError, match="expected 2xx status, got 403"):
            assert_api_returns_data(page, "/api/v1/repos")

    def test_missing_list_key_raises(self) -> None:
        resp = _make_response(200, {"data": []})
        page = _make_page(response=resp)
        with pytest.raises(AssertionError, match="list key .* not found"):
            assert_api_returns_data(page, "/api/items", list_key="items")

    def test_non_list_under_key_raises(self) -> None:
        resp = _make_response(200, {"repos": {"id": 1}})
        page = _make_page(response=resp)
        with pytest.raises(AssertionError, match="expected .* to be a list"):
            assert_api_returns_data(page, "/api/v1/repos", list_key="repos")

    def test_non_json_body_raises(self) -> None:
        resp = _make_response(200, text="not json")
        page = _make_page(response=resp)
        with pytest.raises(AssertionError, match="not valid JSON"):
            assert_api_returns_data(page, "/api/items")


# ---------------------------------------------------------------------------
# assert_api_fields
# ---------------------------------------------------------------------------


class TestAssertApiFields:
    def test_all_fields_present(self) -> None:
        resp = _make_response(200, {"id": "1", "status": "running", "repo": "org/repo"})
        page = _make_page(response=resp)
        result = assert_api_fields(page, "/api/v1/tasks/1", ["id", "status", "repo"])
        assert result["id"] == "1"

    def test_missing_field_raises(self) -> None:
        resp = _make_response(200, {"id": "1", "status": "running"})
        page = _make_page(response=resp)
        with pytest.raises(AssertionError, match="missing required fields"):
            assert_api_fields(page, "/api/v1/tasks/1", ["id", "status", "repo"])

    def test_nested_key(self) -> None:
        resp = _make_response(200, {"task": {"id": "1", "status": "done", "repo": "org/r"}})
        page = _make_page(response=resp)
        result = assert_api_fields(
            page,
            "/api/v1/tasks/1",
            ["id", "status", "repo"],
            nested_key="task",
        )
        assert result["status"] == "done"

    def test_nested_key_missing_raises(self) -> None:
        resp = _make_response(200, {"data": {"id": "1"}})
        page = _make_page(response=resp)
        with pytest.raises(AssertionError, match="nested key .* not found"):
            assert_api_fields(page, "/api/data", ["id"], nested_key="task")

    def test_non_json_object_raises(self) -> None:
        resp = _make_response(200, [{"id": 1}])
        page = _make_page(response=resp)
        with pytest.raises(AssertionError, match="expected JSON object"):
            assert_api_fields(page, "/api/items", ["id"])

    def test_5xx_raises(self) -> None:
        resp = _make_response(500, {"error": "internal"})
        page = _make_page(response=resp)
        with pytest.raises(AssertionError, match="expected 2xx status, got 500"):
            assert_api_fields(page, "/api/v1/tasks/1", ["id"])

    def test_post_method_used(self) -> None:
        resp = _make_response(200, {"result": "ok"})
        page = _make_page(response=resp)
        result = assert_api_fields(
            page,
            "/api/v1/action",
            ["result"],
            method="POST",
            body={"action": "run"},
        )
        assert result["result"] == "ok"
        page.request.post.assert_called_once()


# ---------------------------------------------------------------------------
# assert_api_no_error
# ---------------------------------------------------------------------------


class TestAssertApiNoError:
    def test_clean_200(self) -> None:
        resp = _make_response(200, {"status": "ok"})
        page = _make_page(response=resp)
        result = assert_api_no_error(page, "/healthz")
        assert result == {"status": "ok"}

    def test_404_raises(self) -> None:
        resp = _make_response(404, {"error": "not found"})
        page = _make_page(response=resp)
        with pytest.raises(AssertionError, match="received error status 404"):
            assert_api_no_error(page, "/missing")

    def test_500_raises(self) -> None:
        resp = _make_response(500, {"error": "server error"})
        page = _make_page(response=resp)
        with pytest.raises(AssertionError, match="received error status 500"):
            assert_api_no_error(page, "/api/boom")

    def test_error_key_in_body_raises(self) -> None:
        resp = _make_response(200, {"error": "something went wrong"})
        page = _make_page(response=resp)
        with pytest.raises(AssertionError, match="error indicator"):
            assert_api_no_error(page, "/api/v1/tasks")

    def test_traceback_key_in_body_raises(self) -> None:
        resp = _make_response(200, {"traceback": "Traceback (most recent call last)..."})
        page = _make_page(response=resp)
        with pytest.raises(AssertionError, match="error indicator"):
            assert_api_no_error(page, "/api/v1/bad")

    def test_empty_error_key_is_ok(self) -> None:
        """An empty or falsy 'error' field should not trigger a failure."""
        resp = _make_response(200, {"status": "ok", "error": ""})
        page = _make_page(response=resp)
        result = assert_api_no_error(page, "/healthz")
        assert result is not None

    def test_non_json_body_does_not_raise(self) -> None:
        """Non-JSON 2xx responses should pass the no-error check."""
        resp = _make_response(200, text="OK")
        page = _make_page(response=resp)
        result = assert_api_no_error(page, "/healthz")
        # Returns None for non-JSON
        assert result is None

    def test_error_message_includes_path(self) -> None:
        resp = _make_response(403)
        page = _make_page(response=resp)
        with pytest.raises(AssertionError, match="/admin/health"):
            assert_api_no_error(page, "/admin/health")


# ---------------------------------------------------------------------------
# build_auth_headers
# ---------------------------------------------------------------------------


class TestBuildAuthHeaders:
    def test_user_id_header(self) -> None:
        headers = build_auth_headers(user_id="admin")
        assert headers["X-User-ID"] == "admin"
        assert "Authorization" not in headers

    def test_basic_auth_header(self) -> None:
        import base64

        headers = build_auth_headers(basic_credentials="user:password")
        expected = "Basic " + base64.b64encode(b"user:password").decode()
        assert headers["Authorization"] == expected

    def test_bearer_token_header(self) -> None:
        headers = build_auth_headers(bearer_token="tok123")
        assert headers["Authorization"] == "Bearer tok123"

    def test_basic_takes_precedence_over_bearer(self) -> None:
        """basic_credentials should win over bearer_token when both supplied."""
        headers = build_auth_headers(
            basic_credentials="u:p", bearer_token="should-be-ignored"
        )
        assert headers["Authorization"].startswith("Basic ")

    def test_extra_headers_merged(self) -> None:
        headers = build_auth_headers(
            user_id="alice",
            extra={"X-Request-ID": "abc123", "Accept": "application/json"},
        )
        assert headers["X-User-ID"] == "alice"
        assert headers["X-Request-ID"] == "abc123"
        assert headers["Accept"] == "application/json"

    def test_empty_call_returns_empty_dict(self) -> None:
        headers = build_auth_headers()
        assert headers == {}


# ---------------------------------------------------------------------------
# Integration-style: request_context fallback
# ---------------------------------------------------------------------------


class TestRequestContextFallback:
    def test_direct_context_object(self) -> None:
        """Helpers work when passed a bare APIRequestContext (no .request)."""
        resp = _make_response(200, {"status": "ok"})
        ctx = MagicMock()
        ctx.get.return_value = resp
        # Pass ctx directly (no .request attribute on ctx itself — simulate by
        # removing the .request attribute)
        del ctx.request

        result = assert_api_endpoint(ctx, "GET", "/healthz", 200)
        assert result == {"status": "ok"}
        ctx.get.assert_called_once()
