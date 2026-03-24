"""Unit tests for vendored Ralph SDK task decomposition heuristic (Epic 51.4)."""

from __future__ import annotations

from ralph_sdk.config import RalphConfig
from ralph_sdk.decomposition import (
    DecompositionContext,
    DecompositionHint,
    detect_decomposition_needed,
)
from ralph_sdk.status import RalphLoopStatus, RalphStatus


def test_detect_decomposition_no_signals() -> None:
    cfg = RalphConfig()
    status = RalphStatus(status=RalphLoopStatus.IN_PROGRESS)
    hint = detect_decomposition_needed(status, cfg, DecompositionContext())
    assert hint == DecompositionHint(decompose=False, reasons=(), recommendation="")


def test_detect_decomposition_many_files() -> None:
    cfg = RalphConfig(decompose_files_threshold=5)
    status = RalphStatus(status=RalphLoopStatus.IN_PROGRESS)
    hint = detect_decomposition_needed(
        status,
        cfg,
        DecompositionContext(iteration_files_changed=5),
    )
    assert hint.decompose is True
    assert any("Many files changed" in r for r in hint.reasons)


def test_detect_decomposition_prior_timeout() -> None:
    cfg = RalphConfig()
    status = RalphStatus(status=RalphLoopStatus.IN_PROGRESS)
    hint = detect_decomposition_needed(
        status,
        cfg,
        DecompositionContext(prior_iteration_was_timeout=True),
    )
    assert hint.decompose is True
    assert any("Previous iteration timed out" in r for r in hint.reasons)


def test_detect_decomposition_high_complexity() -> None:
    cfg = RalphConfig(decompose_complexity_min=4)
    status = RalphStatus(status=RalphLoopStatus.IN_PROGRESS)
    hint = detect_decomposition_needed(
        status,
        cfg,
        DecompositionContext(complexity_band="high"),
    )
    assert hint.decompose is True
    assert any("High complexity" in r for r in hint.reasons)


def test_detect_decomposition_no_progress_streak() -> None:
    cfg = RalphConfig(decompose_no_progress_streak_min=3)
    status = RalphStatus(status=RalphLoopStatus.IN_PROGRESS)
    hint = detect_decomposition_needed(
        status,
        cfg,
        DecompositionContext(consecutive_no_progress=3),
    )
    assert hint.decompose is True
    assert any("No file changes" in r for r in hint.reasons)


def test_detect_decomposition_current_timeout() -> None:
    cfg = RalphConfig()
    status = RalphStatus(status=RalphLoopStatus.TIMEOUT)
    hint = detect_decomposition_needed(status, cfg, DecompositionContext())
    assert hint.decompose is True
    assert any("Current iteration timed out" in r for r in hint.reasons)


def test_medium_complexity_does_not_trip_default_threshold() -> None:
    cfg = RalphConfig(decompose_complexity_min=4)
    status = RalphStatus(status=RalphLoopStatus.IN_PROGRESS)
    hint = detect_decomposition_needed(
        status,
        cfg,
        DecompositionContext(complexity_band="medium"),
    )
    assert hint.decompose is False
