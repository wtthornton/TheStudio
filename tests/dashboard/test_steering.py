"""Tests for the pipeline steering API (src/dashboard/steering.py).

Covers:
- ``_detect_current_stage`` helper (pure unit tests, no I/O)
- All 5 steering action endpoints (pause/resume/abort/redirect/retry):
  happy path (202), 404 task-not-found, 409 conflict, 400 bad request
- ``GET /steering/audit`` — list all audit entries with optional action filter
- ``GET /tasks/{id}/audit``  — list per-task audit entries, 404 on missing task
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.app import app
from src.db.connection import get_session
from src.models.taskpacket import TaskPacketStatus

from tests.dashboard.conftest import make_task_row

# Re-export the helper under test directly so import errors surface early.
from src.dashboard.steering import _detect_current_stage  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BASE = "http://test"
_PATH = "/api/v1/dashboard"

# A stage_timings snapshot with "implement" as the active (no-end) stage.
_TIMINGS_AT_IMPLEMENT: dict = {
    "intake": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T00:01:00Z"},
    "context": {"start": "2026-01-01T00:01:00Z", "end": "2026-01-01T00:02:00Z"},
    "implement": {"start": "2026-01-01T00:10:00Z", "end": None},
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _mock_session() -> AsyncMock:
    """Return a minimal mocked AsyncSession (no real DB)."""
    session = AsyncMock()
    session.add = MagicMock()
    return session


def _temporal_client_patch() -> tuple[AsyncMock, object]:
    """Return (mock_client, patch context-manager) for get_temporal_client.

    The import in steering.py is inside the function body::

        from src.ingress.workflow_trigger import get_temporal_client

    We therefore patch the *source* module so the local import picks up the
    mock rather than patching the steering module namespace.
    """
    mock_handle = AsyncMock()
    mock_handle.signal = AsyncMock()
    mock_client = AsyncMock()
    mock_client.get_workflow_handle = MagicMock(return_value=mock_handle)
    patcher = patch(
        "src.ingress.workflow_trigger.get_temporal_client",
        AsyncMock(return_value=mock_client),
    )
    return mock_client, patcher


# ===========================================================================
# _detect_current_stage  (pure unit tests — no HTTP, no DB, no Temporal)
# ===========================================================================


class TestDetectCurrentStage:
    """Unit tests for the _detect_current_stage helper."""

    def test_returns_none_when_timings_is_none(self) -> None:
        assert _detect_current_stage(None) is None

    def test_returns_none_when_timings_is_empty_dict(self) -> None:
        assert _detect_current_stage({}) is None

    def test_returns_active_stage_with_null_end(self) -> None:
        timings = {
            "intake": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T00:01:00Z"},
            "context": {"start": "2026-01-01T00:01:00Z", "end": None},
        }
        assert _detect_current_stage(timings) == "context"

    def test_returns_none_when_all_stages_have_end(self) -> None:
        timings = {
            "intake": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T00:01:00Z"},
            "context": {"start": "2026-01-01T00:01:00Z", "end": "2026-01-01T00:02:00Z"},
        }
        assert _detect_current_stage(timings) is None

    def test_returns_none_when_entry_has_no_start(self) -> None:
        # A timing entry without a "start" key must not be treated as active.
        timings = {"intake": {"end": None}}
        assert _detect_current_stage(timings) is None

    def test_returns_highest_order_stage_when_multiple_active(self) -> None:
        # "implement" (order 10) should beat "intake" (order 1).
        timings = {
            "intake": {"start": "2026-01-01T00:00:00Z", "end": None},
            "implement": {"start": "2026-01-01T00:10:00Z", "end": None},
        }
        assert _detect_current_stage(timings) == "implement"

    def test_unknown_stage_name_falls_back_to_order_zero(self) -> None:
        # Unknown stage names get order=0; they still count if active.
        timings = {"unknown_stage": {"start": "2026-01-01T00:00:00Z", "end": None}}
        result = _detect_current_stage(timings)
        assert result == "unknown_stage"

    def test_non_dict_timing_values_are_skipped(self) -> None:
        # Bad values (strings, ints) should not raise and should be ignored.
        timings = {
            "intake": "bad_value",
            "context": {"start": "2026-01-01T00:01:00Z", "end": None},
        }
        assert _detect_current_stage(timings) == "context"

    def test_active_stage_with_missing_end_key(self) -> None:
        # A timing dict that has "start" but no "end" key at all is active.
        timings = {"intake": {"start": "2026-01-01T00:00:00Z"}}
        assert _detect_current_stage(timings) == "intake"


# ===========================================================================
# POST /tasks/{id}/pause
# ===========================================================================


@pytest.mark.asyncio
async def test_pause_happy_path(no_dashboard_auth: None) -> None:
    """IN_PROGRESS task: 202, pause_task signal sent."""
    task_id = uuid4()
    task = make_task_row(id=task_id, status=TaskPacketStatus.IN_PROGRESS)
    session = _mock_session()
    mock_client, temporal_patcher = _temporal_client_patch()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with temporal_patcher, patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=task)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(f"{_PATH}/tasks/{task_id}/pause")
        assert resp.status_code == 202
        body = resp.json()
        assert body["action"] == "pause"
        assert body["status"] == "accepted"
        assert str(task_id) == body["task_id"]
        handle = mock_client.get_workflow_handle.return_value
        handle.signal.assert_awaited_once()
        assert handle.signal.call_args[0][0] == "pause_task"
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_pause_404_task_not_found(no_dashboard_auth: None) -> None:
    """Pausing a non-existent task returns 404."""
    task_id = uuid4()
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=None)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(f"{_PATH}/tasks/{task_id}/pause")
        assert resp.status_code == 404
        assert str(task_id) in resp.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_pause_409_already_paused(no_dashboard_auth: None) -> None:
    """Pausing an already-PAUSED task returns 409."""
    task_id = uuid4()
    task = make_task_row(id=task_id, status=TaskPacketStatus.PAUSED)
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=task)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(f"{_PATH}/tasks/{task_id}/pause")
        assert resp.status_code == 409
        assert "already paused" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "terminal_status",
    [
        TaskPacketStatus.PUBLISHED,
        TaskPacketStatus.FAILED,
        TaskPacketStatus.ABORTED,
        TaskPacketStatus.REJECTED,
        TaskPacketStatus.AWAITING_APPROVAL_EXPIRED,
    ],
)
async def test_pause_409_terminal_state(
    terminal_status: TaskPacketStatus, no_dashboard_auth: None
) -> None:
    """Pausing a task in any terminal state returns 409."""
    task_id = uuid4()
    task = make_task_row(id=task_id, status=terminal_status)
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=task)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(f"{_PATH}/tasks/{task_id}/pause")
        assert resp.status_code == 409
        assert "terminal" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_session, None)


# ===========================================================================
# POST /tasks/{id}/resume
# ===========================================================================


@pytest.mark.asyncio
async def test_resume_happy_path(no_dashboard_auth: None) -> None:
    """PAUSED task: 202, resume_task signal sent."""
    task_id = uuid4()
    task = make_task_row(id=task_id, status=TaskPacketStatus.PAUSED)
    session = _mock_session()
    mock_client, temporal_patcher = _temporal_client_patch()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with temporal_patcher, patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=task)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(f"{_PATH}/tasks/{task_id}/resume")
        assert resp.status_code == 202
        body = resp.json()
        assert body["action"] == "resume"
        handle = mock_client.get_workflow_handle.return_value
        handle.signal.assert_awaited_once()
        assert handle.signal.call_args[0][0] == "resume_task"
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_resume_404_task_not_found(no_dashboard_auth: None) -> None:
    """Resuming a non-existent task returns 404."""
    task_id = uuid4()
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=None)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(f"{_PATH}/tasks/{task_id}/resume")
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_resume_409_not_paused(no_dashboard_auth: None) -> None:
    """Resuming an IN_PROGRESS task (not paused) returns 409."""
    task_id = uuid4()
    task = make_task_row(id=task_id, status=TaskPacketStatus.IN_PROGRESS)
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=task)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(f"{_PATH}/tasks/{task_id}/resume")
        assert resp.status_code == 409
        assert "not paused" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_session, None)


# ===========================================================================
# POST /tasks/{id}/abort
# ===========================================================================


@pytest.mark.asyncio
async def test_abort_happy_path(no_dashboard_auth: None) -> None:
    """IN_PROGRESS task + reason: 202, abort_task signal sent."""
    task_id = uuid4()
    task = make_task_row(id=task_id, status=TaskPacketStatus.IN_PROGRESS)
    session = _mock_session()
    mock_client, temporal_patcher = _temporal_client_patch()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with temporal_patcher, patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=task)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(
                    f"{_PATH}/tasks/{task_id}/abort",
                    json={"reason": "aborting for test"},
                )
        assert resp.status_code == 202
        body = resp.json()
        assert body["action"] == "abort"
        handle = mock_client.get_workflow_handle.return_value
        handle.signal.assert_awaited_once()
        assert handle.signal.call_args[0][0] == "abort_task"
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_abort_404_task_not_found(no_dashboard_auth: None) -> None:
    task_id = uuid4()
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=None)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(
                    f"{_PATH}/tasks/{task_id}/abort",
                    json={"reason": "test"},
                )
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_abort_409_terminal(no_dashboard_auth: None) -> None:
    """Aborting a FAILED task returns 409 (already terminal)."""
    task_id = uuid4()
    task = make_task_row(id=task_id, status=TaskPacketStatus.FAILED)
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=task)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(
                    f"{_PATH}/tasks/{task_id}/abort",
                    json={"reason": "test"},
                )
        assert resp.status_code == 409
        assert "terminal" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_abort_400_missing_reason(no_dashboard_auth: None) -> None:
    """Abort with empty body returns 422 (Pydantic validation — reason is required)."""
    task_id = uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
        resp = await client.post(f"{_PATH}/tasks/{task_id}/abort", json={})
    assert resp.status_code == 422


# ===========================================================================
# POST /tasks/{id}/redirect
# ===========================================================================


@pytest.mark.asyncio
async def test_redirect_happy_path(no_dashboard_auth: None) -> None:
    """Redirect from 'implement' to earlier stage 'intake': 202, redirect_task signal."""
    task_id = uuid4()
    task = make_task_row(
        id=task_id,
        status=TaskPacketStatus.IN_PROGRESS,
        stage_timings=_TIMINGS_AT_IMPLEMENT,
    )
    session = _mock_session()
    mock_client, temporal_patcher = _temporal_client_patch()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with temporal_patcher, patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=task)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(
                    f"{_PATH}/tasks/{task_id}/redirect",
                    json={"target_stage": "intake", "reason": "restart from intake"},
                )
        assert resp.status_code == 202
        body = resp.json()
        assert body["action"] == "redirect"
        handle = mock_client.get_workflow_handle.return_value
        handle.signal.assert_awaited_once()
        assert handle.signal.call_args[0][0] == "redirect_task"
        # target_stage should be the first positional arg after signal name
        signal_args = handle.signal.call_args[1].get("args") or handle.signal.call_args[0][1]
        assert signal_args[0] == "intake"
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_redirect_404_task_not_found(no_dashboard_auth: None) -> None:
    task_id = uuid4()
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=None)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(
                    f"{_PATH}/tasks/{task_id}/redirect",
                    json={"target_stage": "intake", "reason": "r"},
                )
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_redirect_409_terminal(no_dashboard_auth: None) -> None:
    """Redirecting an ABORTED task returns 409."""
    task_id = uuid4()
    task = make_task_row(id=task_id, status=TaskPacketStatus.ABORTED)
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=task)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(
                    f"{_PATH}/tasks/{task_id}/redirect",
                    json={"target_stage": "intake", "reason": "r"},
                )
        assert resp.status_code == 409
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_redirect_400_unknown_stage(no_dashboard_auth: None) -> None:
    """Redirect to an unknown stage name returns 400."""
    task_id = uuid4()
    task = make_task_row(id=task_id, status=TaskPacketStatus.IN_PROGRESS)
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=task)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(
                    f"{_PATH}/tasks/{task_id}/redirect",
                    json={"target_stage": "not_a_real_stage", "reason": "r"},
                )
        assert resp.status_code == 400
        assert "unknown target_stage" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_redirect_400_target_not_earlier_than_current(no_dashboard_auth: None) -> None:
    """Redirect to a stage at or after the current stage returns 400.

    Task is active at 'implement' (order 10); 'verify' (order 11) is later.
    """
    task_id = uuid4()
    task = make_task_row(
        id=task_id,
        status=TaskPacketStatus.IN_PROGRESS,
        stage_timings=_TIMINGS_AT_IMPLEMENT,
    )
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=task)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(
                    f"{_PATH}/tasks/{task_id}/redirect",
                    json={"target_stage": "verify", "reason": "r"},
                )
        assert resp.status_code == 400
        assert "earlier" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_session, None)


# ===========================================================================
# POST /tasks/{id}/retry
# ===========================================================================


@pytest.mark.asyncio
async def test_retry_happy_path(no_dashboard_auth: None) -> None:
    """Active task: 202, retry_stage signal sent with provided reason."""
    task_id = uuid4()
    task = make_task_row(
        id=task_id,
        status=TaskPacketStatus.IN_PROGRESS,
        stage_timings=_TIMINGS_AT_IMPLEMENT,
    )
    session = _mock_session()
    mock_client, temporal_patcher = _temporal_client_patch()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with temporal_patcher, patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=task)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(
                    f"{_PATH}/tasks/{task_id}/retry",
                    json={"reason": "manual retry requested"},
                )
        assert resp.status_code == 202
        body = resp.json()
        assert body["action"] == "retry"
        handle = mock_client.get_workflow_handle.return_value
        handle.signal.assert_awaited_once()
        assert handle.signal.call_args[0][0] == "retry_stage"
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_retry_happy_path_default_reason(no_dashboard_auth: None) -> None:
    """Retry with empty body uses the default reason (field default)."""
    task_id = uuid4()
    task = make_task_row(id=task_id, status=TaskPacketStatus.IN_PROGRESS)
    session = _mock_session()
    _, temporal_patcher = _temporal_client_patch()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with temporal_patcher, patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=task)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(f"{_PATH}/tasks/{task_id}/retry", json={})
        assert resp.status_code == 202
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_retry_404_task_not_found(no_dashboard_auth: None) -> None:
    task_id = uuid4()
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=None)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(f"{_PATH}/tasks/{task_id}/retry", json={"reason": "r"})
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "terminal_status",
    [
        TaskPacketStatus.REJECTED,
        TaskPacketStatus.AWAITING_APPROVAL_EXPIRED,
        TaskPacketStatus.ABORTED,
    ],
)
async def test_retry_409_terminal(
    terminal_status: TaskPacketStatus, no_dashboard_auth: None
) -> None:
    """Retrying a task in any terminal state returns 409."""
    task_id = uuid4()
    task = make_task_row(id=task_id, status=terminal_status)
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=task)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.post(f"{_PATH}/tasks/{task_id}/retry", json={"reason": "r"})
        assert resp.status_code == 409
    finally:
        app.dependency_overrides.pop(get_session, None)


# ===========================================================================
# GET /steering/audit
# ===========================================================================


@pytest.mark.asyncio
async def test_list_all_audit_returns_empty_list(no_dashboard_auth: None) -> None:
    """GET /steering/audit with no entries returns 200 and empty list."""
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.steering.list_all_audit_entries", AsyncMock(return_value=[])):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.get(f"{_PATH}/steering/audit")
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_list_all_audit_passes_action_filter(no_dashboard_auth: None) -> None:
    """GET /steering/audit?action=pause forwards action filter to the CRUD function."""
    session = _mock_session()
    mock_fn = AsyncMock(return_value=[])

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.steering.list_all_audit_entries", mock_fn):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.get(f"{_PATH}/steering/audit?action=pause")
        assert resp.status_code == 200
        # Verify the action kwarg was forwarded.
        call_kwargs = mock_fn.call_args[1]
        assert call_kwargs.get("action") is not None
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_list_all_audit_invalid_action_returns_422(no_dashboard_auth: None) -> None:
    """GET /steering/audit?action=bad_value is rejected by FastAPI query validation (422)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
        resp = await client.get(f"{_PATH}/steering/audit?action=not_a_valid_action")
    assert resp.status_code == 422


