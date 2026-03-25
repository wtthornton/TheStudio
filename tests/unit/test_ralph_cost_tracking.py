"""Unit tests for vendored Ralph SDK cost tracking (Epic 51.5).

Updated for SDK v2.0.3 API: CostTracker takes pricing dict, AlertLevel replaces BudgetLevel,
get_session_cost returns SessionCost model, check_budget takes only max_budget_usd.
"""

from __future__ import annotations

import pytest
from ralph_sdk.cost import AlertLevel, CostTracker, ModelPricing, DEFAULT_PRICING


def test_cost_tracker_accumulates() -> None:
    pricing = {
        "test-model": ModelPricing(input_per_1m=3.0, output_per_1m=15.0),
    }
    ct = CostTracker(pricing=pricing)
    ct.record_iteration("test-model", 1_000_000, 0)
    assert ct.get_session_cost().total_usd == pytest.approx(3.0)
    ct.record_iteration("test-model", 0, 1_000_000)
    assert ct.get_session_cost().total_usd == pytest.approx(18.0)


def test_cost_tracker_unknown_model_zero_cost() -> None:
    ct = CostTracker(pricing=DEFAULT_PRICING)
    ct.record_iteration("unknown-model", 1000, 1000)
    assert ct.get_session_cost().total_usd == 0.0
    assert ct.get_session_cost().iteration_count == 1


def test_cost_tracker_per_model_breakdown() -> None:
    pricing = {
        "claude-sonnet-4-6": ModelPricing(input_per_1m=3.0, output_per_1m=15.0),
    }
    ct = CostTracker(pricing=pricing)
    ct.record_iteration("claude-sonnet-4-6", 500_000, 500_000)
    session = ct.get_session_cost()
    assert session.total_usd == pytest.approx(1.5 + 7.5)
    assert len(session.by_model) == 1
    assert session.by_model[0].model == "claude-sonnet-4-6"


def test_check_budget_alert_levels() -> None:
    pricing = {
        "test-model": ModelPricing(input_per_1m=10.0, output_per_1m=0.0),
    }
    ct = CostTracker(pricing=pricing, budget_warning_pct=50.0, budget_critical_pct=80.0)
    # Spend $10 (1M input tokens at $10/1M)
    ct.record_iteration("test-model", 1_000_000, 0)

    # Well under budget
    r_ok = ct.check_budget(100.0)
    assert r_ok.alert_level == AlertLevel.NONE

    # Over 50% warning threshold
    r_warn = ct.check_budget(18.0)
    assert r_warn.alert_level == AlertLevel.WARNING

    # Over 80% critical threshold
    r_crit = ct.check_budget(12.0)
    assert r_crit.alert_level == AlertLevel.CRITICAL

    # Over 100% — exhausted
    r_ex = ct.check_budget(5.0)
    assert r_ex.alert_level == AlertLevel.EXHAUSTED
