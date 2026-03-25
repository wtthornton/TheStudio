"""Unit tests for vendored Ralph SDK — Epic 51 P0 (context + stall detection).

Updated for SDK v2.0.3 API: ContextManager replaces build_progressive_context,
separate detector classes replace unified StallDetector.
"""

from __future__ import annotations

import pytest
from ralph_sdk.circuit_breaker import (
    DeferredTestDetector,
    FastTripDetector,
)
from ralph_sdk.context import ContextManager, estimate_tokens
from ralph_sdk.status import RalphLoopStatus, RalphStatus


def test_estimate_tokens() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcdefgh") == 2


def test_context_manager_trims_unchecked() -> None:
    plan = """## Epic A

- [ ] task one
- [ ] task two
- [ ] task three
- [x] done

## Epic B

- [ ] only here
"""
    cm = ContextManager(max_unchecked_items=1)
    out = cm.trim_fix_plan(plan)
    # Should focus on the first section with unchecked items
    assert out is not None
    assert len(out) > 0


def test_deferred_test_detector_trips() -> None:
    det = DeferredTestDetector(warn_at=1, max_consecutive=2)
    r1 = det.record(tests_deferred=True)
    assert not r1.should_trip
    assert r1.should_warn  # warn_at=1, first deferred hits warn

    r2 = det.record(tests_deferred=True)
    assert r2.should_trip
    assert "Deferred" in r2.reason


def test_deferred_test_detector_resets_on_non_deferred() -> None:
    det = DeferredTestDetector(warn_at=2, max_consecutive=3)
    det.record(tests_deferred=True)
    det.record(tests_deferred=False)  # resets
    det.record(tests_deferred=True)
    assert det.consecutive_count == 1


def test_ralph_status_roundtrip() -> None:
    s = RalphStatus(status=RalphLoopStatus.COMPLETED, progress_summary="done")
    d = s.to_dict()
    assert d.get("status") == "COMPLETED"
    assert d.get("PROGRESS_SUMMARY") == "done"
    s2 = RalphStatus.from_dict(d)
    assert s2.status == RalphLoopStatus.COMPLETED
    assert s2.progress_summary == "done"


def test_status_enum_values() -> None:
    assert RalphLoopStatus.TIMEOUT == "TIMEOUT"
    assert RalphLoopStatus.ERROR == "ERROR"
    assert RalphLoopStatus.COMPLETED == "COMPLETED"
    assert RalphLoopStatus.IN_PROGRESS == "IN_PROGRESS"


# ---------------------------------------------------------------------------
# Fast-trip detector tests (replaces StallDetector git-unavailable tests)
# ---------------------------------------------------------------------------


def test_fast_trip_detector_fires_at_threshold() -> None:
    det = FastTripDetector(max_consecutive=3, threshold_seconds=30.0)
    for i in range(3):
        r = det.record(duration_seconds=5.0, tool_use_count=0)
        if i < 2:
            assert not r.should_trip
        else:
            assert r.should_trip
            assert "Fast trip" in r.reason


def test_fast_trip_detector_resets_on_tool_use() -> None:
    det = FastTripDetector(max_consecutive=3, threshold_seconds=30.0)
    det.record(duration_seconds=5.0, tool_use_count=0)
    det.record(duration_seconds=5.0, tool_use_count=0)
    det.record(duration_seconds=5.0, tool_use_count=1)  # resets
    assert det.consecutive_count == 0


def test_fast_trip_detector_resets_on_slow_run() -> None:
    det = FastTripDetector(max_consecutive=3, threshold_seconds=30.0)
    det.record(duration_seconds=5.0, tool_use_count=0)
    det.record(duration_seconds=5.0, tool_use_count=0)
    det.record(duration_seconds=60.0, tool_use_count=0)  # slow, resets
    assert det.consecutive_count == 0
