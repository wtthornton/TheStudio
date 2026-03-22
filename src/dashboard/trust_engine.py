"""Trust tier rule evaluation engine.

Evaluates operator-defined conditions against a TaskPacket and assigns a trust
tier (observe / suggest / execute).  Evaluation contract:

1. Load all *active* ``TrustTierRule`` rows ordered by ``priority`` ascending.
2. For each rule evaluate ALL conditions (AND logic) against the packet's
   flat + nested metadata.  First rule whose conditions all pass wins.
3. Apply ``SafetyBounds`` overrides — if the packet's metrics breach a bound
   the tier is capped at ``SUGGEST`` regardless of what the rules returned.
4. If no rule matches, fall back to ``default_tier`` (caller-supplied, defaults
   to ``OBSERVE``).

Field resolution supports dot-notation against the TaskPacket row attributes.
Examples:
  ``complexity_index.score``  → ``packet.complexity_index["score"]``
  ``risk_flags.security``     → ``packet.risk_flags["security"]``
  ``loopback_count``          → ``packet.loopback_count``
  ``repo``                    → ``packet.repo``
"""

from __future__ import annotations

import fnmatch
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.dashboard.models.trust_config import (
    AssignedTier,
    ConditionOperator,
    RuleCondition,
    TrustTierRuleRead,
    get_safety_bounds,
    list_rules,
)
from src.models.taskpacket import TaskPacketRow

__all__ = ["evaluate_trust_tier", "EvaluationResult"]

log = logging.getLogger(__name__)

# Tiers ordered by restrictiveness — used to cap tier by safety bounds.
_TIER_ORDER: list[AssignedTier] = [
    AssignedTier.OBSERVE,
    AssignedTier.SUGGEST,
    AssignedTier.EXECUTE,
]


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------


class EvaluationResult:
    """Outcome of a trust-tier evaluation.

    Attributes:
        tier: Final assigned tier after rules + safety bounds.
        matched_rule_id: UUID of the first-matching rule, or ``None`` if the
            default tier was used.
        safety_capped: ``True`` when a safety bound reduced the tier.
        reason: Human-readable explanation for audit logging.
    """

    def __init__(
        self,
        tier: AssignedTier,
        *,
        matched_rule_id: Any | None = None,
        safety_capped: bool = False,
        reason: str = "",
    ) -> None:
        self.tier = tier
        self.matched_rule_id = matched_rule_id
        self.safety_capped = safety_capped
        self.reason = reason

    def __repr__(self) -> str:
        return (
            f"EvaluationResult(tier={self.tier!r}, "
            f"matched_rule_id={self.matched_rule_id!r}, "
            f"safety_capped={self.safety_capped!r})"
        )


# ---------------------------------------------------------------------------
# Primary entry point
# ---------------------------------------------------------------------------


async def evaluate_trust_tier(
    session: AsyncSession,
    packet: TaskPacketRow,
    *,
    default_tier: AssignedTier = AssignedTier.OBSERVE,
) -> EvaluationResult:
    """Evaluate trust-tier rules against *packet* and return the result.

    Args:
        session: Active database session (read-only within this function).
        packet: The ``TaskPacketRow`` whose metadata drives evaluation.
        default_tier: Tier to assign when no rule matches (defaults to OBSERVE).

    Returns:
        :class:`EvaluationResult` with final tier, matched rule, and flags.
    """
    rules = await list_rules(session, active_only=True)
    bounds = await get_safety_bounds(session)

    matched_tier: AssignedTier = default_tier
    matched_rule_id: Any | None = None
    match_reason: str = f"no rule matched — using default tier '{default_tier}'"

    for rule in rules:
        if _rule_matches(rule, packet):
            matched_tier = rule.assigned_tier
            matched_rule_id = rule.id
            match_reason = (
                f"rule {rule.id} (priority={rule.priority}) matched — "
                f"assigned tier '{rule.assigned_tier}'"
            )
            log.debug(match_reason)
            break

    # --- Safety bounds cap -----------------------------------------------
    safety_capped = False
    cap_reasons: list[str] = []

    # 1. Loopback count exceeds max_loopbacks → cap at SUGGEST
    if bounds.max_loopbacks is not None and packet.loopback_count > bounds.max_loopbacks:
        cap_reasons.append(
            f"loopback_count={packet.loopback_count} > max_loopbacks={bounds.max_loopbacks}"
        )

    # 2. Diff lines exceed max_auto_merge_lines → cap at SUGGEST
    #    Scope may carry a ``diff_lines`` or ``changed_lines`` key.
    diff_lines = _scope_int(packet, "diff_lines") or _scope_int(packet, "changed_lines")
    if diff_lines is not None and bounds.max_auto_merge_lines is not None:
        if diff_lines > bounds.max_auto_merge_lines:
            cap_reasons.append(
                f"diff_lines={diff_lines} > max_auto_merge_lines={bounds.max_auto_merge_lines}"
            )

    # 3. Repo matches a mandatory-review pattern → cap at SUGGEST
    for pattern in bounds.mandatory_review_patterns:
        if fnmatch.fnmatch(packet.repo, pattern):
            cap_reasons.append(
                f"repo '{packet.repo}' matches mandatory-review pattern '{pattern}'"
            )
            break

    if cap_reasons:
        capped = _cap_tier(matched_tier, AssignedTier.SUGGEST)
        if capped != matched_tier:
            safety_capped = True
            match_reason = (
                f"{match_reason}; safety bounds capped tier to '{capped}' "
                f"because: {'; '.join(cap_reasons)}"
            )
            log.info(
                "Trust tier capped by safety bounds",
                extra={
                    "original_tier": matched_tier,
                    "capped_tier": capped,
                    "reasons": cap_reasons,
                    "task_id": str(packet.id),
                },
            )
            matched_tier = capped

    return EvaluationResult(
        matched_tier,
        matched_rule_id=matched_rule_id,
        safety_capped=safety_capped,
        reason=match_reason,
    )