# ===========================================================================
# GET /tasks/{id}/audit
# ===========================================================================


@pytest.mark.asyncio
async def test_get_task_audit_returns_200_with_empty_list(no_dashboard_auth: None) -> None:
    """GET /tasks/{id}/audit returns 200 and empty list for a known task."""
    task_id = uuid4()
    task = make_task_row(id=task_id, status=TaskPacketStatus.IN_PROGRESS)
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with (
            patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=task)),
            patch("src.dashboard.steering.list_audit_entries_for_task", AsyncMock(return_value=[])),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.get(f"{_PATH}/tasks/{task_id}/audit")
        assert resp.status_code == 200
        assert resp.json() == []
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_get_task_audit_404_task_not_found(no_dashboard_auth: None) -> None:
    """GET /tasks/{id}/audit returns 404 for an unknown task."""
    task_id = uuid4()
    session = _mock_session()

    app.dependency_overrides[get_session] = lambda: session
    try:
        with patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=None)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.get(f"{_PATH}/tasks/{task_id}/audit")
        assert resp.status_code == 404
        assert str(task_id) in resp.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_get_task_audit_pagination_params(no_dashboard_auth: None) -> None:
    """GET /tasks/{id}/audit?limit=5&offset=10 forwards pagination to the CRUD function."""
    task_id = uuid4()
    task = make_task_row(id=task_id, status=TaskPacketStatus.IN_PROGRESS)
    session = _mock_session()
    mock_fn = AsyncMock(return_value=[])

    app.dependency_overrides[get_session] = lambda: session
    try:
        with (
            patch("src.dashboard.steering.get_by_id", AsyncMock(return_value=task)),
            patch("src.dashboard.steering.list_audit_entries_for_task", mock_fn),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url=_BASE) as client:
                resp = await client.get(f"{_PATH}/tasks/{task_id}/audit?limit=5&offset=10")
        assert resp.status_code == 200
        call_kwargs = mock_fn.call_args[1]
        assert call_kwargs.get("limit") == 5
        assert call_kwargs.get("offset") == 10
    finally:
        app.dependency_overrides.pop(get_session, None)
