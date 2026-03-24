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


# ---------------------------------------------------------------------------
# Epic 51-git: git-unavailable hardening tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stall_detector_git_unavailable_skips_fast_trip() -> None:
    """When git is unavailable the fast-trip streak must NOT accumulate.

    Without this guard a missing git binary would return files_changed_count=0
    every iteration and cause a spurious fast-trip stall within 3 loops even
    though the agent may be making real progress.
    """
    backend = NullStateBackend()
    cb = CircuitBreaker(backend)
    # fast_trip_max=2 so the trip would fire on the 2nd iteration normally
    det = StallDetector(cb, fast_trip_max=2, fast_trip_max_seconds=30.0)

    for _ in range(5):
        reason = await det.evaluate_after_iteration(
            iteration_duration_sec=5.0,   # fast iteration
            files_changed_count=0,        # git returned nothing
            tests_status="IN_PROGRESS",
            timed_out=False,
            cli_had_error=False,
            git_unavailable=True,         # git binary was missing
        )
        assert reason is None, "Fast-trip should not fire when git is unavailable"

    st = await cb.get_state()
    assert st["state"] == "CLOSED", "Circuit should stay closed when git is unavailable"


@pytest.mark.asyncio
async def test_stall_detector_fast_trip_still_fires_when_git_available() -> None:
    """Fast-trip must still fire after the threshold when git IS available."""
    backend = NullStateBackend()
    cb = CircuitBreaker(backend)
    det = StallDetector(cb, fast_trip_max=3, fast_trip_max_seconds=30.0)

    for i in range(3):
        reason = await det.evaluate_after_iteration(
            iteration_duration_sec=5.0,
            files_changed_count=0,
            tests_status="IN_PROGRESS",
            timed_out=False,
            cli_had_error=False,
            git_unavailable=False,
        )
        if i < 2:
            assert reason is None
        else:
            assert reason is not None
            assert "Fast-trip" in reason

    st = await cb.get_state()
    assert st["state"] == "OPEN"


@pytest.mark.asyncio
async def test_stall_detector_git_unavailable_does_not_reset_deferred_streak() -> None:
    """git_unavailable should NOT reset the deferred-test streak.

    A missing git binary is unrelated to deferred tests; the deferred streak
    must continue accumulating so the deferred-test stall can still fire.
    """
    backend = NullStateBackend()
    cb = CircuitBreaker(backend)
    det = StallDetector(cb, deferred_test_max=3, fast_trip_max=99)

    # Two deferred iterations with git unavailable
    for _ in range(2):
        await det.evaluate_after_iteration(
            iteration_duration_sec=60.0,
            files_changed_count=0,
            tests_status="DEFERRED",
            timed_out=False,
            cli_had_error=False,
            git_unavailable=True,
        )

    # Third iteration tips the deferred-test stall
    reason = await det.evaluate_after_iteration(
        iteration_duration_sec=60.0,
        files_changed_count=0,
        tests_status="DEFERRED",
        timed_out=False,
        cli_had_error=False,
        git_unavailable=True,
    )
    assert reason is not None
    assert "Deferred" in reason


@pytest.mark.asyncio
async def test_stall_detector_git_unavailable_resets_fast_trip_streak() -> None:
    """A single git_unavailable iteration resets any in-progress fast-trip streak."""
    backend = NullStateBackend()
    cb = CircuitBreaker(backend)
    det = StallDetector(cb, fast_trip_max=3, fast_trip_max_seconds=30.0)

    # Build up 2 fast-trip streak iterations
    for _ in range(2):
        await det.evaluate_after_iteration(
            iteration_duration_sec=5.0,
            files_changed_count=0,
            tests_status="IN_PROGRESS",
            timed_out=False,
            cli_had_error=False,
            git_unavailable=False,
        )

    # One iteration where git was unavailable — streak must reset
    await det.evaluate_after_iteration(
        iteration_duration_sec=5.0,
        files_changed_count=0,
        tests_status="IN_PROGRESS",
        timed_out=False,
        cli_had_error=False,
        git_unavailable=True,
    )

    # Next normal iteration should NOT trip (streak was reset to 0 → now 1)
    reason = await det.evaluate_after_iteration(
        iteration_duration_sec=5.0,
        files_changed_count=0,
        tests_status="IN_PROGRESS",
        timed_out=False,
        cli_had_error=False,
        git_unavailable=False,
    )
    assert reason is None
    st = await cb.get_state()
    assert st["state"] == "CLOSED"
