"""Admin API routes for readiness gate metrics and configuration.

Story 16.7: Admin API — Readiness Metrics and Configuration.

Provides 4 endpoints:
- GET /admin/readiness/metrics — pass/hold/escalate counts
- GET /admin/readiness/calibration — current weights, miss rate
- PUT /admin/readiness/thresholds — update per-repo thresholds
- POST /admin/readiness/calibrate — trigger on-demand calibration
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.admin.rbac import Permission, require_permission
from src.readiness.calibrator import CalibrationResult, get_calibrator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/readiness", tags=["admin", "readiness"])


# --- Response Models ---


class ReadinessMetricsResponse(BaseModel):
    """Response for readiness gate metrics."""

    repo_id: str | None = None
    total_evaluations: int = 0
    pass_count: int = 0
    hold_count: int = 0
    escalate_count: int = 0
    average_score: float = 0.0
    top_missing_dimensions: list[dict[str, int]] = Field(default_factory=list)


class CalibrationInfoResponse(BaseModel):
    """Response for calibration status."""

    repo_id: str | None = None
    current_weights: dict[str, float] = Field(default_factory=dict)
    miss_count: int = 0
    miss_rate: float = 0.0
    recent_adjustments: list[dict[str, float]] = Field(default_factory=list)
    last_calibration_samples: int = 0


class ThresholdUpdateRequest(BaseModel):
    """Request body for updating readiness thresholds."""

    pass_threshold: float | None = Field(None, ge=0.0, le=1.0)
    hold_threshold: float | None = Field(None, ge=0.0, le=1.0)


class ThresholdUpdateResponse(BaseModel):
    """Response for threshold update."""

    repo_id: str | None = None
    updated: bool = True
    pass_threshold: float = 0.0
    hold_threshold: float = 0.0


class CalibrateResponse(BaseModel):
    """Response for on-demand calibration trigger."""

    samples_analyzed: int = 0
    adjustments_made: dict[str, float] = Field(default_factory=dict)
    previous_weights: dict[str, float] = Field(default_factory=dict)
    new_weights: dict[str, float] = Field(default_factory=dict)
    skipped_reason: str | None = None


# --- In-memory stores (production: DB queries) ---

_metrics_store: dict[str, dict] = {}
_threshold_overrides: dict[str, dict[str, float]] = {}


def record_gate_result(
    repo_id: str,
    decision: str,
    score: float,
    missing_dimensions: list[str],
) -> None:
    """Record a gate evaluation result for metrics.

    Called by the readiness activity after each evaluation.
    """
    if repo_id not in _metrics_store:
        _metrics_store[repo_id] = {
            "total": 0,
            "pass": 0,
            "hold": 0,
            "escalate": 0,
            "scores": [],
            "missing_dims": {},
        }

    store = _metrics_store[repo_id]
    store["total"] += 1

    if decision in ("pass", "hold", "escalate"):
        store[decision] += 1

    store["scores"].append(score)

    for dim in missing_dimensions:
        store["missing_dims"][dim] = store["missing_dims"].get(dim, 0) + 1


def get_metrics(repo_id: str | None = None) -> ReadinessMetricsResponse:
    """Get aggregated metrics for a repo or across all repos."""
    if repo_id and repo_id in _metrics_store:
        store = _metrics_store[repo_id]
    elif repo_id:
        return ReadinessMetricsResponse(repo_id=repo_id)
    else:
        # Aggregate across all repos
        store = {"total": 0, "pass": 0, "hold": 0, "escalate": 0, "scores": [], "missing_dims": {}}
        for repo_store in _metrics_store.values():
            store["total"] += repo_store["total"]
            store["pass"] += repo_store["pass"]
            store["hold"] += repo_store["hold"]
            store["escalate"] += repo_store["escalate"]
            store["scores"].extend(repo_store["scores"])
            for dim, count in repo_store["missing_dims"].items():
                store["missing_dims"][dim] = store["missing_dims"].get(dim, 0) + count

    scores = store["scores"]
    avg_score = sum(scores) / len(scores) if scores else 0.0

    # Top missing dimensions sorted by count
    dims_sorted = sorted(store["missing_dims"].items(), key=lambda x: x[1], reverse=True)
    top_dims = [{dim: count} for dim, count in dims_sorted[:5]]

    return ReadinessMetricsResponse(
        repo_id=repo_id,
        total_evaluations=store["total"],
        pass_count=store["pass"],
        hold_count=store["hold"],
        escalate_count=store["escalate"],
        average_score=round(avg_score, 3),
        top_missing_dimensions=top_dims,
    )


def clear_metrics() -> None:
    """Clear metrics and threshold stores (for testing)."""
    _metrics_store.clear()
    _threshold_overrides.clear()


# --- Endpoints ---


@router.get(
    "/metrics",
    response_model=ReadinessMetricsResponse,
    dependencies=[Depends(require_permission(Permission.VIEW_METRICS))],
)
async def readiness_metrics(
    repo_id: Annotated[str | None, Query(description="Filter by repository")] = None,
) -> ReadinessMetricsResponse:
    """Get readiness gate metrics: pass/hold/escalate counts, average scores."""
    return get_metrics(repo_id)


@router.get(
    "/calibration",
    response_model=CalibrationInfoResponse,
    dependencies=[Depends(require_permission(Permission.VIEW_METRICS))],
)
async def readiness_calibration_info(
    repo_id: Annotated[str | None, Query(description="Filter by repository")] = None,
) -> CalibrationInfoResponse:
    """Get current calibration state: weights, miss rate, recent adjustments."""
    calibrator = get_calibrator()
    weights = calibrator.get_weights(repo_id)
    miss_records = calibrator.get_miss_records(repo_id)
    history = calibrator.get_calibration_history()

    metrics = get_metrics(repo_id)
    total = metrics.total_evaluations
    miss_rate = len(miss_records) / total if total > 0 else 0.0

    recent_adjustments = []
    for result in history[-3:]:
        if result.adjustments_made:
            recent_adjustments.append(result.adjustments_made)

    last_samples = history[-1].samples_analyzed if history else 0

    return CalibrationInfoResponse(
        repo_id=repo_id,
        current_weights=weights,
        miss_count=len(miss_records),
        miss_rate=round(miss_rate, 4),
        recent_adjustments=recent_adjustments,
        last_calibration_samples=last_samples,
    )


@router.put(
    "/thresholds",
    response_model=ThresholdUpdateResponse,
    dependencies=[Depends(require_permission(Permission.MANAGE_SETTINGS))],
)
async def update_readiness_thresholds(
    body: ThresholdUpdateRequest,
    repo_id: Annotated[str | None, Query(description="Repository to update")] = None,
) -> ThresholdUpdateResponse:
    """Update readiness gate threshold overrides for a repo."""
    key = repo_id or "__global__"
    current = _threshold_overrides.get(key, {"pass_threshold": 0.5, "hold_threshold": 0.3})

    if body.pass_threshold is not None:
        current["pass_threshold"] = body.pass_threshold
    if body.hold_threshold is not None:
        current["hold_threshold"] = body.hold_threshold

    _threshold_overrides[key] = current

    logger.info(
        "readiness.thresholds.updated",
        extra={
            "repo_id": repo_id,
            "pass_threshold": current["pass_threshold"],
            "hold_threshold": current["hold_threshold"],
        },
    )

    return ThresholdUpdateResponse(
        repo_id=repo_id,
        updated=True,
        pass_threshold=current["pass_threshold"],
        hold_threshold=current["hold_threshold"],
    )


@router.post(
    "/calibrate",
    response_model=CalibrateResponse,
    dependencies=[Depends(require_permission(Permission.MANAGE_SETTINGS))],
)
async def trigger_calibration(
    repo_id: Annotated[str | None, Query(description="Repository to calibrate")] = None,
) -> CalibrateResponse:
    """Trigger on-demand readiness calibration."""
    calibrator = get_calibrator()
    result: CalibrationResult = calibrator.calibrate(repo_id)

    return CalibrateResponse(
        samples_analyzed=result.samples_analyzed,
        adjustments_made=result.adjustments_made,
        previous_weights=result.previous_weights,
        new_weights=result.new_weights,
        skipped_reason=result.skipped_reason,
    )
