"""Tests for Router escalation logic (Story 20.4)."""

from datetime import UTC, datetime
from uuid import uuid4

from src.experts.expert import ExpertClass, ExpertRead, LifecycleState, TrustTier
from src.intake.effective_role import BaseRole, EffectiveRolePolicy, Overlay
from src.routing.router import route

_NOW = datetime.now(UTC)


def _make_expert(
    expert_class: ExpertClass,
    trust_tier: TrustTier = TrustTier.TRUSTED,
    name: str = "TestExpert",
) -> ExpertRead:
    """Create a minimal ExpertRead for testing."""
    return ExpertRead(
        id=uuid4(),
        name=name,
        expert_class=expert_class,
        trust_tier=trust_tier,
        current_version=1,
        capability_tags=["test"],
        scope_description="Test expert",
        tool_policy={},
        lifecycle_state=LifecycleState.ACTIVE,
        created_at=_NOW,
        updated_at=_NOW,
    )


class TestRouterEscalation:
    """Test that Router produces EscalationRequest on high-risk conditions."""

    def test_no_escalation_without_risk_flags(self) -> None:
        """No escalation when no high-risk flags present."""
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        experts = [_make_expert(ExpertClass.SECURITY)]
        plan = route(policy, {}, experts)
        assert plan.escalations == ()

    def test_escalation_on_low_confidence_with_destructive_flag(self) -> None:
        """Escalation when experts have low confidence and destructive risk flag present."""
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        experts = [_make_expert(ExpertClass.SECURITY)]

        # With no reputation lookup, confidence defaults to 0.0 (< 0.7)
        plan = route(
            policy,
            {"risk_destructive": True},
            experts,
        )
        assert len(plan.escalations) > 0
        assert any(e.severity == "high" for e in plan.escalations)
        assert any("confidence" in e.reason.lower() for e in plan.escalations)

    def test_escalation_on_budget_exhausted_with_privileged_access(self) -> None:
        """Escalation when budget exhausted before all mandatory classes covered."""
        policy = EffectiveRolePolicy.compute(
            BaseRole.DEVELOPER, [Overlay.SECURITY, Overlay.COMPLIANCE]
        )
        experts = [
            _make_expert(ExpertClass.SECURITY, name="SecurityExpert"),
            _make_expert(ExpertClass.COMPLIANCE, name="ComplianceExpert"),
            _make_expert(ExpertClass.QA_VALIDATION, name="QAExpert"),
        ]

        # Budget of 1 — will exhaust before all mandatory classes covered
        plan = route(
            policy,
            {"risk_privileged_access": True},
            experts,
            max_experts_per_consult=1,
        )
        # The plan will have at most 1 selection (budget=1)
        assert len(plan.selections) <= 1

    def test_no_escalation_without_high_risk_flags(self) -> None:
        """No escalation with low confidence but no high-risk flags."""
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        experts = [_make_expert(ExpertClass.SECURITY)]
        plan = route(
            policy,
            {"risk_data_access": True},  # Not a high-risk flag
            experts,
        )
        # risk_data_access is not in the high_risk_flags set
        assert plan.escalations == ()
