"""Session cost tracking and budget checks (Epic 51 P1 / evaluation §1.4)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from ralph_sdk.config import RalphConfig


class BudgetLevel(StrEnum):
    """Budget check outcome relative to a caller-provided cap."""

    OK = "ok"
    ALERT = "alert"
    EXCEEDED = "exceeded"


class BudgetCheckResult(BaseModel, frozen=True):
    """Result of comparing accumulated session cost to a budget."""

    level: BudgetLevel
    session_cost_usd: float
    budget_usd: float
    utilization: float = 0.0


def _per_token_rates(
    model: str,
    config: RalphConfig,
) -> tuple[float, float]:
    """Return (usd_per_input_token, usd_per_output_token)."""
    overrides = config.cost_rates_by_model.get(model)
    if overrides:
        inp = float(overrides.get("input_per_million", config.cost_input_usd_per_million_tokens))
        out = float(overrides.get("output_per_million", config.cost_output_usd_per_million_tokens))
    else:
        inp = float(config.cost_input_usd_per_million_tokens)
        out = float(config.cost_output_usd_per_million_tokens)
    return inp / 1_000_000.0, out / 1_000_000.0


class CostTracker:
    """Accumulates per-iteration token costs for the current Ralph session."""

    def __init__(self, config: RalphConfig) -> None:
        self._config = config
        self._total_usd = 0.0

    def reset(self) -> None:
        """Clear accumulated cost (call at start of ``RalphAgent.run()``)."""
        self._total_usd = 0.0

    def record_iteration_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Add one iteration's cost using configured rates; returns marginal USD."""
        if not self._config.cost_tracking_enabled:
            return 0.0
        ri, ro = _per_token_rates(model, self._config)
        marginal = max(0, input_tokens) * ri + max(0, output_tokens) * ro
        self._total_usd += marginal
        return marginal

    def get_session_cost(self) -> float:
        """Cumulative USD for this session since last ``reset()``."""
        return round(self._total_usd, 8)

    def check_budget(self, budget_usd: float, alert_threshold: float = 0.8) -> BudgetCheckResult:
        """Compare session cost to *budget_usd* with an alert band below the cap."""
        cost = self.get_session_cost()
        if budget_usd <= 0:
            return BudgetCheckResult(
                level=BudgetLevel.OK,
                session_cost_usd=cost,
                budget_usd=budget_usd,
                utilization=0.0,
            )
        util = cost / budget_usd
        if cost > budget_usd:
            level = BudgetLevel.EXCEEDED
        elif util >= alert_threshold:
            level = BudgetLevel.ALERT
        else:
            level = BudgetLevel.OK
        return BudgetCheckResult(
            level=level,
            session_cost_usd=cost,
            budget_usd=budget_usd,
            utilization=round(util, 6),
        )
