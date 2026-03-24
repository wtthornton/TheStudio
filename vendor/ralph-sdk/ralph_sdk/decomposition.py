"""Task decomposition hints — CLI-style heuristic (Epic 51 / evaluation §1.3).

Mirrors the bash loop's oversized-task detection: many files touched in one
iteration, repeated timeouts, high complexity band, or consecutive iterations
with no file changes.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ralph_sdk.config import RalphConfig
from ralph_sdk.status import RalphLoopStatus, RalphStatus


def _band_to_score(band: str) -> int | None:
    """Map TaskInput.complexity_band (or payload) to a 1-5 score for thresholds."""
    b = (band or "").strip().lower()
    if b == "high":
        return 5
    if b == "medium":
        return 3
    if b == "low":
        return 2
    return None


class DecompositionContext(BaseModel, frozen=True):
    """Per-iteration signals; pass from RalphAgent (not all are on RalphStatus)."""

    iteration_files_changed: int = Field(default=0, ge=0)
    prior_iteration_was_timeout: bool = False
    complexity_band: str = "unknown"
    consecutive_no_progress: int = Field(default=0, ge=0)


class DecompositionHint(BaseModel, frozen=True):
    """Structured recommendation when a task may be too large for one loop."""

    decompose: bool
    reasons: tuple[str, ...] = ()
    recommendation: str = ""


def detect_decomposition_needed(
    status: RalphStatus,
    config: RalphConfig,
    context: DecompositionContext | None = None,
) -> DecompositionHint:
    """Return whether the current iteration suggests splitting the task.

    Uses the four-factor heuristic from ``docs/ralph-sdk-upgrade-evaluation.md``:
    file count, prior timeout, complexity score ≥ configured minimum, and
    consecutive no-progress iterations.

    When ``context`` is omitted, only conditions inferable from ``status`` alone
    are considered (e.g. this iteration timed out).
    """
    ctx = context or DecompositionContext()
    reasons: list[str] = []

    if ctx.iteration_files_changed >= config.decompose_files_threshold:
        reasons.append(
            f"Many files changed in one iteration ({ctx.iteration_files_changed} ≥ "
            f"{config.decompose_files_threshold})"
        )

    if ctx.prior_iteration_was_timeout:
        reasons.append("Previous iteration timed out")

    score = _band_to_score(ctx.complexity_band)
    if score is not None and score >= config.decompose_complexity_min:
        reasons.append(f"High complexity (score {score} ≥ {config.decompose_complexity_min})")

    if ctx.consecutive_no_progress >= config.decompose_no_progress_streak_min:
        reasons.append(
            f"No file changes for {ctx.consecutive_no_progress} consecutive "
            f"iterations (≥ {config.decompose_no_progress_streak_min})"
        )

    st = status.status
    if isinstance(st, RalphLoopStatus):
        timed_out_now = st == RalphLoopStatus.TIMEOUT
    else:
        timed_out_now = str(st).upper() == "TIMEOUT"
    if timed_out_now:
        reasons.append("Current iteration timed out")

    if not reasons:
        return DecompositionHint(decompose=False, reasons=(), recommendation="")

    joined = "; ".join(reasons)
    rec = "Consider splitting this task into smaller stories or epics: " + joined + "."
    return DecompositionHint(decompose=True, reasons=tuple(reasons), recommendation=rec)