# ---------------------------------------------------------------------------
# Rule / condition evaluation
# ---------------------------------------------------------------------------


def _rule_matches(rule: TrustTierRuleRead, packet: TaskPacketRow) -> bool:
    """Return True when ALL conditions in *rule* are satisfied by *packet*."""
    for condition in rule.conditions:
        if not _condition_matches(condition, packet):
            return False
    return True  # vacuously true when conditions list is empty


def _condition_matches(condition: RuleCondition, packet: TaskPacketRow) -> bool:
    """Evaluate a single condition against the packet.

    Returns ``False`` on any resolution or type error to ensure rules fail
    safely (i.e. a broken rule never grants unintended access).
    """
    try:
        actual = _resolve_field(packet, condition.field)
    except (KeyError, TypeError, AttributeError) as exc:
        log.debug(
            "Could not resolve field '%s' on packet %s: %s",
            condition.field,
            packet.id,
            exc,
        )
        return False

    return _apply_operator(condition.op, actual, condition.value)


def _apply_operator(op: ConditionOperator, actual: Any, expected: Any) -> bool:
    """Apply *op* comparison between *actual* (from packet) and *expected* (from rule)."""
    try:
        match op:
            case ConditionOperator.EQUALS:
                return actual == expected
            case ConditionOperator.NOT_EQUALS:
                return actual != expected
            case ConditionOperator.LESS_THAN:
                return float(actual) < float(expected)
            case ConditionOperator.GREATER_THAN:
                return float(actual) > float(expected)
            case ConditionOperator.CONTAINS:
                # Works for str (substring) and list/set (membership).
                if isinstance(actual, (list, set, tuple)):
                    return expected in actual
                return str(expected) in str(actual)
            case ConditionOperator.MATCHES_GLOB:
                return fnmatch.fnmatch(str(actual), str(expected))
    except (TypeError, ValueError) as exc:
        log.debug("Operator '%s' failed: %s", op, exc)
        return False
    return False  # unreachable; satisfies type checker


# ---------------------------------------------------------------------------
# Field resolution helpers
# ---------------------------------------------------------------------------


def _resolve_field(packet: TaskPacketRow, field: str) -> Any:
    """Resolve a dot-separated *field* path against *packet*.

    The first segment is always a TaskPacketRow attribute.  Subsequent
    segments navigate into nested dicts.

    Raises ``AttributeError`` / ``KeyError`` / ``TypeError`` on failure.
    """
    parts = field.split(".", maxsplit=1)
    root_attr = parts[0]
    value: Any = getattr(packet, root_attr)  # raises AttributeError if missing

    if len(parts) == 2 and parts[1]:
        sub_path = parts[1]
        for key in sub_path.split("."):
            if not isinstance(value, dict):
                raise TypeError(
                    f"Expected dict at '{root_attr}' when traversing '{field}', "
                    f"got {type(value).__name__}"
                )
            value = value[key]  # raises KeyError if missing

    return value


def _scope_int(packet: TaskPacketRow, key: str) -> int | None:
    """Safely extract an integer value from ``packet.scope``."""
    if not isinstance(packet.scope, dict):
        return None
    raw = packet.scope.get(key)
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Tier cap helper
# ---------------------------------------------------------------------------


def _cap_tier(tier: AssignedTier, max_tier: AssignedTier) -> AssignedTier:
    """Return the more restrictive of *tier* and *max_tier*.

    Lower index in ``_TIER_ORDER`` is more restrictive (OBSERVE < SUGGEST < EXECUTE).
    """
    tier_idx = _TIER_ORDER.index(tier) if tier in _TIER_ORDER else len(_TIER_ORDER)
    max_idx = _TIER_ORDER.index(max_tier) if max_tier in _TIER_ORDER else len(_TIER_ORDER)
    return _TIER_ORDER[min(tier_idx, max_idx)]
