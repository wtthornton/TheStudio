"""Drift detection — identifies improving, stable, or declining weight trends.

Architecture reference: thestudioarc/06-reputation-engine.md lines 90-98

Drift rules:
- Rolling window (default 10 outcomes)
- improving: trend slope > +0.05
- stable: trend slope between -0.05 and +0.05
- declining: trend slope < -0.05
"""

import logging
from uuid import UUID

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# Default drift configuration
DEFAULT_WINDOW_SIZE = 10  # Rolling window for drift detection
DEFAULT_IMPROVING_THRESHOLD = 0.05  # Slope threshold for improving
DEFAULT_DECLINING_THRESHOLD = -0.05  # Slope threshold for declining


class DriftDirection:
    """Drift direction enum (string constants for compatibility)."""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


class DriftResult(BaseModel):
    """Result of drift computation."""

    expert_id: UUID
    context_key: str
    direction: str  # DriftDirection value
    slope: float
    window_size: int
    sample_count: int


# Store for drift results
_drift_results: list[DriftResult] = []


def clear() -> None:
    """Clear stores (for testing)."""
    _drift_results.clear()


def get_drift_results() -> list[DriftResult]:
    """Return all drift results."""
    return list(_drift_results)


def compute_drift(
    recent_weights: list[float],
    window_size: int = DEFAULT_WINDOW_SIZE,
    improving_threshold: float = DEFAULT_IMPROVING_THRESHOLD,
    declining_threshold: float = DEFAULT_DECLINING_THRESHOLD,
) -> str:
    """Compute drift direction from recent weight history.

    Per DoD:
    - Rolling window (default 10 outcomes)
    - improving: trend slope > +0.05
    - stable: trend slope between -0.05 and +0.05
    - declining: trend slope < -0.05

    Args:
        recent_weights: List of recent weight values (oldest first).
        window_size: Rolling window size.
        improving_threshold: Slope threshold for improving.
        declining_threshold: Slope threshold for declining.

    Returns:
        DriftDirection value (improving, stable, declining).
    """
    if len(recent_weights) < 3:
        return DriftDirection.STABLE

    # Take the most recent window_size weights
    window = recent_weights[-window_size:]
    if len(window) < 3:
        return DriftDirection.STABLE

    # Compute linear regression slope
    slope = _compute_slope(window)

    if slope > improving_threshold:
        return DriftDirection.IMPROVING
    if slope < declining_threshold:
        return DriftDirection.DECLINING
    return DriftDirection.STABLE


def _compute_slope(values: list[float]) -> float:
    """Compute linear regression slope for a list of values.

    Uses simple linear regression: y = mx + b
    Returns m (slope).
    """
    n = len(values)
    if n < 2:
        return 0.0

    # x values are indices (0, 1, 2, ...)
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n

    numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 0.0

    return numerator / denominator


def compute_drift_for_expert(
    expert_id: UUID,
    context_key: str,
    weight_history: list[float],
    window_size: int = DEFAULT_WINDOW_SIZE,
) -> DriftResult:
    """Compute drift for a specific expert and record the result.

    Args:
        expert_id: Expert UUID.
        context_key: Context key for the weight.
        weight_history: Full weight history.
        window_size: Rolling window size.

    Returns:
        DriftResult with direction and slope.
    """
    window = weight_history[-window_size:] if len(weight_history) > window_size else weight_history
    slope = _compute_slope(window) if len(window) >= 2 else 0.0
    direction = compute_drift(weight_history, window_size)

    result = DriftResult(
        expert_id=expert_id,
        context_key=context_key,
        direction=direction,
        slope=slope,
        window_size=len(window),
        sample_count=len(weight_history),
    )

    _drift_results.append(result)
    return result


def compute_drift_score(
    weight_history: list[float], window_size: int = DEFAULT_WINDOW_SIZE,
) -> float:
    """Compute a drift score (-1 to +1) from weight history.

    Positive = improving, negative = declining.
    Magnitude indicates strength of trend.
    """
    if len(weight_history) < 3:
        return 0.0

    window = weight_history[-window_size:]
    slope = _compute_slope(window)

    # Normalize to approximately -1 to +1
    # Slopes are typically small (0.01 - 0.10), so scale up
    normalized = slope * 10.0
    return max(-1.0, min(1.0, normalized))
