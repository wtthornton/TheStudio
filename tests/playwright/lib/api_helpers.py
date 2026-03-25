"""API Endpoint Verification Helper (Epic 58, Story 58.4).

Reusable helpers that call API endpoints via Playwright's ``APIRequestContext``
(sharing authentication cookies/headers with the browser session) and assert on
HTTP status codes, JSON response structure, and absence of error payloads.

All helpers accept a Playwright ``Page`` object and derive the request context
from ``page.request`` so that any session cookies / ``Authorization`` headers
set by ``page.context`` are automatically forwarded.  Alternatively, callers
may pass any object with a ``.request`` attribute that conforms to the
Playwright ``APIRequestContext`` interface (e.g. a ``BrowserContext``).

Covers:
- ``assert_api_endpoint`` — assert HTTP status + optional JSON key presence
- ``assert_api_returns_data`` — assert list or object endpoint returns data
- ``assert_api_fields`` — assert all required fields present in JSON response
- ``assert_api_no_error`` — assert no 4xx/5xx status and no error body

Usage example::

    from tests.playwright.lib.api_helpers import (
        assert_api_endpoint,
        assert_api_fields,
        assert_api_no_error,
        assert_api_returns_data,
    )

    def test_healthz(page):
        page.goto("/admin/ui/dashboard")
        assert_api_endpoint(page, "GET", "/healthz", 200, json_keys=["status"])
        assert_api_no_error(page, "/healthz")

    def test_list_endpoint(page):
        page.goto("/admin/ui/repos")
        assert_api_returns_data(page, "/api/v1/repos", list_key="repos")

Authentication notes:

    # Pass extra headers for Basic Auth / X-User-ID endpoints:
    assert_api_endpoint(
        page,
        "GET",
        "/admin/health",
        200,
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert_api_no_error(
        page,
        "/admin/health",
        headers={"X-User-ID": "admin"},
    )
"""

from __future__ import annotations

import json as _json
from typing import Any

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Maximum number of response body characters to include in failure messages.
_BODY_EXCERPT_LEN = 500

# HTTP methods supported by Playwright's APIRequestContext.
_SUPPORTED_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})

# Status code ranges considered error responses.
_CLIENT_ERROR_RANGE = range(400, 500)
_SERVER_ERROR_RANGE = range(500, 600)

# JSON body keys that indicate an error payload.
_ERROR_BODY_KEYS = ("error", "detail", "traceback", "exception", "message")


def _request_context(page_or_ctx: Any) -> Any:
    """Return the Playwright ``APIRequestContext`` from a Page or Context.

    Playwright ``Page`` objects expose ``.request``; ``BrowserContext``
    objects also expose ``.request``.  We fall back to the object itself if
    neither attribute is present, which makes the helper testable with
    lightweight fakes.
    """
    if hasattr(page_or_ctx, "request"):
        return page_or_ctx.request
    return page_or_ctx


