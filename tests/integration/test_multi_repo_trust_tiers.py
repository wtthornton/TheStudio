"""Integration tests for per-repo trust tier rule scoping (Epic 41, Story 41.9).

Verifies that trust tier rules scoped to specific repos via the ``repo`` field
condition produce independent tier assignments:
- A rule for Repo A does not affect Repo B
- A rule for Repo B does not affect Repo A
- The correct rule fires for each repo
- The default tier is used when no repo-specific rule matches

These tests mock ``list_rules`` and ``get_safety_bounds`` so they can run without
a live PostgreSQL instance while still exercising the full rule engine logic.
"""

from __future__ import annotations

from datetime import datetime, timezone
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
from src.dashboard.trust_engine import evaluate_trust_tier
from src.models.taskpacket import TaskPacketRow, TaskPacketStatus

pytestmark = pytest.mark.integration

_NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rule(
    *,
    priority: int,
    repo: str | None = None,
    complexity_lt: float | None = None,
    assigned_tier: AssignedTier,
    active: bool = True,
    description: str | None = None,
) -> TrustTierRuleRead:
    """Build a TrustTierRuleRead with optional repo and complexity conditions."""
    conditions: list[RuleCondition] = []
    if repo is not None:
        conditions.append(
            RuleCondition(field="repo", op=ConditionOperator.EQUALS, value=repo)
        )
    if complexity_lt is not None:
        conditions.append(
            RuleCondition(
                field="complexity_index.score",
                op=ConditionOperator.LESS_THAN,
                value=complexity_lt,
            )
        )
    return TrustTierRuleRead(
        id=uuid4(),
        priority=priority,
        conditions=conditions,
        assigned_tier=assigned_tier,
        active=active,
        description=description,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _make_packet(
    repo: str,
    complexity_score: float = 0.3,
) -> TaskPacketRow:
    """Build a minimal TaskPacketRow for trust evaluation."""
    row = MagicMock(spec=TaskPacketRow)
    row.repo = repo
    row.complexity_index = {"score": complexity_score, "band": "low"}
    row.risk_flags = {}
    row.loopback_count = 0
    row.status = TaskPacketStatus.RECEIVED
    return row


def _empty_bounds() -> SafeBoundsRead:
    return SafeBoundsRead(
        max_auto_merge_lines=None,
        max_auto_merge_cost=None,
        max_loopbacks=None,
        mandatory_review_patterns=[],
        updated_at=_NOW,
    )


# ---------------------------------------------------------------------------
# Context manager for mocking trust engine DB calls
# ---------------------------------------------------------------------------


def _patched_trust_engine(rules: list[TrustTierRuleRead]):
    """Return a context manager that mocks list_rules + get_safety_bounds."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        with (
            patch(
                "src.dashboard.trust_engine.list_rules",
                new=AsyncMock(return_value=rules),
            ),
            patch(
                "src.dashboard.trust_engine.get_safety_bounds",
                new=AsyncMock(return_value=_empty_bounds()),
            ),
        ):
            yield

    return _ctx()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def session():
    return AsyncMock()


@pytest.fixture
def rule_repo_a_observe() -> TrustTierRuleRead:
    return _make_rule(
        priority=10,
        repo="test-org-a/repo-alpha",
        assigned_tier=AssignedTier.OBSERVE,
        description="Force repo-alpha to OBSERVE",
    )


@pytest.fixture
def rule_repo_b_suggest() -> TrustTierRuleRead:
    return _make_rule(
        priority=10,
        repo="test-org-b/repo-beta",
        assigned_tier=AssignedTier.SUGGEST,
        description="Allow repo-beta to SUGGEST",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPerRepoTrustTierScoping:
    """Trust tier rules scoped by repo field produce isolated tier assignments."""

    async def test_repo_a_rule_does_not_affect_repo_b(
        self, session, rule_repo_a_observe: TrustTierRuleRead
    ) -> None:
        """OBSERVE rule for repo-alpha does not match repo-beta packets."""
        packet_b = _make_packet("test-org-b/repo-beta")

        with _patched_trust_engine([rule_repo_a_observe]):
            result = await evaluate_trust_tier(
                session=session,
                packet=packet_b,
                default_tier=AssignedTier.OBSERVE,
            )

        assert result.tier == AssignedTier.OBSERVE
        assert result.matched_rule_id is None  # no match → default

    async def test_repo_b_rule_does_not_affect_repo_a(
        self, session, rule_repo_b_suggest: TrustTierRuleRead
    ) -> None:
        """SUGGEST rule for repo-beta does not elevate repo-alpha."""
        packet_a = _make_packet("test-org-a/repo-alpha")

        with _patched_trust_engine([rule_repo_b_suggest]):
            result = await evaluate_trust_tier(
                session=session,
                packet=packet_a,
                default_tier=AssignedTier.OBSERVE,
            )

        assert result.tier == AssignedTier.OBSERVE
        assert result.matched_rule_id is None

    async def test_correct_rule_fires_for_each_repo(self, session) -> None:
        """With two per-repo rules, each repo gets its own assigned tier."""
        rule_a = _make_rule(
            priority=10, repo="org/repo-a", assigned_tier=AssignedTier.OBSERVE
        )
        rule_b = _make_rule(
            priority=20, repo="org/repo-b", assigned_tier=AssignedTier.SUGGEST
        )
        rules = [rule_a, rule_b]

        packet_a = _make_packet("org/repo-a")
        packet_b = _make_packet("org/repo-b")

        with _patched_trust_engine(rules):
            result_a = await evaluate_trust_tier(
                session=session, packet=packet_a, default_tier=AssignedTier.OBSERVE
            )
        with _patched_trust_engine(rules):
            result_b = await evaluate_trust_tier(
                session=session, packet=packet_b, default_tier=AssignedTier.OBSERVE
            )

        assert result_a.tier == AssignedTier.OBSERVE
        assert result_a.matched_rule_id == rule_a.id

        assert result_b.tier == AssignedTier.SUGGEST
        assert result_b.matched_rule_id == rule_b.id

    async def test_conditional_rule_fires_only_when_complexity_low(
        self, session
    ) -> None:
        """Repo rule with complexity condition fires only when score < 0.5."""
        rule = _make_rule(
            priority=10,
            repo="org/repo-b",
            complexity_lt=0.5,
            assigned_tier=AssignedTier.SUGGEST,
        )

        packet_low = _make_packet("org/repo-b", complexity_score=0.3)
        packet_high = _make_packet("org/repo-b", complexity_score=0.8)

        with _patched_trust_engine([rule]):
            result_low = await evaluate_trust_tier(
                session=session, packet=packet_low, default_tier=AssignedTier.OBSERVE
            )
        with _patched_trust_engine([rule]):
            result_high = await evaluate_trust_tier(
                session=session, packet=packet_high, default_tier=AssignedTier.OBSERVE
            )

        assert result_low.tier == AssignedTier.SUGGEST
        assert result_high.tier == AssignedTier.OBSERVE  # complexity too high → default

    async def test_default_tier_used_when_no_rule_matches(self, session) -> None:
        """When no rules exist, the caller-supplied default tier is returned."""
        packet = _make_packet("unknown-org/unknown-repo")

        with _patched_trust_engine([]):
            result = await evaluate_trust_tier(
                session=session, packet=packet, default_tier=AssignedTier.OBSERVE
            )

        assert result.tier == AssignedTier.OBSERVE
        assert result.matched_rule_id is None

    async def test_glob_rule_matches_entire_org(self, session) -> None:
        """A glob rule 'acme-corp/*' matches all repos under acme-corp."""
        glob_rule = TrustTierRuleRead(
            id=uuid4(),
            priority=100,
            conditions=[
                RuleCondition(
                    field="repo",
                    op=ConditionOperator.MATCHES_GLOB,
                    value="acme-corp/*",
                )
            ],
            assigned_tier=AssignedTier.SUGGEST,
            active=True,
            description="Cap entire acme-corp org at SUGGEST",
            created_at=_NOW,
            updated_at=_NOW,
        )

        for repo in ("acme-corp/backend-api", "acme-corp/frontend"):
            packet = _make_packet(repo)
            with _patched_trust_engine([glob_rule]):
                result = await evaluate_trust_tier(
                    session=session, packet=packet, default_tier=AssignedTier.OBSERVE
                )
            assert result.tier == AssignedTier.SUGGEST, f"Expected SUGGEST for {repo}"

        # Repo outside the org should fall through
        other = _make_packet("other-org/something")
        with _patched_trust_engine([glob_rule]):
            result_other = await evaluate_trust_tier(
                session=session, packet=other, default_tier=AssignedTier.OBSERVE
            )
        assert result_other.tier == AssignedTier.OBSERVE

    async def test_priority_order_specific_rule_beats_glob(self, session) -> None:
        """A high-priority repo-specific OBSERVE rule beats a lower-priority glob SUGGEST."""
        specific_rule = TrustTierRuleRead(
            id=uuid4(),
            priority=10,
            conditions=[
                RuleCondition(
                    field="repo", op=ConditionOperator.EQUALS, value="org/repo-alpha"
                )
            ],
            assigned_tier=AssignedTier.OBSERVE,
            active=True,
            description="Force repo-alpha to OBSERVE",
            created_at=_NOW,
            updated_at=_NOW,
        )
        glob_rule = TrustTierRuleRead(
            id=uuid4(),
            priority=100,
            conditions=[
                RuleCondition(
                    field="repo", op=ConditionOperator.MATCHES_GLOB, value="org/*"
                )
            ],
            assigned_tier=AssignedTier.SUGGEST,
            active=True,
            description="Promote all org/* to SUGGEST",
            created_at=_NOW,
            updated_at=_NOW,
        )
        rules = [specific_rule, glob_rule]

        packet_alpha = _make_packet("org/repo-alpha")
        packet_beta = _make_packet("org/repo-beta")

        with _patched_trust_engine(rules):
            result_alpha = await evaluate_trust_tier(
                session=session, packet=packet_alpha, default_tier=AssignedTier.OBSERVE
            )
        with _patched_trust_engine(rules):
            result_beta = await evaluate_trust_tier(
                session=session, packet=packet_beta, default_tier=AssignedTier.OBSERVE
            )

        # specific rule wins for repo-alpha (priority 10 beats 100)
        assert result_alpha.tier == AssignedTier.OBSERVE
        assert result_alpha.matched_rule_id == specific_rule.id

        # glob rule matches repo-beta (falls through specific rule)
        assert result_beta.tier == AssignedTier.SUGGEST
        assert result_beta.matched_rule_id == glob_rule.id
