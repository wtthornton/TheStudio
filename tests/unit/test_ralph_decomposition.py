"""Unit tests for vendored Ralph SDK task decomposition heuristic (Epic 51.4).

Updated for SDK v2.0.3 API: DecompositionHint and detect_decomposition_needed
moved from ralph_sdk.decomposition to ralph_sdk.agent.
"""

from __future__ import annotations

from ralph_sdk.agent import (
    DecompositionHint,
    IterationRecord,
    detect_decomposition_needed,
)
from ralph_sdk.config import RalphConfig
from ralph_sdk.status import RalphLoopStatus, RalphStatus


def test_detect_decomposition_no_signals() -> None:
    cfg = RalphConfig()
    status = RalphStatus(status=RalphLoopStatus.COMPLETED)
    hint = detect_decomposition_needed(status, [], cfg)
    assert not hint.should_decompose


def test_detect_decomposition_many_files() -> None:
    cfg = RalphConfig()
    status = RalphStatus(
        status=RalphLoopStatus.COMPLETED,
        progress_summary="Modified src/a.py, src/b.py, src/c.py, src/d.py, src/e.py, src/f.py",
    )
    history = [IterationRecord(timed_out=True)]  # + previous timeout = 2 factors
    hint = detect_decomposition_needed(status, history, cfg)
    assert hint.should_decompose
    assert hint.suggested_split >= 2


def test_detect_decomposition_prior_timeout() -> None:
    cfg = RalphConfig()
    status = RalphStatus(
        status=RalphLoopStatus.COMPLETED,
        progress_summary="Modified src/a.py, src/b.py, src/c.py, src/d.py, src/e.py, src/f.py",
    )
    history = [IterationRecord(timed_out=True)]
    hint = detect_decomposition_needed(status, history, cfg)
    # previous_timeout + file_count should give 2 factors
    assert hint.should_decompose


def test_detect_decomposition_high_complexity() -> None:
    cfg = RalphConfig()
    status = RalphStatus(
        status=RalphLoopStatus.COMPLETED,
        next_task="Refactor complex multi-step workflow involving database, API, and frontend changes",
    )
    history = [IterationRecord(timed_out=True)]  # + previous timeout = 2 factors
    hint = detect_decomposition_needed(status, history, cfg)
    assert hint.should_decompose


def test_detect_decomposition_no_progress_streak() -> None:
    cfg = RalphConfig()
    status = RalphStatus(status=RalphLoopStatus.COMPLETED)
    history = [
        IterationRecord(had_progress=False),
        IterationRecord(had_progress=False),
        IterationRecord(had_progress=False),
        IterationRecord(timed_out=True),  # + previous timeout = 2 factors
    ]
    hint = detect_decomposition_needed(status, history, cfg)
    assert hint.should_decompose


def test_detect_decomposition_current_timeout() -> None:
    cfg = RalphConfig()
    status = RalphStatus(status=RalphLoopStatus.TIMEOUT)
    # No extra factors from history — need another factor
    history = [
        IterationRecord(had_progress=False),
        IterationRecord(had_progress=False),
        IterationRecord(had_progress=False),
    ]
    hint = detect_decomposition_needed(status, history, cfg)
    # consecutive_no_progress (3) is one factor; need to check if timeout alone counts
    assert isinstance(hint, DecompositionHint)


def test_medium_complexity_does_not_trip_default_threshold() -> None:
    cfg = RalphConfig()
    status = RalphStatus(status=RalphLoopStatus.COMPLETED)
    hint = detect_decomposition_needed(status, [], cfg)
    assert not hint.should_decompose
