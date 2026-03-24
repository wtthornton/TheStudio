"""Unit tests for vendored Ralph SDK cost tracking (Epic 51.5)."""

from __future__ import annotations

import pytest
from ralph_sdk.config import RalphConfig
from ralph_sdk.cost_tracking import BudgetLevel, CostTracker


def test_cost_tracker_accumulates() -> None:
    cfg = RalphConfig(
        cost_input_usd_per_million_tokens=3.0,
        cost_output_usd_per_million_tokens=15.0,
    )
    ct = CostTracker(cfg)
    ct.record_iteration_cost(cfg.model, 1_000_000, 0)
    assert ct.get_session_cost() == pytest.approx(3.0)
    ct.record_iteration_cost(cfg.model, 0, 1_000_000)
    assert ct.get_session_cost() == pytest.approx(18.0)


def test_cost_tracker_reset() -> None:
    cfg = RalphConfig()
    ct = CostTracker(cfg)
    ct.record_iteration_cost(cfg.model, 1000, 0)
    ct.reset()
    assert ct.get_session_cost() == 0.0


def test_cost_tracker_per_model_override() -> None:
    cfg = RalphConfig(
        model="claude-sonnet-4-20250514",
        cost_rates_by_model={
            "claude-sonnet-4-20250514": {
                "input_per_million": 6.0,
                "output_per_million": 30.0,
            },
        },
    )
    ct = CostTracker(cfg)
    ct.record_iteration_cost("claude-sonnet-4-20250514", 500_000, 500_000)
    assert ct.get_session_cost() == pytest.approx(3.0 + 15.0)


def test_check_budget_alert_and_exceeded() -> None:
    cfg = RalphConfig()
    ct = CostTracker(cfg)
    ct.record_iteration_cost(cfg.model, 10_000_000, 0)  # $30 at default input rate
    r_ok = ct.check_budget(100.0, alert_threshold=0.8)
    assert r_ok.level == BudgetLevel.OK
    r_alert = ct.check_budget(40.0, alert_threshold=0.5)
    assert r_alert.level == BudgetLevel.ALERT
    r_ex = ct.check_budget(20.0, alert_threshold=0.99)
    assert r_ex.level == BudgetLevel.EXCEEDED