def _make_request(
    ctx: Any,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> Any:
    """Dispatch a request via Playwright APIRequestContext and return the response.

    Args:
        ctx: Playwright ``APIRequestContext`` (obtained via ``_request_context``).
        method: HTTP method string (e.g. ``"GET"``).
        path: Relative URL path (e.g. ``"/healthz"``).
        headers: Optional extra request headers.
        body: Optional JSON body dict (only sent for POST/PUT/PATCH).

    Returns:
        Playwright ``APIResponse`` object.
    """
    method = method.upper()
    if method not in _SUPPORTED_METHODS:
        raise ValueError(
            f"Unsupported HTTP method {method!r}. "
            f"Supported: {sorted(_SUPPORTED_METHODS)!r}"
        )

    kwargs: dict[str, Any] = {}
    if headers:
        kwargs["headers"] = headers
    if body is not None and method in {"POST", "PUT", "PATCH"}:
        kwargs["data"] = body

    dispatch = getattr(ctx, method.lower(), None)
    if dispatch is None:
        raise AttributeError(
            f"APIRequestContext does not have a {method.lower()!r} method"
        )

    return dispatch(path, **kwargs)


def _response_body_excerpt(response: Any) -> str:
    """Return a truncated string representation of the response body.

    Tries JSON first (pretty-printed), then falls back to plain text.
    """
    try:
        body = response.json()
        text = _json.dumps(body, indent=2)
    except Exception:
        try:
            text = response.text()
        except Exception:
            text = "<unreadable body>"

    if len(text) > _BODY_EXCERPT_LEN:
        text = text[:_BODY_EXCERPT_LEN] + f"… (truncated to {_BODY_EXCERPT_LEN} chars)"
    return text


def _safe_json(response: Any) -> dict[str, Any] | list[Any] | None:
    """Return parsed JSON from a response, or ``None`` on failure."""
    try:
        return response.json()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public assertion helpers
# ---------------------------------------------------------------------------


def assert_api_endpoint(
    page: Any,
    method: str,
    path: str,
    expected_status: int,
    *,
    json_keys: list[str] | None = None,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any] | None:
    """Call an API endpoint and assert the HTTP status code.

    Optionally verifies that the JSON response contains specific top-level keys.
    Returns the parsed JSON body so callers can perform additional assertions.

    Args:
        page: Playwright ``Page`` (or any object with a ``.request`` attribute).
        method: HTTP method, e.g. ``"GET"`` or ``"POST"``.
        path: Relative URL path, e.g. ``"/healthz"`` or ``"/api/v1/tasks"``.
        expected_status: The HTTP status code the response **must** have.
        json_keys: Optional list of top-level JSON keys that must be present.
        headers: Optional extra request headers (e.g. Basic Auth, X-User-ID).
        body: Optional JSON dict to send as the request body (POST/PUT/PATCH).

    Returns:
        Parsed JSON response body, or ``None`` if the body is not JSON.

    Raises:
        AssertionError: If the actual status code does not match, or if any
            required JSON keys are absent from the response.

    Example::

        data = assert_api_endpoint(page, "GET", "/healthz", 200,
                                   json_keys=["status"])
        assert data["status"] in ("ok", "degraded")
    """
    ctx = _request_context(page)
    response = _make_request(ctx, method, path, headers=headers, body=body)

    actual_status = response.status
    if actual_status != expected_status:
        excerpt = _response_body_excerpt(response)
        raise AssertionError(
            f"API {method} {path!r}: expected status {expected_status}, "
            f"got {actual_status}.\n"
            f"  Response body: {excerpt}"
        )

    parsed = _safe_json(response)

    if json_keys:
        if not isinstance(parsed, dict):
            raise AssertionError(
                f"API {method} {path!r}: expected JSON object for key checks "
                f"but response is {type(parsed).__name__!r}.\n"
                f"  Response body: {_response_body_excerpt(response)}"
            )
        missing = [k for k in json_keys if k not in parsed]
        if missing:
            raise AssertionError(
                f"API {method} {path!r}: missing expected JSON keys {missing!r}.\n"
                f"  Present keys : {list(parsed.keys())!r}\n"
                f"  Response body: {_response_body_excerpt(response)}"
            )

    return parsed


def assert_api_returns_data(
    page: Any,
    path: str,
    *,
    list_key: str | None = None,
    allow_empty: bool = True,
    headers: dict[str, str] | None = None,
) -> dict[str, Any] | list[Any]:
    """Assert that a GET endpoint returns a non-error response with data.

    For list endpoints, verifies the response contains an array (either directly
    or under ``list_key``).  Does not fail on empty lists unless
    ``allow_empty=False``.

    Args:
        page: Playwright ``Page`` (or any object with a ``.request`` attribute).
        path: Relative URL path of the list endpoint.
        list_key: Optional top-level JSON key that wraps the list (e.g.
            ``"repos"`` for ``{"repos": [...], "total": 5}``).
        allow_empty: When ``True`` (default), an empty list ``[]`` is accepted.
            Set to ``False`` to require at least one item.
        headers: Optional extra request headers.

    Returns:
        The list (or full JSON body if ``list_key`` is not given).

    Raises:
        AssertionError: If the status is not 2xx, the body is not JSON, the
            ``list_key`` is absent, the value under ``list_key`` is not a list,
            or the list is empty when ``allow_empty=False``.

    Example::

        repos = assert_api_returns_data(page, "/api/v1/repos", list_key="repos")
        assert all("name" in r for r in repos)
    """
    ctx = _request_context(page)
    response = _make_request(ctx, "GET", path, headers=headers)

    actual_status = response.status
    if actual_status < 200 or actual_status >= 300:
        excerpt = _response_body_excerpt(response)
        raise AssertionError(
            f"API GET {path!r}: expected 2xx status, got {actual_status}.\n"
            f"  Response body: {excerpt}"
        )

    parsed = _safe_json(response)
    if parsed is None:
        raise AssertionError(
            f"API GET {path!r}: response body is not valid JSON.\n"
            f"  Response body: {_response_body_excerpt(response)}"
        )

    if list_key is not None:
        if not isinstance(parsed, dict):
            raise AssertionError(
                f"API GET {path!r}: expected JSON object with key {list_key!r}, "
                f"got {type(parsed).__name__!r}."
            )
        if list_key not in parsed:
            raise AssertionError(
                f"API GET {path!r}: list key {list_key!r} not found in response.\n"
                f"  Present keys : {list(parsed.keys())!r}"  # type: ignore[union-attr]
            )
        data = parsed[list_key]
        if not isinstance(data, list):
            raise AssertionError(
                f"API GET {path!r}: expected {list_key!r} to be a list, "
                f"got {type(data).__name__!r}."
            )
    else:
        data = parsed  # type: ignore[assignment]

    if not allow_empty:
        if isinstance(data, list) and len(data) == 0:
            raise AssertionError(
                f"API GET {path!r}: expected non-empty list"
                + (f" under key {list_key!r}" if list_key else "")
                + ", but got empty list []."
            )

    return data  # type: ignore[return-value]


def assert_api_fields(
    page: Any,
    path: str,
    required_fields: list[str],
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    nested_key: str | None = None,
) -> dict[str, Any]:
    """Assert that all required fields are present in the JSON response.

    Calls the endpoint and validates that each field in ``required_fields``
    exists as a top-level key in the response object.  If ``nested_key`` is
    provided, the field check is applied to the nested object at that key.

    Args:
        page: Playwright ``Page`` (or any object with a ``.request`` attribute).
        path: Relative URL path of the endpoint.
        required_fields: List of JSON field names that must be present.
        method: HTTP method (default ``"GET"``).
        headers: Optional extra request headers.
        body: Optional JSON body dict for POST/PUT/PATCH.
        nested_key: If provided, field checks are applied to
            ``response[nested_key]`` instead of the root response object.

    Returns:
        The JSON object (or nested object) that was validated.

    Raises:
        AssertionError: If the response is not 2xx, not a JSON object, or any
            required field is absent.

    Example::

        task = assert_api_fields(
            page,
            "/api/v1/tasks/123",
            required_fields=["id", "status", "repo", "created_at"],
        )
        assert task["status"] in ("pending", "running", "done")
    """
    ctx = _request_context(page)
    response = _make_request(ctx, method, path, headers=headers, body=body)

    actual_status = response.status
    if actual_status < 200 or actual_status >= 300:
        excerpt = _response_body_excerpt(response)
        raise AssertionError(
            f"API {method} {path!r}: expected 2xx status, got {actual_status}.\n"
            f"  Response body: {excerpt}"
        )

    parsed = _safe_json(response)
    if not isinstance(parsed, dict):
        raise AssertionError(
            f"API {method} {path!r}: expected JSON object for field checks, "
            f"got {type(parsed).__name__!r}.\n"
            f"  Response body: {_response_body_excerpt(response)}"
        )

    target: dict[str, Any] = parsed
    if nested_key is not None:
        if nested_key not in parsed:
            raise AssertionError(
                f"API {method} {path!r}: nested key {nested_key!r} not found.\n"
                f"  Present keys : {list(parsed.keys())!r}"
            )
        if not isinstance(parsed[nested_key], dict):
            raise AssertionError(
                f"API {method} {path!r}: nested key {nested_key!r} is not a "
                f"JSON object, got {type(parsed[nested_key]).__name__!r}."
            )
        target = parsed[nested_key]

    missing = [f for f in required_fields if f not in target]
    if missing:
        raise AssertionError(
            f"API {method} {path!r}: missing required fields {missing!r}.\n"
            f"  Present keys : {list(target.keys())!r}\n"
            + (f"  Nested under : {nested_key!r}\n" if nested_key else "")
            + f"  Response body: {_response_body_excerpt(response)}"
        )

    return target


def assert_api_no_error(
    page: Any,
    path: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any] | list[Any] | None:
    """Assert that an endpoint returns no HTTP error and no error payload.

    Checks two things:
    1. The HTTP status is not 4xx or 5xx.
    2. The JSON body (if any) does not contain error-indicator keys such as
       ``"error"``, ``"traceback"``, or ``"exception"`` with non-empty values.

    Args:
        page: Playwright ``Page`` (or any object with a ``.request`` attribute).
        path: Relative URL path of the endpoint.
        method: HTTP method (default ``"GET"``).
        headers: Optional extra request headers.
        body: Optional JSON body dict for POST/PUT/PATCH.

    Returns:
        Parsed JSON response body (or ``None`` if the body is not JSON).

    Raises:
        AssertionError: If the status code is 4xx/5xx, or if the response body
            contains an error payload.

    Example::

        assert_api_no_error(page, "/healthz")
        assert_api_no_error(page, "/admin/health",
                            headers={"Authorization": "Basic dXNlcjpwYXNz"})
    """
    ctx = _request_context(page)
    response = _make_request(ctx, method, path, headers=headers, body=body)

    actual_status = response.status
    if actual_status in _CLIENT_ERROR_RANGE or actual_status in _SERVER_ERROR_RANGE:
        excerpt = _response_body_excerpt(response)
        raise AssertionError(
            f"API {method} {path!r}: received error status {actual_status}.\n"
            f"  Response body: {excerpt}"
        )

    parsed = _safe_json(response)

    if isinstance(parsed, dict):
        for key in _ERROR_BODY_KEYS:
            value = parsed.get(key)
            # Treat non-empty string / non-False truthy values as errors
            if value and (isinstance(value, str) and value.strip()):
                excerpt = _response_body_excerpt(response)
                raise AssertionError(
                    f"API {method} {path!r}: response contains error indicator "
                    f"{key!r} = {value!r}.\n"
                    f"  Response body: {excerpt}"
                )

    return parsed


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def build_auth_headers(
    *,
    user_id: str | None = None,
    basic_credentials: str | None = None,
    bearer_token: str | None = None,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build a headers dict for authenticated API calls.

    Args:
        user_id: Value for the ``X-User-ID`` header (admin endpoints).
        basic_credentials: Raw ``user:password`` string for Basic Auth
            (will be base64-encoded automatically).
        bearer_token: Token for ``Authorization: Bearer <token>`` header.
        extra: Any additional headers to merge in.

    Returns:
        A ``dict[str, str]`` ready to pass as ``headers=`` to any helper.

    Example::

        headers = build_auth_headers(user_id="admin-user")
        assert_api_no_error(page, "/admin/health", headers=headers)

        headers = build_auth_headers(basic_credentials="user:password")
        assert_api_endpoint(page, "GET", "/admin/repos", 200, headers=headers)
    """
    import base64

    headers: dict[str, str] = {}

    if user_id is not None:
        headers["X-User-ID"] = user_id

    if basic_credentials is not None:
        encoded = base64.b64encode(basic_credentials.encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"
    elif bearer_token is not None:
        headers["Authorization"] = f"Bearer {bearer_token}"

    if extra:
        headers.update(extra)

    return headers


# ---------------------------------------------------------------------------
# Convenience re-exports
# ---------------------------------------------------------------------------

__all__ = [
    # Core assertion helpers
    "assert_api_endpoint",
    "assert_api_returns_data",
    "assert_api_fields",
    "assert_api_no_error",
    # Auth helper
    "build_auth_headers",
    # Constants (for advanced consumers)
    "_BODY_EXCERPT_LEN",
    "_ERROR_BODY_KEYS",
]
