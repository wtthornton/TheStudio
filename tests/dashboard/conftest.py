"""Shared fixtures for tests/dashboard unit tests.

Provides:
- ``db_session``        — mocked AsyncSession (no real DB required)
- ``mock_temporal``     — patched get_temporal_client returning an AsyncMock client
- ``make_task_row``     — factory function that returns a MagicMock TaskPacketRow
- ``nats_message``      — factory that returns a mock NATS message with helpers
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.dashboard.models.notification import NotificationRow, NotificationType
from src.models.taskpacket import TaskPacketRow, TaskPacketStatus, TaskTrustTier

# ---------------------------------------------------------------------------
# TaskPacketRow factory
# ---------------------------------------------------------------------------

_DEFAULT_TASK_FIELDS: dict[str, Any] = {
    "repo": "owner/repo",
    "issue_id": 42,
    "delivery_id": "d-{id}",
    "source_name": "github",
    "status": TaskPacketStatus.RECEIVED,
    "scope": None,
    "risk_flags": None,
    "complexity_index": None,
    "context_packs": None,
    "intent_spec_id": None,
    "intent_version": None,
    "readiness_evaluation_count": 0,
    "readiness_hold_comment_id": None,
    "readiness_score": None,
    "readiness_miss": False,
    "stage_timings": None,
    "issue_title": "Fix SSO login timeout",
    "issue_body": "## Problem\n\nSSO login times out after 30 seconds.",
    "triage_enrichment": None,
    "rejection_reason": None,
    "routing_result": None,
    "pr_number": None,
    "pr_url": None,
    "task_trust_tier": None,
    "loopback_count": 0,
}


def make_task_row(**overrides: Any) -> MagicMock:
    """Return a ``MagicMock(spec=TaskPacketRow)`` with sensible defaults.

    Each call generates a fresh UUID so rows are independent by default.

    Usage::

        row = make_task_row(status=TaskPacketStatus.IN_PROGRESS)
        row_with_tier = make_task_row(task_trust_tier=TaskTrustTier.SUGGEST)
    """
    task_id: UUID = overrides.pop("id", uuid4())
    correlation_id: UUID = overrides.pop("correlation_id", uuid4())
    now = datetime.now(UTC)

    fields = dict(_DEFAULT_TASK_FIELDS)
    fields["delivery_id"] = fields["delivery_id"].format(id=task_id.hex[:8])
    fields.update(overrides)

    row = MagicMock(spec=TaskPacketRow)
    row.id = task_id
    row.correlation_id = correlation_id
    row.created_at = now
    row.updated_at = now
    for key, value in fields.items():
        setattr(row, key, value)

    return row


# ---------------------------------------------------------------------------
# Async DB session mock
# ---------------------------------------------------------------------------


def _build_execute_side_effect(rows: list[Any], count: int) -> Any:
    """Build a side-effect function that handles count + data queries in order."""
    call_count = 0

    async def _execute(stmt: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            # First call assumed to be a count/scalar query
            result.scalar_one.return_value = count
            result.scalars.return_value.all.return_value = rows
        else:
            result.scalars.return_value.all.return_value = rows
            result.scalar_one.return_value = rows[0] if rows else None
            result.scalar_one_or_none.return_value = rows[0] if rows else None
        return result

    return _execute


@pytest.fixture
def db_session() -> AsyncMock:
    """Mocked AsyncSession with no real DB connection.

    The session exposes:
    - ``session.execute(stmt)`` — returns a MagicMock result
    - ``session.add(obj)`` — no-op
    - ``session.commit()`` — awaitable no-op
    - ``session.refresh(obj)`` — awaitable no-op
    - ``session.delete(obj)`` — awaitable no-op

    For query-specific behaviour, configure the session directly in your test::

        db_session.execute.return_value = MagicMock(...)
    """
    session = AsyncMock()
    session.add = MagicMock()  # sync helper on AsyncSession
    return session


def make_db_session(rows: list[Any] = (), count: int = 0) -> AsyncMock:
    """Return a pre-configured mocked AsyncSession for list/count queries.

    Args:
        rows: Iterable of ORM rows returned by ``scalars().all()``.
        count: Integer returned by the first ``scalar_one()`` call (count query).
    """
    session = AsyncMock()
    session.add = MagicMock()
    session.execute.side_effect = _build_execute_side_effect(list(rows), count)
    return session


# ---------------------------------------------------------------------------
# Mock Temporal client
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_temporal(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Patch ``get_temporal_client`` to return a mock Temporal client.

    The mock exposes ``client.get_workflow_handle(workflow_id)`` which returns
    a workflow handle mock that pre-configures common signals:

    - ``handle.signal(signal_name, arg)`` — awaitable no-op
    - ``handle.query(query_name)``         — awaitable returning ``None``
    - ``handle.describe()``               — awaitable returning a mock info obj

    The fixture patches the import path used by dashboard modules::

        from src.ingress.workflow_trigger import get_temporal_client

    Usage in tests::

        async def test_pause(mock_temporal):
            resp = await client.post(f"/tasks/{task_id}/pause")
            mock_temporal.get_workflow_handle.assert_called_once()
    """
    client_mock = AsyncMock()

    # Default workflow handle behaviour
    handle_mock = AsyncMock()
    handle_mock.signal = AsyncMock()
    handle_mock.query = AsyncMock(return_value=None)
    info_mock = MagicMock()
    info_mock.status = MagicMock()
    handle_mock.describe = AsyncMock(return_value=info_mock)
    client_mock.get_workflow_handle = MagicMock(return_value=handle_mock)

    # Patch all known import sites in dashboard modules
    _targets = [
        "src.dashboard.steering.get_temporal_client",
        "src.dashboard.budget_checker.get_temporal_client",
        "src.dashboard.planning.get_temporal_client",
    ]
    patches = [monkeypatch.setattr(target, AsyncMock(return_value=client_mock)) for target in _targets]  # noqa: F841

    return client_mock


