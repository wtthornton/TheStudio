"""Unit tests for EffectiveRolePolicy enforcement (Story 1.12).

Tests policy computation, tool allowlists, verification/QA strictness,
publishing posture, and downstream consumption at Router.
"""

from datetime import UTC, datetime
from uuid import uuid4

from src.experts.expert import ExpertClass, ExpertRead, TrustTier
from src.intake.effective_role import (
    BaseRole,
    EffectiveRolePolicy,
    Overlay,
    PublishingPosture,
    QAStrictness,
    VerificationStrictness,
)
from src.routing.router import route

# --- Policy Computation ---


class TestPolicyComputation:
    def test_developer_defaults(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [])
        assert policy.base_role == BaseRole.DEVELOPER
        assert policy.overlays == ()
        assert policy.requires_human_review is False
        assert "Read" in policy.tool_allowlist
        assert "Write" in policy.tool_allowlist
        assert "Edit" in policy.tool_allowlist
        assert "Bash" in policy.tool_allowlist
        assert policy.verification_strictness == VerificationStrictness.STANDARD
        assert policy.qa_strictness == QAStrictness.STANDARD
        assert policy.publishing_posture == PublishingPosture.READY_AFTER_GATE
        assert policy.max_experts_per_consult == 3

    def test_planner_read_only_tools(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.PLANNER, [])
        assert "Write" not in policy.tool_allowlist
        assert "Edit" not in policy.tool_allowlist
        assert "Bash" not in policy.tool_allowlist
        assert "Read" in policy.tool_allowlist
        assert "Glob" in policy.tool_allowlist
        assert "Grep" in policy.tool_allowlist

    def test_architect_higher_budget(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.ARCHITECT, [])
        assert policy.max_experts_per_consult == 5

    def test_planner_lower_budget(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.PLANNER, [])
        assert policy.max_experts_per_consult == 2


# --- Verification Strictness ---


class TestVerificationStrictness:
    def test_security_overlay_strict_verification(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        assert policy.verification_strictness == VerificationStrictness.STRICT

    def test_compliance_overlay_strict_verification(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.COMPLIANCE])
        assert policy.verification_strictness == VerificationStrictness.STRICT

    def test_migration_overlay_strict_verification(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.MIGRATION])
        assert policy.verification_strictness == VerificationStrictness.STRICT

    def test_infra_overlay_strict_verification(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.INFRA])
        assert policy.verification_strictness == VerificationStrictness.STRICT

    def test_hotfix_overlay_standard_verification(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.HOTFIX])
        assert policy.verification_strictness == VerificationStrictness.STANDARD

    def test_no_overlay_standard_verification(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [])
        assert policy.verification_strictness == VerificationStrictness.STANDARD


# --- QA Strictness ---


class TestQAStrictness:
    def test_security_overlay_strict_qa(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        assert policy.qa_strictness == QAStrictness.STRICT

    def test_partner_api_overlay_strict_qa(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.PARTNER_API])
        assert policy.qa_strictness == QAStrictness.STRICT

    def test_high_risk_overlay_strict_qa(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.HIGH_RISK])
        assert policy.qa_strictness == QAStrictness.STRICT

    def test_hotfix_overlay_standard_qa(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.HOTFIX])
        assert policy.qa_strictness == QAStrictness.STANDARD


# --- Publishing Posture ---


class TestPublishingPosture:
    def test_no_overlays_ready_after_gate(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [])
        assert policy.publishing_posture == PublishingPosture.READY_AFTER_GATE

    def test_security_overlay_draft_only(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        assert policy.publishing_posture == PublishingPosture.DRAFT_ONLY

    def test_compliance_overlay_draft_only(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.COMPLIANCE])
        assert policy.publishing_posture == PublishingPosture.DRAFT_ONLY

    def test_infra_overlay_draft_only(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.INFRA])
        assert policy.publishing_posture == PublishingPosture.DRAFT_ONLY

    def test_migration_draft_only_via_escalation(self) -> None:
        """Migration requires human review -> draft only."""
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.MIGRATION])
        assert policy.publishing_posture == PublishingPosture.DRAFT_ONLY

    def test_hotfix_ready_after_gate(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.HOTFIX])
        assert policy.publishing_posture == PublishingPosture.READY_AFTER_GATE

    def test_high_risk_ready_after_gate(self) -> None:
        """HIGH_RISK has strict QA but no escalation, so ready_after_gate."""
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.HIGH_RISK])
        assert policy.publishing_posture == PublishingPosture.READY_AFTER_GATE


