"""Pydantic model validation tests for budget config models.

Tests cover:
- BudgetConfigRead required/optional fields, from_attributes ORM loading
- BudgetConfigUpdate all-optional schema, ge/le constraints, range validation
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from typing import Any

import pytest
from pydantic import ValidationError

from src.dashboard.models.budget_config import (
    BudgetConfigRead,
    BudgetConfigUpdate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(UTC)


def _make_config_row(**overrides: Any) -> MagicMock:
    """Return a MagicMock suitable for BudgetConfigRead.model_validate."""
    row = MagicMock()
    row.daily_spend_warning = overrides.get("daily_spend_warning", None)
    row.weekly_budget_cap = overrides.get("weekly_budget_cap", None)
    row.per_task_warning = overrides.get("per_task_warning", None)
    row.pause_on_budget_exceeded = overrides.get("pause_on_budget_exceeded", False)
    row.model_downgrade_on_approach = overrides.get("model_downgrade_on_approach", False)
    row.downgrade_threshold_percent = overrides.get("downgrade_threshold_percent", 80.0)
    row.updated_at = overrides.get("updated_at", _NOW)
    return row


# ---------------------------------------------------------------------------
# BudgetConfigRead
# ---------------------------------------------------------------------------


class TestBudgetConfigRead:
    def test_direct_construction_with_defaults(self) -> None:
        read = BudgetConfigRead(
            daily_spend_warning=None,
            weekly_budget_cap=None,
            per_task_warning=None,
            pause_on_budget_exceeded=False,
            model_downgrade_on_approach=False,
            downgrade_threshold_percent=80.0,
            updated_at=_NOW,
        )
        assert read.daily_spend_warning is None
        assert read.weekly_budget_cap is None
        assert read.per_task_warning is None
        assert read.pause_on_budget_exceeded is False
        assert read.model_downgrade_on_approach is False
        assert read.downgrade_threshold_percent == 80.0

    def test_direct_construction_with_values(self) -> None:
        read = BudgetConfigRead(
            daily_spend_warning=10.0,
            weekly_budget_cap=50.0,
            per_task_warning=5.0,
            pause_on_budget_exceeded=True,
            model_downgrade_on_approach=True,
            downgrade_threshold_percent=75.0,
            updated_at=_NOW,
        )
        assert read.daily_spend_warning == 10.0
        assert read.weekly_budget_cap == 50.0
        assert read.per_task_warning == 5.0
        assert read.pause_on_budget_exceeded is True
        assert read.model_downgrade_on_approach is True
        assert read.downgrade_threshold_percent == 75.0

    def test_from_attributes_orm_row_defaults(self) -> None:
        row = _make_config_row()
        read = BudgetConfigRead.model_validate(row)
        assert read.daily_spend_warning is None
        assert read.weekly_budget_cap is None
        assert read.per_task_warning is None
        assert read.pause_on_budget_exceeded is False
        assert read.model_downgrade_on_approach is False
        assert read.downgrade_threshold_percent == 80.0

    def test_from_attributes_orm_row_with_values(self) -> None:
        row = _make_config_row(
            daily_spend_warning=20.0,
            weekly_budget_cap=100.0,
            per_task_warning=10.0,
            pause_on_budget_exceeded=True,
            model_downgrade_on_approach=True,
            downgrade_threshold_percent=60.0,
        )
        read = BudgetConfigRead.model_validate(row)
        assert read.daily_spend_warning == 20.0
        assert read.weekly_budget_cap == 100.0
        assert read.per_task_warning == 10.0
        assert read.pause_on_budget_exceeded is True
        assert read.model_downgrade_on_approach is True
        assert read.downgrade_threshold_percent == 60.0

    def test_model_config_from_attributes(self) -> None:
        assert BudgetConfigRead.model_config.get("from_attributes") is True

    def test_missing_pause_on_budget_exceeded_raises(self) -> None:
        with pytest.raises(ValidationError):
            BudgetConfigRead(
                daily_spend_warning=None,
                weekly_budget_cap=None,
                per_task_warning=None,
                model_downgrade_on_approach=False,
                downgrade_threshold_percent=80.0,
                updated_at=_NOW,
                # missing pause_on_budget_exceeded
            )  # type: ignore[call-arg]

    def test_missing_downgrade_threshold_percent_raises(self) -> None:
        with pytest.raises(ValidationError):
            BudgetConfigRead(
                daily_spend_warning=None,
                weekly_budget_cap=None,
                per_task_warning=None,
                pause_on_budget_exceeded=False,
                model_downgrade_on_approach=False,
                updated_at=_NOW,
                # missing downgrade_threshold_percent
            )  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# BudgetConfigUpdate
# ---------------------------------------------------------------------------


class TestBudgetConfigUpdate:
    def test_empty_update_valid(self) -> None:
        update = BudgetConfigUpdate()
        assert update.daily_spend_warning is None
        assert update.weekly_budget_cap is None
        assert update.per_task_warning is None
        assert update.pause_on_budget_exceeded is None
        assert update.model_downgrade_on_approach is None
        assert update.downgrade_threshold_percent is None

    def test_partial_daily_spend_warning(self) -> None:
        update = BudgetConfigUpdate(daily_spend_warning=25.0)
        assert update.daily_spend_warning == 25.0

    def test_partial_weekly_budget_cap(self) -> None:
        update = BudgetConfigUpdate(weekly_budget_cap=150.0)
        assert update.weekly_budget_cap == 150.0

    def test_partial_per_task_warning(self) -> None:
        update = BudgetConfigUpdate(per_task_warning=7.5)
        assert update.per_task_warning == 7.5

    def test_daily_spend_warning_ge_0(self) -> None:
        with pytest.raises(ValidationError):
            BudgetConfigUpdate(daily_spend_warning=-0.01)

    def test_daily_spend_warning_0_valid(self) -> None:
        update = BudgetConfigUpdate(daily_spend_warning=0.0)
        assert update.daily_spend_warning == 0.0

    def test_weekly_budget_cap_ge_0(self) -> None:
        with pytest.raises(ValidationError):
            BudgetConfigUpdate(weekly_budget_cap=-1.0)

    def test_weekly_budget_cap_0_valid(self) -> None:
        update = BudgetConfigUpdate(weekly_budget_cap=0.0)
        assert update.weekly_budget_cap == 0.0

    def test_per_task_warning_ge_0(self) -> None:
        with pytest.raises(ValidationError):
            BudgetConfigUpdate(per_task_warning=-0.01)

    def test_per_task_warning_0_valid(self) -> None:
        update = BudgetConfigUpdate(per_task_warning=0.0)
        assert update.per_task_warning == 0.0

    def test_downgrade_threshold_percent_ge_0(self) -> None:
        with pytest.raises(ValidationError):
            BudgetConfigUpdate(downgrade_threshold_percent=-1.0)

    def test_downgrade_threshold_percent_le_100(self) -> None:
        with pytest.raises(ValidationError):
            BudgetConfigUpdate(downgrade_threshold_percent=100.01)

    def test_downgrade_threshold_percent_0_valid(self) -> None:
        update = BudgetConfigUpdate(downgrade_threshold_percent=0.0)
        assert update.downgrade_threshold_percent == 0.0

    def test_downgrade_threshold_percent_100_valid(self) -> None:
        update = BudgetConfigUpdate(downgrade_threshold_percent=100.0)
        assert update.downgrade_threshold_percent == 100.0

    def test_downgrade_threshold_midrange_valid(self) -> None:
        update = BudgetConfigUpdate(downgrade_threshold_percent=80.0)
        assert update.downgrade_threshold_percent == 80.0

    def test_pause_on_budget_exceeded_flag(self) -> None:
        update = BudgetConfigUpdate(pause_on_budget_exceeded=True)
        assert update.pause_on_budget_exceeded is True

    def test_model_downgrade_on_approach_flag(self) -> None:
        update = BudgetConfigUpdate(model_downgrade_on_approach=True)
        assert update.model_downgrade_on_approach is True

    def test_full_update(self) -> None:
        update = BudgetConfigUpdate(
            daily_spend_warning=10.0,
            weekly_budget_cap=70.0,
            per_task_warning=3.0,
            pause_on_budget_exceeded=True,
            model_downgrade_on_approach=True,
            downgrade_threshold_percent=70.0,
        )
        assert update.daily_spend_warning == 10.0
        assert update.weekly_budget_cap == 70.0
        assert update.per_task_warning == 3.0
        assert update.pause_on_budget_exceeded is True
        assert update.model_downgrade_on_approach is True
        assert update.downgrade_threshold_percent == 70.0
