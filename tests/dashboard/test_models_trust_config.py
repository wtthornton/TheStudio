"""Pydantic model validation tests for trust config models.

Tests cover:
- AssignedTier and ConditionOperator enum values
- RuleCondition field requirements
- TrustTierRuleCreate required/optional fields, ge/le constraints
- TrustTierRuleUpdate all-optional partial update schema
- TrustTierRuleRead from_attributes ORM loading
- SafeBoundsUpdate ge constraints
- SafeBoundsRead from_attributes ORM loading
- DefaultTierRead and DefaultTierUpdate
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from src.dashboard.models.trust_config import (
    AssignedTier,
    ConditionOperator,
    DefaultTierRead,
    DefaultTierUpdate,
    RuleCondition,
    SafeBoundsRead,
    SafeBoundsUpdate,
    TrustTierRuleCreate,
    TrustTierRuleRead,
    TrustTierRuleUpdate,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(UTC)
_RULE_ID = uuid4()


def _make_rule_row(**overrides: Any) -> MagicMock:
    """Return a MagicMock suitable for TrustTierRuleRead.model_validate."""
    row = MagicMock()
    row.id = overrides.get("id", _RULE_ID)
    row.priority = overrides.get("priority", 100)
    row.conditions = overrides.get("conditions", [])
    row.assigned_tier = overrides.get("assigned_tier", AssignedTier.OBSERVE)
    row.active = overrides.get("active", True)
    row.description = overrides.get("description", None)
    # Epic 42 Story 42.11 — rule success tracking fields
    row.merge_count = overrides.get("merge_count", 0)
    row.revert_count = overrides.get("revert_count", 0)
    row.deactivation_reason = overrides.get("deactivation_reason", None)
    row.created_at = overrides.get("created_at", _NOW)
    row.updated_at = overrides.get("updated_at", _NOW)
    return row


def _make_bounds_row(**overrides: Any) -> MagicMock:
    """Return a MagicMock suitable for SafeBoundsRead.model_validate."""
    row = MagicMock()
    row.max_auto_merge_lines = overrides.get("max_auto_merge_lines", 500)
    row.max_auto_merge_cost = overrides.get("max_auto_merge_cost", 500)
    row.max_loopbacks = overrides.get("max_loopbacks", 3)
    row.mandatory_review_patterns = overrides.get("mandatory_review_patterns", [])
    row.updated_at = overrides.get("updated_at", _NOW)
    return row


# ---------------------------------------------------------------------------
# AssignedTier enum
# ---------------------------------------------------------------------------


class TestAssignedTierEnum:
    def test_all_values(self) -> None:
        assert {t.value for t in AssignedTier} == {"observe", "suggest", "execute"}

    def test_is_str_enum(self) -> None:
        assert isinstance(AssignedTier.OBSERVE, str)

    def test_values(self) -> None:
        assert AssignedTier.OBSERVE == "observe"
        assert AssignedTier.SUGGEST == "suggest"
        assert AssignedTier.EXECUTE == "execute"

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            AssignedTier("unknown")


# ---------------------------------------------------------------------------
# ConditionOperator enum
# ---------------------------------------------------------------------------


class TestConditionOperatorEnum:
    def test_all_six_operators(self) -> None:
        expected = {"equals", "not_equals", "less_than", "greater_than", "contains", "matches_glob"}
        assert {op.value for op in ConditionOperator} == expected

    def test_each_member(self) -> None:
        assert ConditionOperator.EQUALS == "equals"
        assert ConditionOperator.NOT_EQUALS == "not_equals"
        assert ConditionOperator.LESS_THAN == "less_than"
        assert ConditionOperator.GREATER_THAN == "greater_than"
        assert ConditionOperator.CONTAINS == "contains"
        assert ConditionOperator.MATCHES_GLOB == "matches_glob"

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            ConditionOperator("regex")


# ---------------------------------------------------------------------------
# RuleCondition
# ---------------------------------------------------------------------------


class TestRuleCondition:
    def test_happy_path(self) -> None:
        cond = RuleCondition(field="complexity_index", op=ConditionOperator.GREATER_THAN, value=0.8)
        assert cond.field == "complexity_index"
        assert cond.op == ConditionOperator.GREATER_THAN
        assert cond.value == 0.8

    def test_missing_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            RuleCondition(op=ConditionOperator.EQUALS, value="prod")  # type: ignore[call-arg]

    def test_missing_op_raises(self) -> None:
        with pytest.raises(ValidationError):
            RuleCondition(field="repo", value="prod")  # type: ignore[call-arg]

    def test_missing_value_raises(self) -> None:
        with pytest.raises(ValidationError):
            RuleCondition(field="repo", op=ConditionOperator.EQUALS)  # type: ignore[call-arg]

    def test_dot_notation_field(self) -> None:
        cond = RuleCondition(field="risk_flags.security", op=ConditionOperator.CONTAINS, value="sql")
        assert cond.field == "risk_flags.security"

    def test_value_accepts_string(self) -> None:
        cond = RuleCondition(field="repo", op=ConditionOperator.EQUALS, value="owner/repo")
        assert cond.value == "owner/repo"

    def test_value_accepts_number(self) -> None:
        cond = RuleCondition(field="loopback_count", op=ConditionOperator.LESS_THAN, value=5)
        assert cond.value == 5

    def test_value_accepts_bool(self) -> None:
        cond = RuleCondition(field="readiness_miss", op=ConditionOperator.EQUALS, value=True)
        assert cond.value is True

    def test_all_operators_accepted(self) -> None:
        for op in ConditionOperator:
            cond = RuleCondition(field="x", op=op, value=1)
            assert cond.op == op


# ---------------------------------------------------------------------------
# TrustTierRuleCreate
# ---------------------------------------------------------------------------


class TestTrustTierRuleCreate:
    def test_happy_path_required_only(self) -> None:
        rule = TrustTierRuleCreate(assigned_tier=AssignedTier.SUGGEST)
        assert rule.assigned_tier == AssignedTier.SUGGEST

    def test_missing_assigned_tier_raises(self) -> None:
        with pytest.raises(ValidationError):
            TrustTierRuleCreate()  # type: ignore[call-arg]

    def test_priority_default(self) -> None:
        rule = TrustTierRuleCreate(assigned_tier=AssignedTier.OBSERVE)
        assert rule.priority == 100

    def test_conditions_default_empty(self) -> None:
        rule = TrustTierRuleCreate(assigned_tier=AssignedTier.OBSERVE)
        assert rule.conditions == []

    def test_active_default_true(self) -> None:
        rule = TrustTierRuleCreate(assigned_tier=AssignedTier.OBSERVE)
        assert rule.active is True

    def test_description_default_none(self) -> None:
        rule = TrustTierRuleCreate(assigned_tier=AssignedTier.OBSERVE)
        assert rule.description is None

    def test_priority_ge_1(self) -> None:
        with pytest.raises(ValidationError):
            TrustTierRuleCreate(assigned_tier=AssignedTier.OBSERVE, priority=0)

    def test_priority_le_9999(self) -> None:
        with pytest.raises(ValidationError):
            TrustTierRuleCreate(assigned_tier=AssignedTier.OBSERVE, priority=10000)

    def test_priority_boundary_1(self) -> None:
        rule = TrustTierRuleCreate(assigned_tier=AssignedTier.OBSERVE, priority=1)
        assert rule.priority == 1

    def test_priority_boundary_9999(self) -> None:
        rule = TrustTierRuleCreate(assigned_tier=AssignedTier.OBSERVE, priority=9999)
        assert rule.priority == 9999

    def test_description_max_length_500(self) -> None:
        desc_500 = "d" * 500
        rule = TrustTierRuleCreate(assigned_tier=AssignedTier.OBSERVE, description=desc_500)
        assert len(rule.description) == 500  # type: ignore[arg-type]

    def test_description_exceeds_500_raises(self) -> None:
        with pytest.raises(ValidationError):
            TrustTierRuleCreate(assigned_tier=AssignedTier.OBSERVE, description="d" * 501)

    def test_conditions_with_items(self) -> None:
        cond = RuleCondition(field="complexity_index", op=ConditionOperator.GREATER_THAN, value=0.9)
        rule = TrustTierRuleCreate(assigned_tier=AssignedTier.EXECUTE, conditions=[cond])
        assert len(rule.conditions) == 1
        assert rule.conditions[0].field == "complexity_index"


# ---------------------------------------------------------------------------
# TrustTierRuleUpdate
# ---------------------------------------------------------------------------


class TestTrustTierRuleUpdate:
    def test_empty_update_is_valid(self) -> None:
        update = TrustTierRuleUpdate()
        assert update.priority is None
        assert update.conditions is None
        assert update.assigned_tier is None
        assert update.active is None
        assert update.description is None

    def test_partial_priority_only(self) -> None:
        update = TrustTierRuleUpdate(priority=50)
        assert update.priority == 50

    def test_partial_active_only(self) -> None:
        update = TrustTierRuleUpdate(active=False)
        assert update.active is False

    def test_priority_ge_1(self) -> None:
        with pytest.raises(ValidationError):
            TrustTierRuleUpdate(priority=0)

    def test_priority_le_9999(self) -> None:
        with pytest.raises(ValidationError):
            TrustTierRuleUpdate(priority=10000)

    def test_description_max_length_500(self) -> None:
        update = TrustTierRuleUpdate(description="x" * 500)
        assert len(update.description) == 500  # type: ignore[arg-type]

    def test_description_exceeds_500_raises(self) -> None:
        with pytest.raises(ValidationError):
            TrustTierRuleUpdate(description="x" * 501)

    def test_full_update(self) -> None:
        cond = RuleCondition(field="loopback_count", op=ConditionOperator.GREATER_THAN, value=2)
        update = TrustTierRuleUpdate(
            priority=10,
            conditions=[cond],
            assigned_tier=AssignedTier.SUGGEST,
            active=False,
            description="Updated",
        )
        assert update.priority == 10
        assert update.assigned_tier == AssignedTier.SUGGEST
        assert update.active is False


# ---------------------------------------------------------------------------
# TrustTierRuleRead
# ---------------------------------------------------------------------------


class TestTrustTierRuleRead:
    def test_direct_construction(self) -> None:
        read = TrustTierRuleRead(
            id=_RULE_ID,
            priority=100,
            conditions=[],
            assigned_tier=AssignedTier.OBSERVE,
            active=True,
            description=None,
            created_at=_NOW,
            updated_at=_NOW,
        )
        assert read.id == _RULE_ID
        assert read.assigned_tier == AssignedTier.OBSERVE

    def test_from_attributes_orm_row(self) -> None:
        row = _make_rule_row(
            assigned_tier=AssignedTier.SUGGEST,
            conditions=[{"field": "x", "op": "equals", "value": 1}],
        )
        read = TrustTierRuleRead.model_validate(row)
        assert read.id == _RULE_ID
        assert read.assigned_tier == AssignedTier.SUGGEST
        assert len(read.conditions) == 1
        assert read.conditions[0].field == "x"

    def test_from_attributes_empty_conditions(self) -> None:
        row = _make_rule_row(conditions=[])
        read = TrustTierRuleRead.model_validate(row)
        assert read.conditions == []

    def test_model_config_from_attributes(self) -> None:
        assert TrustTierRuleRead.model_config.get("from_attributes") is True

    def test_uuid_field(self) -> None:
        row = _make_rule_row()
        read = TrustTierRuleRead.model_validate(row)
        assert isinstance(read.id, UUID)

    def test_inactive_rule(self) -> None:
        row = _make_rule_row(active=False)
        read = TrustTierRuleRead.model_validate(row)
        assert read.active is False

    def test_all_assigned_tiers(self) -> None:
        for tier in AssignedTier:
            row = _make_rule_row(assigned_tier=tier)
            read = TrustTierRuleRead.model_validate(row)
            assert read.assigned_tier == tier


# ---------------------------------------------------------------------------
# SafeBoundsUpdate
# ---------------------------------------------------------------------------


class TestSafeBoundsUpdate:
    def test_empty_update_valid(self) -> None:
        update = SafeBoundsUpdate()
        assert update.max_auto_merge_lines is None
        assert update.max_auto_merge_cost is None
        assert update.max_loopbacks is None
        assert update.mandatory_review_patterns is None

    def test_max_auto_merge_lines_ge_1(self) -> None:
        with pytest.raises(ValidationError):
            SafeBoundsUpdate(max_auto_merge_lines=0)

    def test_max_auto_merge_lines_1_valid(self) -> None:
        update = SafeBoundsUpdate(max_auto_merge_lines=1)
        assert update.max_auto_merge_lines == 1

    def test_max_auto_merge_cost_ge_0(self) -> None:
        with pytest.raises(ValidationError):
            SafeBoundsUpdate(max_auto_merge_cost=-1)

    def test_max_auto_merge_cost_0_valid(self) -> None:
        update = SafeBoundsUpdate(max_auto_merge_cost=0)
        assert update.max_auto_merge_cost == 0

    def test_max_loopbacks_ge_0(self) -> None:
        with pytest.raises(ValidationError):
            SafeBoundsUpdate(max_loopbacks=-1)

    def test_max_loopbacks_0_valid(self) -> None:
        update = SafeBoundsUpdate(max_loopbacks=0)
        assert update.max_loopbacks == 0

    def test_mandatory_review_patterns_list(self) -> None:
        patterns = ["**/migrations/**", "**/settings*"]
        update = SafeBoundsUpdate(mandatory_review_patterns=patterns)
        assert update.mandatory_review_patterns == patterns


# ---------------------------------------------------------------------------
# SafeBoundsRead
# ---------------------------------------------------------------------------


class TestSafeBoundsRead:
    def test_direct_construction(self) -> None:
        read = SafeBoundsRead(
            max_auto_merge_lines=500,
            max_auto_merge_cost=500,
            max_loopbacks=3,
            mandatory_review_patterns=["**/migrations/**"],
            updated_at=_NOW,
        )
        assert read.max_auto_merge_lines == 500

    def test_from_attributes_orm_row(self) -> None:
        row = _make_bounds_row(
            max_auto_merge_lines=1000,
            mandatory_review_patterns=["**/migrations/**"],
        )
        read = SafeBoundsRead.model_validate(row)
        assert read.max_auto_merge_lines == 1000
        assert read.mandatory_review_patterns == ["**/migrations/**"]

    def test_nullable_fields(self) -> None:
        row = _make_bounds_row(
            max_auto_merge_lines=None,
            max_auto_merge_cost=None,
            max_loopbacks=None,
        )
        read = SafeBoundsRead.model_validate(row)
        assert read.max_auto_merge_lines is None
        assert read.max_auto_merge_cost is None
        assert read.max_loopbacks is None

    def test_model_config_from_attributes(self) -> None:
        assert SafeBoundsRead.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# DefaultTierRead / DefaultTierUpdate
# ---------------------------------------------------------------------------


class TestDefaultTierRead:
    def test_construction(self) -> None:
        read = DefaultTierRead(default_tier=AssignedTier.OBSERVE, updated_at=_NOW)
        assert read.default_tier == AssignedTier.OBSERVE

    def test_from_attributes(self) -> None:
        row = MagicMock()
        row.default_tier = AssignedTier.SUGGEST
        row.updated_at = _NOW
        read = DefaultTierRead.model_validate(row)
        assert read.default_tier == AssignedTier.SUGGEST

    def test_model_config_from_attributes(self) -> None:
        assert DefaultTierRead.model_config.get("from_attributes") is True

    def test_all_tiers_accepted(self) -> None:
        for tier in AssignedTier:
            read = DefaultTierRead(default_tier=tier, updated_at=_NOW)
            assert read.default_tier == tier


class TestDefaultTierUpdate:
    def test_required_field(self) -> None:
        update = DefaultTierUpdate(default_tier=AssignedTier.EXECUTE)
        assert update.default_tier == AssignedTier.EXECUTE

    def test_missing_default_tier_raises(self) -> None:
        with pytest.raises(ValidationError):
            DefaultTierUpdate()  # type: ignore[call-arg]

    def test_invalid_tier_raises(self) -> None:
        with pytest.raises(ValidationError):
            DefaultTierUpdate(default_tier="superuser")  # type: ignore[arg-type]
