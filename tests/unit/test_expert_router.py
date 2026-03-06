"""Unit tests for Expert Router (Story 1.3)."""

from datetime import UTC, datetime
from uuid import uuid4

from src.experts.expert import ExpertClass, ExpertRead, LifecycleState, TrustTier
from src.intake.effective_role import BaseRole, EffectiveRolePolicy, Overlay
from src.routing.router import (
    route,
)


def _make_expert(
    name: str = "test-expert",
    expert_class: ExpertClass = ExpertClass.SECURITY,
    trust_tier: TrustTier = TrustTier.PROBATION,
    capability_tags: list[str] | None = None,
) -> ExpertRead:
    """Helper to create an ExpertRead for testing."""
    return ExpertRead(
        id=uuid4(),
        name=name,
        expert_class=expert_class,
        capability_tags=capability_tags or ["auth"],
        scope_description="test",
        tool_policy={},
        trust_tier=trust_tier,
        lifecycle_state=LifecycleState.ACTIVE,
        current_version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestRouterNoRiskFlags:
    """Router with no risk flags and no mandatory coverage."""

    def test_no_overlays_returns_empty_plan(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [])
        plan = route(policy, risk_flags=None, available_experts=[])
        assert plan.selections == ()
        assert plan.recruiter_requests == ()
        assert plan.budget_remaining == 3

    def test_no_overlays_no_risk_flags(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [])
        plan = route(policy, risk_flags={}, available_experts=[])
        assert plan.selections == ()


class TestRouterMandatoryCoverage:
    """Router enforces mandatory expert coverage from overlays."""

    def test_security_overlay_selects_security_expert(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        expert = _make_expert("sec-expert", ExpertClass.SECURITY)
        qa_expert = _make_expert("qa-expert", ExpertClass.QA_VALIDATION)
        plan = route(policy, risk_flags=None, available_experts=[expert, qa_expert])
        classes = {s.expert_class for s in plan.selections}
        assert ExpertClass.SECURITY in classes

    def test_any_overlay_requires_qa_validation(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.INFRA])
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)
        infra = _make_expert("infra", ExpertClass.TECHNICAL)
        plan = route(policy, risk_flags=None, available_experts=[qa, infra])
        classes = {s.expert_class for s in plan.selections}
        assert ExpertClass.QA_VALIDATION in classes

    def test_billing_overlay_requires_business_expert(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.BILLING])
        biz = _make_expert("biz", ExpertClass.BUSINESS)
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)
        plan = route(policy, risk_flags=None, available_experts=[biz, qa])
        classes = {s.expert_class for s in plan.selections}
        assert ExpertClass.BUSINESS in classes


class TestRouterRecruiterCallback:
    """Router emits Recruiter callback when no eligible expert exists."""

    def test_no_expert_triggers_recruiter_request(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        # Only QA expert available, no security expert
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)
        plan = route(policy, risk_flags=None, available_experts=[qa])
        assert len(plan.recruiter_requests) > 0
        sec_req = [r for r in plan.recruiter_requests if r.expert_class == ExpertClass.SECURITY]
        assert len(sec_req) == 1
        assert "No eligible" in sec_req[0].reason

    def test_recruiter_request_has_capability_tags(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        plan = route(policy, risk_flags=None, available_experts=[])
        sec_req = [r for r in plan.recruiter_requests if r.expert_class == ExpertClass.SECURITY]
        assert len(sec_req) == 1
        assert "auth" in sec_req[0].capability_tags


class TestRouterShadowExclusion:
    """Shadow experts are excluded from auto-selection."""

    def test_shadow_expert_not_selected(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        shadow = _make_expert("shadow-sec", ExpertClass.SECURITY, TrustTier.SHADOW)
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)
        plan = route(policy, risk_flags=None, available_experts=[shadow, qa])
        sec_selections = [s for s in plan.selections if s.expert_class == ExpertClass.SECURITY]
        assert len(sec_selections) == 0
        # Should trigger Recruiter request instead
        sec_req = [r for r in plan.recruiter_requests if r.expert_class == ExpertClass.SECURITY]
        assert len(sec_req) == 1

    def test_probation_expert_is_selected(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        prob = _make_expert("prob-sec", ExpertClass.SECURITY, TrustTier.PROBATION)
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)
        plan = route(policy, risk_flags=None, available_experts=[prob, qa])
        sec_selections = [s for s in plan.selections if s.expert_class == ExpertClass.SECURITY]
        assert len(sec_selections) == 1

    def test_trusted_expert_preferred_over_probation(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        prob = _make_expert("prob-sec", ExpertClass.SECURITY, TrustTier.PROBATION)
        trusted = _make_expert("trusted-sec", ExpertClass.SECURITY, TrustTier.TRUSTED)
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)
        # Put trusted first in the list (as search would rank it)
        plan = route(policy, risk_flags=None, available_experts=[trusted, prob, qa])
        sec_selections = [s for s in plan.selections if s.expert_class == ExpertClass.SECURITY]
        assert len(sec_selections) == 1
        assert sec_selections[0].expert_id == trusted.id


class TestRouterBudget:
    """Router enforces budget limits."""

    def test_budget_limits_total_selections(self) -> None:
        policy = EffectiveRolePolicy.compute(
            BaseRole.DEVELOPER, [Overlay.SECURITY, Overlay.COMPLIANCE, Overlay.BILLING]
        )
        sec = _make_expert("sec", ExpertClass.SECURITY)
        comp = _make_expert("comp", ExpertClass.COMPLIANCE)
        biz = _make_expert("biz", ExpertClass.BUSINESS)
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)
        plan = route(
            policy, risk_flags=None,
            available_experts=[sec, comp, biz, qa],
            max_experts_per_consult=2,
        )
        assert len(plan.selections) <= 2
        assert plan.budget_remaining == 0

    def test_budget_remaining_tracks_correctly(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        sec = _make_expert("sec", ExpertClass.SECURITY)
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)
        plan = route(
            policy, risk_flags=None,
            available_experts=[sec, qa],
            max_experts_per_consult=5,
        )
        assert plan.budget_remaining == 5 - len(plan.selections)


class TestRouterConsultPlan:
    """Test ConsultPlan structure."""

    def test_plan_has_rationale(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        sec = _make_expert("sec", ExpertClass.SECURITY)
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)
        plan = route(policy, risk_flags=None, available_experts=[sec, qa])
        assert len(plan.rationale) > 0
        assert "sec" in plan.rationale

    def test_selection_has_parallel_pattern(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        sec = _make_expert("sec", ExpertClass.SECURITY)
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)
        plan = route(policy, risk_flags=None, available_experts=[sec, qa])
        for selection in plan.selections:
            assert selection.pattern == "parallel"

    def test_selection_includes_expert_version(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        sec = _make_expert("sec", ExpertClass.SECURITY)
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)
        plan = route(policy, risk_flags=None, available_experts=[sec, qa])
        for selection in plan.selections:
            assert selection.expert_version >= 1


class TestRouterRiskFlags:
    """Router uses risk flags to add QA validation requirement."""

    def test_risk_flags_add_qa_requirement(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [])
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)
        plan = route(
            policy,
            risk_flags={"auth": True, "billing": False},
            available_experts=[qa],
        )
        classes = {s.expert_class for s in plan.selections}
        assert ExpertClass.QA_VALIDATION in classes

    def test_all_false_risk_flags_no_qa(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [])
        plan = route(
            policy,
            risk_flags={"auth": False},
            available_experts=[],
        )
        assert plan.selections == ()