# --- Router Consumes Policy Budget ---


class TestRouterPolicyConsumption:
    def _make_expert(self, expert_class: ExpertClass) -> ExpertRead:
        now = datetime.now(UTC)
        return ExpertRead(
            id=uuid4(),
            name=f"test-{expert_class.value}",
            expert_class=expert_class,
            capability_tags=["test"],
            scope_description="Test scope",
            tool_policy={"allowed": ["read"]},
            trust_tier=TrustTier.TRUSTED,
            lifecycle_state="active",
            current_version=1,
            created_at=now,
            updated_at=now,
        )

    def test_router_uses_policy_budget(self) -> None:
        """Router uses max_experts_per_consult from EffectiveRolePolicy."""
        policy = EffectiveRolePolicy.compute(
            BaseRole.DEVELOPER, [Overlay.SECURITY]
        )
        experts = [
            self._make_expert(ExpertClass.SECURITY),
            self._make_expert(ExpertClass.QA_VALIDATION),
        ]
        plan = route(policy, {"risk_security": True}, experts)
        # Developer budget is 3, should select both
        assert len(plan.selections) == 2
        assert plan.budget_remaining == 1

    def test_router_respects_planner_budget(self) -> None:
        """Planner has smaller budget (2)."""
        policy = EffectiveRolePolicy.compute(
            BaseRole.PLANNER, [Overlay.SECURITY]
        )
        experts = [
            self._make_expert(ExpertClass.SECURITY),
            self._make_expert(ExpertClass.QA_VALIDATION),
        ]
        plan = route(policy, {"risk_security": True}, experts)
        assert len(plan.selections) == 2
        assert plan.budget_remaining == 0

    def test_router_override_budget(self) -> None:
        """Explicit max_experts_per_consult overrides policy."""
        policy = EffectiveRolePolicy.compute(
            BaseRole.ARCHITECT, [Overlay.SECURITY]
        )
        experts = [
            self._make_expert(ExpertClass.SECURITY),
            self._make_expert(ExpertClass.QA_VALIDATION),
        ]
        plan = route(policy, {"risk_security": True}, experts, max_experts_per_consult=1)
        assert len(plan.selections) == 1
        assert plan.budget_remaining == 0


# --- Combined Overlay Effects ---


class TestCombinedOverlays:
    def test_multiple_overlays_combine(self) -> None:
        policy = EffectiveRolePolicy.compute(
            BaseRole.DEVELOPER,
            [Overlay.SECURITY, Overlay.PARTNER_API, Overlay.HOTFIX],
        )
        assert Overlay.SECURITY in policy.overlays
        assert Overlay.PARTNER_API in policy.overlays
        assert Overlay.HOTFIX in policy.overlays
        # Security -> strict verification, Partner API -> strict QA
        assert policy.verification_strictness == VerificationStrictness.STRICT
        assert policy.qa_strictness == QAStrictness.STRICT
        # Security -> draft only
        assert policy.publishing_posture == PublishingPosture.DRAFT_ONLY
        # Mandatory experts from both overlays
        assert ExpertClass.SECURITY in policy.mandatory_expert_classes
        assert ExpertClass.PARTNER in policy.mandatory_expert_classes
        assert ExpertClass.QA_VALIDATION in policy.mandatory_expert_classes

    def test_duplicate_overlays_deduplicated(self) -> None:
        policy = EffectiveRolePolicy.compute(
            BaseRole.DEVELOPER,
            [Overlay.SECURITY, Overlay.SECURITY, Overlay.SECURITY],
        )
        assert policy.overlays == (Overlay.SECURITY,)

    def test_frozen_immutability(self) -> None:
        """EffectiveRolePolicy is a frozen dataclass — cannot be modified."""
        import pytest

        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [])
        with pytest.raises(AttributeError):
            policy.base_role = BaseRole.ARCHITECT  # type: ignore[misc]
