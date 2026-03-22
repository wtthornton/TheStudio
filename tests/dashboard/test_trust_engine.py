"""Tests for src/dashboard/trust_engine.py.

Covers:
- All 6 ConditionOperator values (equals, not_equals, less_than, greater_than,
  contains, matches_glob)
- _resolve_field with dot-notation (flat, nested, missing)
- _rule_matches AND logic (all conditions must pass)
- evaluate_trust_tier first-match-wins ordering
- Safety bounds override (loopback cap, diff-lines cap, mandatory-review pattern)
- Default tier fallback (no rules match)
- _cap_tier logic (OBSERVE < SUGGEST < EXECUTE ordering)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.dashboard.models.trust_config import (
    AssignedTier,
    ConditionOperator,
    RuleCondition,
    SafeBoundsRead,
    TrustTierRuleRead,
)
from src.dashboard.trust_engine import (
    EvaluationResult,
    _cap_tier,
    _resolve_field,
    _rule_matches,
    evaluate_trust_tier,
)

from tests.dashboard.conftest import make_task_row

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


def _make_rule(
    *,
    conditions: list[dict[str, Any]],
    assigned_tier: AssignedTier = AssignedTier.SUGGEST,
    priority: int = 100,
    rule_id: Any = None,
) -> TrustTierRuleRead:
    """Build a TrustTierRuleRead for tests without hitting the database."""
    return TrustTierRuleRead(
        id=rule_id or uuid4(),
        priority=priority,
        conditions=[RuleCondition.model_validate(c) for c in conditions],
        assigned_tier=assigned_tier,
        active=True,
        description=None,
        created_at=_now(),
        updated_at=_now(),
    )


def _make_bounds(
    *,
    max_loopbacks: int | None = None,
    max_auto_merge_lines: int | None = None,
    mandatory_review_patterns: list[str] | None = None,
) -> SafeBoundsRead:
    """Build a SafeBoundsRead for tests."""
    return SafeBoundsRead(
        max_auto_merge_lines=max_auto_merge_lines,
        max_auto_merge_cost=None,
        max_loopbacks=max_loopbacks,
        mandatory_review_patterns=mandatory_review_patterns or [],
        updated_at=_now(),
    )


def _patch_engine(rules: list[TrustTierRuleRead], bounds: SafeBoundsRead):
    """Context manager that patches list_rules and get_safety_bounds."""
    return patch.multiple(
        "src.dashboard.trust_engine",
        list_rules=AsyncMock(return_value=rules),
        get_safety_bounds=AsyncMock(return_value=bounds),
    )


# ---------------------------------------------------------------------------
# _cap_tier
# ---------------------------------------------------------------------------


class TestCapTier:
    """_cap_tier returns the more restrictive tier."""

    def test_same_tier(self):
        assert _cap_tier(AssignedTier.SUGGEST, AssignedTier.SUGGEST) == AssignedTier.SUGGEST

    def test_cap_execute_to_suggest(self):
        assert _cap_tier(AssignedTier.EXECUTE, AssignedTier.SUGGEST) == AssignedTier.SUGGEST

    def test_cap_execute_to_observe(self):
        assert _cap_tier(AssignedTier.EXECUTE, AssignedTier.OBSERVE) == AssignedTier.OBSERVE

    def test_cap_suggest_to_observe(self):
        assert _cap_tier(AssignedTier.SUGGEST, AssignedTier.OBSERVE) == AssignedTier.OBSERVE

    def test_no_cap_when_already_lower(self):
        # tier is already below max — no change
        assert _cap_tier(AssignedTier.OBSERVE, AssignedTier.EXECUTE) == AssignedTier.OBSERVE

    def test_no_cap_observe_against_suggest(self):
        assert _cap_tier(AssignedTier.OBSERVE, AssignedTier.SUGGEST) == AssignedTier.OBSERVE


# ---------------------------------------------------------------------------
# _resolve_field
# ---------------------------------------------------------------------------


class TestResolveField:
    """_resolve_field resolves flat and dot-notation paths on a TaskPacketRow mock."""

    def test_flat_attribute(self):
        packet = make_task_row(loopback_count=3)
        assert _resolve_field(packet, "loopback_count") == 3

    def test_flat_string_attribute(self):
        packet = make_task_row(repo="acme/platform")
        assert _resolve_field(packet, "repo") == "acme/platform"

    def test_nested_one_level(self):
        packet = make_task_row(complexity_index={"score": 0.9, "level": "high"})
        assert _resolve_field(packet, "complexity_index.score") == 0.9

    def test_nested_two_levels(self):
        packet = make_task_row(risk_flags={"security": {"critical": True}})
        assert _resolve_field(packet, "risk_flags.security.critical") is True

    def test_missing_attribute_raises(self):
        packet = make_task_row()
        with pytest.raises(AttributeError):
            _resolve_field(packet, "nonexistent_field")

    def test_missing_nested_key_raises(self):
        packet = make_task_row(complexity_index={"score": 0.5})
        with pytest.raises(KeyError):
            _resolve_field(packet, "complexity_index.missing_key")

    def test_non_dict_intermediate_raises(self):
        # complexity_index is a scalar, not a dict — traversal should raise TypeError
        packet = make_task_row(complexity_index="not_a_dict")
        with pytest.raises(TypeError):
            _resolve_field(packet, "complexity_index.score")


# ---------------------------------------------------------------------------
# Condition operators — _rule_matches (via single-condition rules)
# ---------------------------------------------------------------------------


class TestConditionEquals:
    def test_equals_true(self):
        rule = _make_rule(conditions=[{"field": "repo", "op": "equals", "value": "owner/repo"}])
        packet = make_task_row(repo="owner/repo")
        assert _rule_matches(rule, packet) is True

    def test_equals_false(self):
        rule = _make_rule(conditions=[{"field": "repo", "op": "equals", "value": "other/repo"}])
        packet = make_task_row(repo="owner/repo")
        assert _rule_matches(rule, packet) is False

    def test_equals_numeric(self):
        rule = _make_rule(conditions=[{"field": "loopback_count", "op": "equals", "value": 0}])
        packet = make_task_row(loopback_count=0)
        assert _rule_matches(rule, packet) is True


class TestConditionNotEquals:
    def test_not_equals_true(self):
        rule = _make_rule(
            conditions=[{"field": "repo", "op": "not_equals", "value": "other/repo"}]
        )
        packet = make_task_row(repo="owner/repo")
        assert _rule_matches(rule, packet) is True

    def test_not_equals_false(self):
        rule = _make_rule(
            conditions=[{"field": "repo", "op": "not_equals", "value": "owner/repo"}]
        )
        packet = make_task_row(repo="owner/repo")
        assert _rule_matches(rule, packet) is False


class TestConditionLessThan:
    def test_less_than_true(self):
        rule = _make_rule(
            conditions=[{"field": "loopback_count", "op": "less_than", "value": 5}]
        )
        packet = make_task_row(loopback_count=2)
        assert _rule_matches(rule, packet) is True

    def test_less_than_equal_is_false(self):
        rule = _make_rule(
            conditions=[{"field": "loopback_count", "op": "less_than", "value": 2}]
        )
        packet = make_task_row(loopback_count=2)
        assert _rule_matches(rule, packet) is False

    def test_less_than_false(self):
        rule = _make_rule(
            conditions=[{"field": "loopback_count", "op": "less_than", "value": 1}]
        )
        packet = make_task_row(loopback_count=3)
        assert _rule_matches(rule, packet) is False


class TestConditionGreaterThan:
    def test_greater_than_true(self):
        rule = _make_rule(
            conditions=[{"field": "loopback_count", "op": "greater_than", "value": 1}]
        )
        packet = make_task_row(loopback_count=3)
        assert _rule_matches(rule, packet) is True

    def test_greater_than_equal_is_false(self):
        rule = _make_rule(
            conditions=[{"field": "loopback_count", "op": "greater_than", "value": 3}]
        )
        packet = make_task_row(loopback_count=3)
        assert _rule_matches(rule, packet) is False

    def test_greater_than_nested_float(self):
        rule = _make_rule(
            conditions=[{"field": "complexity_index.score", "op": "greater_than", "value": 0.7}]
        )
        packet = make_task_row(complexity_index={"score": 0.9})
        assert _rule_matches(rule, packet) is True


class TestConditionContains:
    def test_contains_substring_true(self):
        rule = _make_rule(
            conditions=[{"field": "repo", "op": "contains", "value": "platform"}]
        )
        packet = make_task_row(repo="acme/platform")
        assert _rule_matches(rule, packet) is True

    def test_contains_substring_false(self):
        rule = _make_rule(
            conditions=[{"field": "repo", "op": "contains", "value": "staging"}]
        )
        packet = make_task_row(repo="acme/platform")
        assert _rule_matches(rule, packet) is False

    def test_contains_list_membership_true(self):
        rule = _make_rule(
            conditions=[{"field": "risk_flags", "op": "contains", "value": "security"}]
        )
        packet = make_task_row(risk_flags=["security", "compliance"])
        assert _rule_matches(rule, packet) is True

    def test_contains_list_membership_false(self):
        rule = _make_rule(
            conditions=[{"field": "risk_flags", "op": "contains", "value": "billing"}]
        )
        packet = make_task_row(risk_flags=["security", "compliance"])
        assert _rule_matches(rule, packet) is False


class TestConditionMatchesGlob:
    def test_matches_glob_true(self):
        rule = _make_rule(
            conditions=[{"field": "repo", "op": "matches_glob", "value": "acme/*"}]
        )
        packet = make_task_row(repo="acme/platform")
        assert _rule_matches(rule, packet) is True

    def test_matches_glob_false(self):
        rule = _make_rule(
            conditions=[{"field": "repo", "op": "matches_glob", "value": "other/*"}]
        )
        packet = make_task_row(repo="acme/platform")
        assert _rule_matches(rule, packet) is False

    def test_matches_glob_wildcard_all(self):
        rule = _make_rule(
            conditions=[{"field": "repo", "op": "matches_glob", "value": "*"}]
        )
        packet = make_task_row(repo="anything/goes")
        assert _rule_matches(rule, packet) is True

    def test_matches_glob_question_mark(self):
        rule = _make_rule(
            conditions=[{"field": "repo", "op": "matches_glob", "value": "acme/platfor?"}]
        )
        packet = make_task_row(repo="acme/platform")
        assert _rule_matches(rule, packet) is True


# ---------------------------------------------------------------------------
# _rule_matches — AND logic
# ---------------------------------------------------------------------------


class TestRuleMatchesAndLogic:
    def test_all_conditions_pass(self):
        rule = _make_rule(
            conditions=[
                {"field": "loopback_count", "op": "less_than", "value": 5},
                {"field": "repo", "op": "equals", "value": "owner/repo"},
            ]
        )
        packet = make_task_row(loopback_count=2, repo="owner/repo")
        assert _rule_matches(rule, packet) is True

    def test_first_condition_fails(self):
        rule = _make_rule(
            conditions=[
                {"field": "loopback_count", "op": "less_than", "value": 1},
                {"field": "repo", "op": "equals", "value": "owner/repo"},
            ]
        )
        packet = make_task_row(loopback_count=5, repo="owner/repo")
        assert _rule_matches(rule, packet) is False

    def test_second_condition_fails(self):
        rule = _make_rule(
            conditions=[
                {"field": "loopback_count", "op": "less_than", "value": 5},
                {"field": "repo", "op": "equals", "value": "wrong/repo"},
            ]
        )
        packet = make_task_row(loopback_count=2, repo="owner/repo")
        assert _rule_matches(rule, packet) is False

    def test_empty_conditions_is_vacuously_true(self):
        rule = _make_rule(conditions=[])
        packet = make_task_row()
        assert _rule_matches(rule, packet) is True

    def test_unresolvable_field_returns_false(self):
        # A rule with a missing field should safely return False, not raise.
        rule = _make_rule(
            conditions=[{"field": "nonexistent_field", "op": "equals", "value": "x"}]
        )
        packet = make_task_row()
        assert _rule_matches(rule, packet) is False


# ---------------------------------------------------------------------------
# evaluate_trust_tier — integration (mocked DB)
# ---------------------------------------------------------------------------


class TestEvaluateTrustTier:
    """High-level tests for the full evaluation pipeline."""

    @pytest.mark.asyncio
    async def test_default_tier_when_no_rules(self):
        session = AsyncMock()
        bounds = _make_bounds()
        with _patch_engine(rules=[], bounds=bounds):
            result = await evaluate_trust_tier(
                session, make_task_row(), default_tier=AssignedTier.OBSERVE
            )
        assert result.tier == AssignedTier.OBSERVE
        assert result.matched_rule_id is None
        assert result.safety_capped is False

    @pytest.mark.asyncio
    async def test_default_tier_suggest_when_no_rules(self):
        session = AsyncMock()
        bounds = _make_bounds()
        with _patch_engine(rules=[], bounds=bounds):
            result = await evaluate_trust_tier(
                session, make_task_row(), default_tier=AssignedTier.SUGGEST
            )
        assert result.tier == AssignedTier.SUGGEST

    @pytest.mark.asyncio
    async def test_first_match_wins(self):
        """First rule in priority order that matches wins; subsequent rules ignored."""
        rule_id_1 = uuid4()
        rule_id_2 = uuid4()
        rules = [
            _make_rule(
                conditions=[{"field": "loopback_count", "op": "less_than", "value": 10}],
                assigned_tier=AssignedTier.EXECUTE,
                priority=10,
                rule_id=rule_id_1,
            ),
            _make_rule(
                conditions=[{"field": "loopback_count", "op": "less_than", "value": 10}],
                assigned_tier=AssignedTier.OBSERVE,
                priority=20,
                rule_id=rule_id_2,
            ),
        ]
        bounds = _make_bounds()
        session = AsyncMock()
        with _patch_engine(rules=rules, bounds=bounds):
            result = await evaluate_trust_tier(session, make_task_row(loopback_count=3))
        assert result.tier == AssignedTier.EXECUTE
        assert result.matched_rule_id == rule_id_1

    @pytest.mark.asyncio
    async def test_second_rule_matches_when_first_fails(self):
        rule_id_1 = uuid4()
        rule_id_2 = uuid4()
        rules = [
            _make_rule(
                conditions=[{"field": "repo", "op": "equals", "value": "no-match/repo"}],
                assigned_tier=AssignedTier.EXECUTE,
                priority=10,
                rule_id=rule_id_1,
            ),
            _make_rule(
                conditions=[{"field": "repo", "op": "equals", "value": "owner/repo"}],
                assigned_tier=AssignedTier.SUGGEST,
                priority=20,
                rule_id=rule_id_2,
            ),
        ]
        bounds = _make_bounds()
        session = AsyncMock()
        with _patch_engine(rules=rules, bounds=bounds):
            result = await evaluate_trust_tier(session, make_task_row(repo="owner/repo"))
        assert result.tier == AssignedTier.SUGGEST
        assert result.matched_rule_id == rule_id_2

    @pytest.mark.asyncio
    async def test_no_rule_matches_uses_default(self):
        rule = _make_rule(
            conditions=[{"field": "repo", "op": "equals", "value": "no-match"}],
            assigned_tier=AssignedTier.EXECUTE,
        )
        bounds = _make_bounds()
        session = AsyncMock()
        with _patch_engine(rules=[rule], bounds=bounds):
            result = await evaluate_trust_tier(
                session,
                make_task_row(repo="owner/repo"),
                default_tier=AssignedTier.OBSERVE,
            )
        assert result.tier == AssignedTier.OBSERVE
        assert result.matched_rule_id is None


# ---------------------------------------------------------------------------
# Safety bounds override
# ---------------------------------------------------------------------------


class TestSafetyBoundsCap:
    @pytest.mark.asyncio
    async def test_loopback_exceeds_max_caps_to_suggest(self):
        """EXECUTE tier should be capped to SUGGEST when loopback_count > max_loopbacks."""
        rule = _make_rule(
            conditions=[],  # always matches
            assigned_tier=AssignedTier.EXECUTE,
        )
        bounds = _make_bounds(max_loopbacks=3)
        session = AsyncMock()
        with _patch_engine(rules=[rule], bounds=bounds):
            result = await evaluate_trust_tier(
                session, make_task_row(loopback_count=5)
            )
        assert result.tier == AssignedTier.SUGGEST
        assert result.raw_tier == AssignedTier.EXECUTE
        assert result.safety_capped is True

    @pytest.mark.asyncio
    async def test_loopback_at_max_does_not_cap(self):
        """Exactly at max_loopbacks should NOT trigger the safety cap."""
        rule = _make_rule(conditions=[], assigned_tier=AssignedTier.EXECUTE)
        bounds = _make_bounds(max_loopbacks=3)
        session = AsyncMock()
        with _patch_engine(rules=[rule], bounds=bounds):
            result = await evaluate_trust_tier(
                session, make_task_row(loopback_count=3)
            )
        # loopback_count == max_loopbacks (not strictly greater) → no cap
        assert result.safety_capped is False
        assert result.tier == AssignedTier.EXECUTE

    @pytest.mark.asyncio
    async def test_diff_lines_exceeds_max_caps_to_suggest(self):
        """EXECUTE tier capped when diff_lines in scope exceeds max_auto_merge_lines."""
        rule = _make_rule(conditions=[], assigned_tier=AssignedTier.EXECUTE)
        bounds = _make_bounds(max_auto_merge_lines=100)
        session = AsyncMock()
        packet = make_task_row(scope={"diff_lines": 500})
        with _patch_engine(rules=[rule], bounds=bounds):
            result = await evaluate_trust_tier(session, packet)
        assert result.tier == AssignedTier.SUGGEST
        assert result.safety_capped is True

    @pytest.mark.asyncio
    async def test_changed_lines_key_also_checked(self):
        """Safety bounds check the 'changed_lines' key as well as 'diff_lines'."""
        rule = _make_rule(conditions=[], assigned_tier=AssignedTier.EXECUTE)
        bounds = _make_bounds(max_auto_merge_lines=50)
        session = AsyncMock()
        packet = make_task_row(scope={"changed_lines": 200})
        with _patch_engine(rules=[rule], bounds=bounds):
            result = await evaluate_trust_tier(session, packet)
        assert result.tier == AssignedTier.SUGGEST
        assert result.safety_capped is True

    @pytest.mark.asyncio
    async def test_mandatory_review_pattern_caps_to_suggest(self):
        """Repos matching mandatory_review_patterns should be capped at SUGGEST."""
        rule = _make_rule(conditions=[], assigned_tier=AssignedTier.EXECUTE)
        bounds = _make_bounds(mandatory_review_patterns=["acme/*"])
        session = AsyncMock()
        packet = make_task_row(repo="acme/platform")
        with _patch_engine(rules=[rule], bounds=bounds):
            result = await evaluate_trust_tier(session, packet)
        assert result.tier == AssignedTier.SUGGEST
        assert result.safety_capped is True

    @pytest.mark.asyncio
    async def test_mandatory_review_pattern_no_match(self):
        """Repos NOT matching patterns should not be capped."""
        rule = _make_rule(conditions=[], assigned_tier=AssignedTier.EXECUTE)
        bounds = _make_bounds(mandatory_review_patterns=["acme/*"])
        session = AsyncMock()
        packet = make_task_row(repo="other/platform")
        with _patch_engine(rules=[rule], bounds=bounds):
            result = await evaluate_trust_tier(session, packet)
        assert result.safety_capped is False
        assert result.tier == AssignedTier.EXECUTE

    @pytest.mark.asyncio
    async def test_safety_cap_does_not_elevate_tier(self):
        """Safety bounds cap at SUGGEST; they should NOT elevate OBSERVE to SUGGEST."""
        rule = _make_rule(conditions=[], assigned_tier=AssignedTier.OBSERVE)
        bounds = _make_bounds(max_loopbacks=0, max_auto_merge_lines=1)
        session = AsyncMock()
        # Exceeds every safety bound but tier is already OBSERVE (already restricted)
        packet = make_task_row(loopback_count=99, scope={"diff_lines": 9999})
        with _patch_engine(rules=[rule], bounds=bounds):
            result = await evaluate_trust_tier(session, packet)
        # OBSERVE is already below SUGGEST — cap should not elevate it
        assert result.tier == AssignedTier.OBSERVE
        # safety_capped stays False because capping didn't actually change the tier
        assert result.safety_capped is False

    @pytest.mark.asyncio
    async def test_no_bounds_set_means_no_safety_cap(self):
        """When all safety bounds are None, no cap should be applied."""
        rule = _make_rule(conditions=[], assigned_tier=AssignedTier.EXECUTE)
        bounds = _make_bounds()  # all None
        session = AsyncMock()
        packet = make_task_row(loopback_count=100, scope={"diff_lines": 10000})
        with _patch_engine(rules=[rule], bounds=bounds):
            result = await evaluate_trust_tier(session, packet)
        assert result.tier == AssignedTier.EXECUTE
        assert result.safety_capped is False


# ---------------------------------------------------------------------------
# EvaluationResult attributes
# ---------------------------------------------------------------------------


class TestEvaluationResult:
    def test_raw_tier_defaults_to_tier(self):
        result = EvaluationResult(AssignedTier.SUGGEST)
        assert result.raw_tier == AssignedTier.SUGGEST

    def test_raw_tier_explicit(self):
        result = EvaluationResult(
            AssignedTier.SUGGEST,
            raw_tier=AssignedTier.EXECUTE,
            safety_capped=True,
        )
        assert result.raw_tier == AssignedTier.EXECUTE
        assert result.tier == AssignedTier.SUGGEST
        assert result.safety_capped is True

    def test_repr_contains_tier(self):
        result = EvaluationResult(AssignedTier.OBSERVE)
        assert "OBSERVE" in repr(result)

    def test_matched_rule_id_none_by_default(self):
        result = EvaluationResult(AssignedTier.OBSERVE)
        assert result.matched_rule_id is None
