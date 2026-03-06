"""Unit tests for Expert Router (Story 1.3, updated Story 2.7)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.experts.expert import ExpertClass, ExpertRead, LifecycleState, TrustTier
from src.intake.effective_role import BaseRole, EffectiveRolePolicy, Overlay
from src.reputation.models import DriftSignal, WeightQueryResult
from src.reputation.models import TrustTier as RepTrustTier
from src.routing.router import (
    DEFAULT_REPUTATION_CONFIDENCE,
    DEFAULT_REPUTATION_WEIGHT,
    _compute_selection_score,
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


# --- Story 2.7: Reputation-aware selection tests ---


def _make_weight_result(
    expert_id: UUID,
    weight: float,
    confidence: float,
) -> WeightQueryResult:
    """Helper to create a WeightQueryResult for testing."""
    return WeightQueryResult(
        expert_id=expert_id,
        expert_version=1,
        context_key="test-repo:mixed:medium",
        weight=weight,
        confidence=confidence,
        trust_tier=RepTrustTier.PROBATION,
        drift_signal=DriftSignal.STABLE,
    )


class TestSelectionScore:
    """Tests for _compute_selection_score function."""

    def test_trusted_base_score(self) -> None:
        score = _compute_selection_score(TrustTier.TRUSTED, 0.5, 0.0)
        assert score == 3.0

    def test_probation_base_score(self) -> None:
        score = _compute_selection_score(TrustTier.PROBATION, 0.5, 0.0)
        assert score == 2.0

    def test_reputation_adjusts_score(self) -> None:
        # High weight with high confidence increases score
        base = _compute_selection_score(TrustTier.PROBATION, 0.5, 0.0)
        boosted = _compute_selection_score(TrustTier.PROBATION, 0.8, 0.9)
        assert boosted > base

    def test_low_confidence_dampens_weight(self) -> None:
        # Same weight, different confidence
        high_conf = _compute_selection_score(TrustTier.PROBATION, 0.8, 0.9)
        low_conf = _compute_selection_score(TrustTier.PROBATION, 0.8, 0.1)
        assert high_conf > low_conf

    def test_score_formula_correct(self) -> None:
        # Formula: trust_tier_score * (1 + weight * confidence)
        score = _compute_selection_score(TrustTier.TRUSTED, 0.8, 0.5)
        expected = 3.0 * (1 + 0.8 * 0.5)
        assert abs(score - expected) < 0.001


class TestRouterReputationIntegration:
    """Router uses reputation weights in expert selection."""

    def test_selection_includes_reputation_fields(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        sec = _make_expert("sec", ExpertClass.SECURITY)
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)

        def lookup(expert_id: UUID, repo: str | None) -> WeightQueryResult | None:
            if expert_id == sec.id:
                return _make_weight_result(expert_id, 0.75, 0.8)
            if expert_id == qa.id:
                return _make_weight_result(expert_id, 0.6, 0.5)
            return None

        plan = route(
            policy,
            risk_flags=None,
            available_experts=[sec, qa],
            reputation_lookup=lookup,
        )
        sec_sel = [s for s in plan.selections if s.expert_class == ExpertClass.SECURITY]
        assert len(sec_sel) == 1
        assert sec_sel[0].reputation_weight == 0.75
        assert sec_sel[0].reputation_confidence == 0.8
        assert sec_sel[0].selection_score > 0

    def test_high_confidence_expert_preferred(self) -> None:
        """Higher confidence expert wins even with same trust tier."""
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        sec_low_conf = _make_expert("sec-low", ExpertClass.SECURITY, TrustTier.PROBATION)
        sec_high_conf = _make_expert("sec-high", ExpertClass.SECURITY, TrustTier.PROBATION)
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)

        def lookup(expert_id: UUID, repo: str | None) -> WeightQueryResult | None:
            if expert_id == sec_low_conf.id:
                return _make_weight_result(expert_id, 0.7, 0.2)  # Low confidence
            if expert_id == sec_high_conf.id:
                return _make_weight_result(expert_id, 0.7, 0.9)  # High confidence
            if expert_id == qa.id:
                return _make_weight_result(expert_id, 0.5, 0.5)
            return None

        plan = route(
            policy,
            risk_flags=None,
            available_experts=[sec_low_conf, sec_high_conf, qa],
            reputation_lookup=lookup,
        )
        sec_sel = [s for s in plan.selections if s.expert_class == ExpertClass.SECURITY]
        assert len(sec_sel) == 1
        assert sec_sel[0].expert_id == sec_high_conf.id

    def test_low_confidence_flagged_in_rationale(self) -> None:
        """Experts with confidence < 0.3 are flagged as probationary selection."""
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        sec = _make_expert("sec", ExpertClass.SECURITY)
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)

        def lookup(expert_id: UUID, repo: str | None) -> WeightQueryResult | None:
            if expert_id == sec.id:
                return _make_weight_result(expert_id, 0.6, 0.1)  # Below threshold
            if expert_id == qa.id:
                return _make_weight_result(expert_id, 0.5, 0.8)  # Above threshold
            return None

        plan = route(
            policy,
            risk_flags=None,
            available_experts=[sec, qa],
            reputation_lookup=lookup,
        )
        assert "probationary selection" in plan.rationale
        assert "low confidence" in plan.rationale

    def test_rationale_includes_reputation_info(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        sec = _make_expert("sec", ExpertClass.SECURITY)
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)

        def lookup(expert_id: UUID, repo: str | None) -> WeightQueryResult | None:
            if expert_id == sec.id:
                return _make_weight_result(expert_id, 0.85, 0.7)
            if expert_id == qa.id:
                return _make_weight_result(expert_id, 0.5, 0.5)
            return None

        plan = route(
            policy,
            risk_flags=None,
            available_experts=[sec, qa],
            reputation_lookup=lookup,
        )
        assert "reputation weight" in plan.rationale
        assert "0.85" in plan.rationale
        assert "confidence" in plan.rationale
        assert "0.70" in plan.rationale

    def test_mandatory_coverage_unaffected_by_reputation(self) -> None:
        """Reputation adjusts within required classes, not across them."""
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        sec = _make_expert("sec", ExpertClass.SECURITY, TrustTier.PROBATION)
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION, TrustTier.TRUSTED)

        def lookup(expert_id: UUID, repo: str | None) -> WeightQueryResult | None:
            if expert_id == sec.id:
                return _make_weight_result(expert_id, 0.3, 0.2)  # Low score
            if expert_id == qa.id:
                return _make_weight_result(expert_id, 0.9, 0.9)  # High score
            return None

        plan = route(
            policy,
            risk_flags=None,
            available_experts=[sec, qa],
            reputation_lookup=lookup,
        )
        classes = {s.expert_class for s in plan.selections}
        assert ExpertClass.SECURITY in classes
        assert ExpertClass.QA_VALIDATION in classes

    def test_missing_weight_uses_defaults(self) -> None:
        """Experts with no reputation history get default values."""
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        sec = _make_expert("sec", ExpertClass.SECURITY)
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)

        def lookup(expert_id: UUID, repo: str | None) -> WeightQueryResult | None:
            return None  # No reputation data for any expert

        plan = route(
            policy,
            risk_flags=None,
            available_experts=[sec, qa],
            reputation_lookup=lookup,
        )
        for selection in plan.selections:
            assert selection.reputation_weight == DEFAULT_REPUTATION_WEIGHT
            assert selection.reputation_confidence == DEFAULT_REPUTATION_CONFIDENCE

    def test_no_lookup_uses_defaults(self) -> None:
        """Without reputation_lookup, defaults are used."""
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        sec = _make_expert("sec", ExpertClass.SECURITY)
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)
        plan = route(
            policy,
            risk_flags=None,
            available_experts=[sec, qa],
        )
        for selection in plan.selections:
            assert selection.reputation_weight == DEFAULT_REPUTATION_WEIGHT
            assert selection.reputation_confidence == DEFAULT_REPUTATION_CONFIDENCE

    def test_ranking_by_selection_score(self) -> None:
        """Candidates within a class are ranked by selection score."""
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        sec_bad = _make_expert("sec-bad", ExpertClass.SECURITY, TrustTier.PROBATION)
        sec_good = _make_expert("sec-good", ExpertClass.SECURITY, TrustTier.PROBATION)
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)

        def lookup(expert_id: UUID, repo: str | None) -> WeightQueryResult | None:
            if expert_id == sec_bad.id:
                return _make_weight_result(expert_id, 0.3, 0.5)  # Lower score
            if expert_id == sec_good.id:
                return _make_weight_result(expert_id, 0.9, 0.9)  # Higher score
            if expert_id == qa.id:
                return _make_weight_result(expert_id, 0.5, 0.5)
            return None

        plan = route(
            policy,
            risk_flags=None,
            available_experts=[sec_bad, sec_good, qa],
            reputation_lookup=lookup,
        )
        sec_sel = [s for s in plan.selections if s.expert_class == ExpertClass.SECURITY]
        assert len(sec_sel) == 1
        assert sec_sel[0].expert_id == sec_good.id


class TestRouterReputationWithRepo:
    """Router passes repo to reputation lookup."""

    def test_repo_passed_to_lookup(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        sec = _make_expert("sec", ExpertClass.SECURITY)
        qa = _make_expert("qa", ExpertClass.QA_VALIDATION)
        captured_repos: list[str | None] = []

        def lookup(expert_id: UUID, repo: str | None) -> WeightQueryResult | None:
            captured_repos.append(repo)
            return _make_weight_result(expert_id, 0.5, 0.5)

        route(
            policy,
            risk_flags=None,
            available_experts=[sec, qa],
            reputation_lookup=lookup,
            repo="my-repo",
        )
        assert all(r == "my-repo" for r in captured_repos)