# ---------------------------------------------------------------------------
# Mock NATS message factory
# ---------------------------------------------------------------------------


class MockNatsMessage:
    """Minimal NATS message stub sufficient for ``_on_message`` handler tests.

    Attributes:
        data: Raw bytes payload (set at construction from ``payload``).
        ack_called: Number of times ``ack()`` was awaited.
    """

    def __init__(self, payload: dict[str, Any] | str | bytes) -> None:
        if isinstance(payload, dict):
            self.data: bytes = json.dumps(payload).encode()
        elif isinstance(payload, str):
            self.data = payload.encode()
        else:
            self.data = payload
        self.ack_called: int = 0
        self._ack_mock = AsyncMock()

    async def ack(self) -> None:
        """Acknowledge message receipt (NATS JetStream protocol)."""
        self.ack_called += 1
        await self._ack_mock()

    @property
    def payload_json(self) -> dict[str, Any]:
        """Decode and parse JSON payload for assertion convenience."""
        return json.loads(self.data.decode())


@pytest.fixture
def nats_message() -> type[MockNatsMessage]:
    """Return the ``MockNatsMessage`` factory class.

    Usage::

        msg = nats_message({"event": "gate_fail", "task_id": str(uuid4())})
        await handler._on_message(msg)
        assert msg.ack_called == 1
    """
    return MockNatsMessage


# ---------------------------------------------------------------------------
# Convenience: make_task_row available as a fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def task_row_factory() -> Any:
    """Return the ``make_task_row`` factory function as a fixture.

    Usage::

        def test_something(task_row_factory):
            row = task_row_factory(status=TaskPacketStatus.IN_PROGRESS)
    """
    return make_task_row


# ---------------------------------------------------------------------------
# Auth bypass helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def no_dashboard_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable dashboard bearer-token auth for tests by clearing the token."""
    from src import settings as settings_mod

    monkeypatch.setattr(settings_mod.settings, "dashboard_token", "")
