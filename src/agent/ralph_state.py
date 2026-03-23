"""PostgresStateBackend — persistent state for RalphAgent via ralph_agent_state table.

Implements the 12-method ``RalphStateBackend`` protocol from the Ralph SDK using
upsert/select on the ``ralph_agent_state`` table (added in migration 048).

Each state key is stored as an independent row keyed by ``(taskpacket_id, key_name)``.
All reads return a safe default when no row exists; all writes are atomic upserts.

Epic reference: Epic 43 Story 43.7 — PostgresStateBackend
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text

from src.db.connection import get_async_session

logger = logging.getLogger(__name__)

__all__ = ["PostgresStateBackend"]

# ---------------------------------------------------------------------------
# Key constants — must fit within VARCHAR(64) in ralph_agent_state.key_name
# ---------------------------------------------------------------------------

_KEY_STATUS = "status"
_KEY_CIRCUIT_BREAKER = "circuit_breaker"
_KEY_CALL_COUNT = "call_count"
_KEY_LAST_RESET = "last_reset"
_KEY_SESSION_ID = "session_id"
_KEY_FIX_PLAN = "fix_plan"

# ---------------------------------------------------------------------------
# Upsert SQL (PostgreSQL ON CONFLICT)
# ---------------------------------------------------------------------------

_UPSERT_SQL = text(
    """
    INSERT INTO ralph_agent_state (taskpacket_id, key_name, value_json, updated_at)
    VALUES (:tid, :key, :value, NOW())
    ON CONFLICT (taskpacket_id, key_name)
    DO UPDATE SET value_json = EXCLUDED.value_json, updated_at = NOW()
    """
)

_SELECT_SQL = text(
    """
    SELECT value_json
    FROM ralph_agent_state
    WHERE taskpacket_id = :tid
      AND key_name = :key
    """
)

_SELECT_WITH_TS_SQL = text(
    """
    SELECT value_json, updated_at
    FROM ralph_agent_state
    WHERE taskpacket_id = :tid
      AND key_name = :key
    """
)

_DELETE_SQL = text(
    """
    DELETE FROM ralph_agent_state
    WHERE taskpacket_id = :tid
      AND key_name = :key
    """
)


class PostgresStateBackend:
    """RalphStateBackend implementation backed by PostgreSQL.

    All 12 protocol methods are implemented as async upsert/select operations
    on the ``ralph_agent_state`` table.  Each method opens a short-lived
    session via ``get_async_session()`` and commits immediately, so no
    persistent session is held between calls.

    Args:
        taskpacket_id: UUID of the TaskPacket this backend is scoped to.
            All reads and writes are isolated to this taskpacket_id.
    """

    def __init__(self, taskpacket_id: UUID) -> None:
        self._taskpacket_id = taskpacket_id

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _read_raw(self, key: str) -> str | None:
        """Return raw ``value_json`` string for *key*, or ``None`` if absent."""
        async with get_async_session() as session:
            result = await session.execute(
                _SELECT_SQL, {"tid": self._taskpacket_id, "key": key}
            )
            row = result.fetchone()
            return str(row[0]) if row else None

    async def _write_raw(self, key: str, value: str) -> None:
        """Upsert *value* as the ``value_json`` for *key*."""
        async with get_async_session() as session:
            await session.execute(
                _UPSERT_SQL,
                {"tid": self._taskpacket_id, "key": key, "value": value},
            )
            await session.commit()

    async def _read_json(self, key: str) -> dict[str, Any]:
        """Read a JSON-encoded dict; return ``{}`` when absent."""
        raw = await self._read_raw(key)
        if raw is None:
            return {}
        loaded: dict[str, Any] = json.loads(raw)
        return loaded

    async def _write_json(self, key: str, data: dict[str, Any]) -> None:
        """Write a dict as JSON."""
        await self._write_raw(key, json.dumps(data))

    async def _read_int(self, key: str) -> int:
        """Read an int; return ``0`` when absent."""
        raw = await self._read_raw(key)
        if raw is None:
            return 0
        return int(raw)

    async def _write_int(self, key: str, value: int) -> None:
        """Write an int as its string representation."""
        await self._write_raw(key, str(value))

    async def _read_str(self, key: str) -> str:
        """Read a string; return ``""`` when absent."""
        raw = await self._read_raw(key)
        return raw if raw is not None else ""

    # ------------------------------------------------------------------
    # Status (2 methods)
    # ------------------------------------------------------------------

    async def read_status(self) -> dict[str, Any]:
        """Read agent status (status.json equivalent)."""
        return await self._read_json(_KEY_STATUS)

    async def write_status(self, data: dict[str, Any]) -> None:
        """Write agent status atomically."""
        await self._write_json(_KEY_STATUS, data)

    # ------------------------------------------------------------------
    # Circuit breaker (2 methods)
    # ------------------------------------------------------------------

    async def read_circuit_breaker(self) -> dict[str, Any]:
        """Read circuit breaker state."""
        return await self._read_json(_KEY_CIRCUIT_BREAKER)

    async def write_circuit_breaker(self, data: dict[str, Any]) -> None:
        """Write circuit breaker state atomically."""
        await self._write_json(_KEY_CIRCUIT_BREAKER, data)

    # ------------------------------------------------------------------
    # Rate limiting — call count (2 methods)
    # ------------------------------------------------------------------

    async def read_call_count(self) -> int:
        """Read the current API call counter; returns 0 when unset."""
        return await self._read_int(_KEY_CALL_COUNT)

    async def write_call_count(self, count: int) -> None:
        """Write the current API call counter."""
        await self._write_int(_KEY_CALL_COUNT, count)

    # ------------------------------------------------------------------
    # Rate limiting — last reset timestamp (2 methods)
    # ------------------------------------------------------------------

    async def read_last_reset(self) -> int:
        """Read the Unix timestamp of the last call-count reset; returns 0."""
        return await self._read_int(_KEY_LAST_RESET)

    async def write_last_reset(self, timestamp: int) -> None:
        """Write the Unix timestamp of the last call-count reset."""
        await self._write_int(_KEY_LAST_RESET, timestamp)

    # ------------------------------------------------------------------
    # Session continuity (2 methods)
    # ------------------------------------------------------------------

    async def read_session_id(self) -> str:
        """Read the Claude session ID for session continuity; returns ''."""
        return await self._read_str(_KEY_SESSION_ID)

    async def write_session_id(self, session_id: str) -> None:
        """Write the Claude session ID."""
        await self._write_raw(_KEY_SESSION_ID, session_id)

    # ------------------------------------------------------------------
    # Fix plan (2 methods)
    # ------------------------------------------------------------------

    async def read_fix_plan(self) -> str:
        """Read the fix plan content; returns ''."""
        return await self._read_str(_KEY_FIX_PLAN)

    async def write_fix_plan(self, content: str) -> None:
        """Write the fix plan content."""
        await self._write_raw(_KEY_FIX_PLAN, content)

    # ------------------------------------------------------------------
    # Session TTL (Story 43.8)
    # ------------------------------------------------------------------

    async def clear_session_if_stale(self, ttl_seconds: int = 7200) -> bool:
        """Discard the stored session ID if it is older than *ttl_seconds*.

        Reads the ``updated_at`` timestamp for the ``session_id`` row and
        deletes the row when the session has expired.  Called by
        ``_implement_ralph()`` before constructing a ``RalphAgent`` so that
        stale Claude session IDs are not accidentally resumed.

        Args:
            ttl_seconds: Maximum age of a session ID in seconds.
                Defaults to 7200 (2 hours).

        Returns:
            ``True`` if a stale session was found and cleared, ``False``
            otherwise (including when no session ID is stored at all).
        """
        async with get_async_session() as session:
            result = await session.execute(
                _SELECT_WITH_TS_SQL,
                {"tid": self._taskpacket_id, "key": _KEY_SESSION_ID},
            )
            row = result.fetchone()

        if row is None:
            return False  # nothing stored — nothing to clear

        _value_json, updated_at = row

        # updated_at may be a timezone-aware or naive datetime from the DB driver
        if updated_at is None:
            return False

        now = datetime.now(tz=UTC)
        if updated_at.tzinfo is None:
            # Treat naive timestamps as UTC (matches the table's TIMESTAMPTZ default)
            updated_at = updated_at.replace(tzinfo=UTC)

        age_seconds = (now - updated_at).total_seconds()
        if age_seconds <= ttl_seconds:
            return False  # session is still fresh

        # Session is stale — delete it
        async with get_async_session() as session:
            await session.execute(
                _DELETE_SQL,
                {"tid": self._taskpacket_id, "key": _KEY_SESSION_ID},
            )
            await session.commit()

        logger.info(
            "Discarded stale Ralph session_id for taskpacket %s (age=%.0fs, ttl=%ds)",
            self._taskpacket_id,
            age_seconds,
            ttl_seconds,
        )
        return True
