"""Unit tests for vendored Ralph SDK — Epic 51 P0 (context + stall detection)."""

from __future__ import annotations

import pytest
from ralph_sdk.circuit_breaker import CircuitBreaker, StallDetector
from ralph_sdk.context_management import build_progressive_context, estimate_tokens
from ralph_sdk.state import NullStateBackend
from ralph_sdk.status import RalphLoopStatus, RalphStatus


def test_estimate_tokens() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcdefgh") == 2


def test_build_progressive_context_truncates_unchecked() -> None:
    plan = """## Epic A

- [ ] task one
- [ ] task two
- [ ] task three
- [x] done

## Epic B

- [ ] only here
"""
    out = build_progressive_context(plan, max_items=1)
    assert "Epic B" in out or "only here" in out
    assert "omitted" in out.lower() or "Earlier" in out


@pytest.mark.asyncio
async def test_stall_detector_deferred_trips() -> None:
    backend = NullStateBackend()
    cb = CircuitBreaker(backend)
    det = StallDetector(cb, deferred_test_max=2)
    assert (
        await det.evaluate_after_iteration(
            iteration_duration_sec=60.0,
            files_changed_count=1,
            tests_status="DEFERRED",
            timed_out=False,
            cli_had_error=False,
        )
        is None
    )
    reason = await det.evaluate_after_iteration(
        iteration_duration_sec=60.0,
        files_changed_count=1,
        tests_status="DEFERRED",
        timed_out=False,
        cli_had_error=False,
    )
    assert reason is not None
    assert "Deferred" in reason
    st = await cb.get_state()
    assert st["state"] == "OPEN"


@pytest.mark.asyncio
async def test_stall_detector_resets_on_cli_error() -> None:
    backend = NullStateBackend()
    cb = CircuitBreaker(backend)
    det = StallDetector(cb, deferred_test_max=2)
    await det.evaluate_after_iteration(
        iteration_duration_sec=60.0,
        files_changed_count=0,
        tests_status="DEFERRED",
        timed_out=False,
        cli_had_error=False,
    )
    await det.evaluate_after_iteration(
        iteration_duration_sec=60.0,
        files_changed_count=0,
        tests_status="UNKNOWN",
        timed_out=False,
        cli_had_error=True,
    )
    await det.evaluate_after_iteration(
        iteration_duration_sec=60.0,
        files_changed_count=0,
        tests_status="DEFERRED",
        timed_out=False,
        cli_had_error=False,
    )
    st = await cb.get_state()
    assert st["state"] == "CLOSED"


def test_ralph_status_tests_status_roundtrip() -> None:
    s = RalphStatus(tests_status="DEFERRED")
    d = s.to_dict()
    assert d.get("TESTS_STATUS") == "DEFERRED"
    s2 = RalphStatus.from_dict(d)
    assert s2.tests_status == "DEFERRED"


def test_status_is_error_helper_via_enum() -> None:
    from ralph_sdk.agent import _status_is_error, _status_is_timeout

    assert _status_is_timeout(RalphStatus(status=RalphLoopStatus.TIMEOUT))
    assert _status_is_error(RalphStatus(status=RalphLoopStatus.ERROR))
    assert not _status_is_error(RalphStatus(status=RalphLoopStatus.COMPLETED))
