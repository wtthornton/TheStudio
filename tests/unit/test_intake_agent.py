"""Unit tests for Intake Agent (Story 1.1)."""

import pytest

from src.experts.expert import ExpertClass
from src.intake.effective_role import (
    ESCALATION_OVERLAYS,
    BaseRole,
    EffectiveRolePolicy,
    Overlay,
)
from src.intake.intake_agent import (
    evaluate_eligibility,
)


class TestEligibility:
    """Test eligibility gate evaluation."""

    def _default_kwargs(self, **overrides) -> dict:  # type: ignore[no-untyped-def]
        defaults = {
            "labels": ["agent:run", "type:bug"],
            "repo": "owner/repo",
            "repo_registered": True,
            "repo_paused": False,
            "has_active_workflow": False,
            "event_id": "evt-001",
        }
        defaults.update(overrides)
        return defaults

    def test_eligible_issue(self) -> None:
        result = evaluate_eligibility(**self._default_kwargs())
        assert result.accepted is True
        assert result.rejection is None
        assert result.effective_role is not None

    def test_reject_missing_agent_run(self) -> None:
        result = evaluate_eligibility(**self._default_kwargs(labels=["type:bug"]))
        assert result.accepted is False
        assert result.rejection is not None
        assert "agent:run" in result.rejection.reason

    def test_reject_unregistered_repo(self) -> None:
        result = evaluate_eligibility(**self._default_kwargs(repo_registered=False))
        assert result.accepted is False
        assert "not registered" in result.rejection.reason  # type: ignore[union-attr]

    def test_reject_paused_repo(self) -> None:
        result = evaluate_eligibility(**self._default_kwargs(repo_paused=True))
        assert result.accepted is False
        assert "paused" in result.rejection.reason  # type: ignore[union-attr]

    def test_reject_active_workflow(self) -> None:
        result = evaluate_eligibility(**self._default_kwargs(has_active_workflow=True))
        assert result.accepted is False
        assert "active workflow" in result.rejection.reason  # type: ignore[union-attr]

    def test_rejection_has_event_id_and_repo(self) -> None:
        result = evaluate_eligibility(**self._default_kwargs(labels=["type:bug"]))
        assert result.rejection is not None
        assert result.rejection.event_id == "evt-001"
        assert result.rejection.repo == "owner/repo"
        assert result.rejection.timestamp is not None


class TestBaseRoleSelection:
    """Test base role selection from issue type labels."""

    def _eval(self, labels: list[str]) -> EffectiveRolePolicy:
        result = evaluate_eligibility(
            labels=["agent:run", *labels],
            repo="owner/repo",
            repo_registered=True,
            repo_paused=False,
            has_active_workflow=False,
            event_id="evt-001",
        )
        assert result.effective_role is not None
        return result.effective_role

    def test_bug_maps_to_developer(self) -> None:
        assert self._eval(["type:bug"]).base_role == BaseRole.DEVELOPER

    def test_feature_maps_to_developer(self) -> None:
        assert self._eval(["type:feature"]).base_role == BaseRole.DEVELOPER

    def test_chore_maps_to_developer(self) -> None:
        assert self._eval(["type:chore"]).base_role == BaseRole.DEVELOPER

    def test_refactor_maps_to_architect(self) -> None:
        assert self._eval(["type:refactor"]).base_role == BaseRole.ARCHITECT

    def test_no_type_defaults_to_developer(self) -> None:
        assert self._eval([]).base_role == BaseRole.DEVELOPER

    def test_docs_maps_to_developer(self) -> None:
        assert self._eval(["type:docs"]).base_role == BaseRole.DEVELOPER


class TestOverlayApplication:
    """Test overlay application from risk labels."""

    def _eval(self, labels: list[str]) -> EffectiveRolePolicy:
        result = evaluate_eligibility(
            labels=["agent:run", "type:bug", *labels],
            repo="owner/repo",
            repo_registered=True,
            repo_paused=False,
            has_active_workflow=False,
            event_id="evt-001",
        )
        assert result.effective_role is not None
        return result.effective_role

    def test_risk_auth_applies_security_overlay(self) -> None:
        policy = self._eval(["risk:auth"])
        assert Overlay.SECURITY in policy.overlays

    def test_risk_compliance_applies_compliance_overlay(self) -> None:
        policy = self._eval(["risk:compliance"])
        assert Overlay.COMPLIANCE in policy.overlays

    def test_risk_billing_applies_billing_overlay(self) -> None:
        policy = self._eval(["risk:billing"])
        assert Overlay.BILLING in policy.overlays

    def test_risk_migration_applies_migration_overlay(self) -> None:
        policy = self._eval(["risk:migration"])
        assert Overlay.MIGRATION in policy.overlays

    def test_risk_partner_api_applies_partner_overlay(self) -> None:
        policy = self._eval(["risk:partner-api"])
        assert Overlay.PARTNER_API in policy.overlays

    def test_risk_infra_applies_infra_overlay(self) -> None:
        policy = self._eval(["risk:infra"])
        assert Overlay.INFRA in policy.overlays

    def test_no_risk_labels_no_overlays(self) -> None:
        policy = self._eval([])
        assert len(policy.overlays) == 0

    def test_multiple_overlays_merge(self) -> None:
        policy = self._eval(["risk:auth", "risk:billing", "risk:compliance"])
        assert Overlay.SECURITY in policy.overlays
        assert Overlay.BILLING in policy.overlays
        assert Overlay.COMPLIANCE in policy.overlays
        assert len(policy.overlays) == 3

    def test_duplicate_risk_labels_deduplicated(self) -> None:
        policy = self._eval(["risk:auth", "risk:auth"])
        assert policy.overlays.count(Overlay.SECURITY) == 1


class TestEffectiveRolePolicy:
    """Test EffectiveRolePolicy computation."""

    def test_compute_no_overlays(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [])
        assert policy.base_role == BaseRole.DEVELOPER
        assert policy.overlays == ()
        assert policy.mandatory_expert_classes == ()
        assert policy.requires_human_review is False

    def test_security_overlay_mandates_security_expert(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        assert ExpertClass.SECURITY in policy.mandatory_expert_classes

    def test_compliance_overlay_mandates_compliance_expert(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.COMPLIANCE])
        assert ExpertClass.COMPLIANCE in policy.mandatory_expert_classes

    def test_billing_overlay_mandates_business_expert(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.BILLING])
        assert ExpertClass.BUSINESS in policy.mandatory_expert_classes

    def test_any_overlay_mandates_qa_validation(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.INFRA])
        assert ExpertClass.QA_VALIDATION in policy.mandatory_expert_classes

    def test_escalation_overlays_require_human_review(self) -> None:
        for overlay in ESCALATION_OVERLAYS:
            policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [overlay])
            assert policy.requires_human_review is True, f"{overlay} should require human review"

    def test_non_escalation_overlay_no_human_review(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.INFRA])
        assert policy.requires_human_review is False

    def test_policy_is_frozen(self) -> None:
        policy = EffectiveRolePolicy.compute(BaseRole.DEVELOPER, [Overlay.SECURITY])
        with pytest.raises(AttributeError):
            policy.base_role = BaseRole.ARCHITECT  # type: ignore[misc]

    def test_multiple_overlays_collect_all_mandatory_experts(self) -> None:
        policy = EffectiveRolePolicy.compute(
            BaseRole.DEVELOPER, [Overlay.SECURITY, Overlay.BILLING]
        )
        assert ExpertClass.SECURITY in policy.mandatory_expert_classes
        assert ExpertClass.BUSINESS in policy.mandatory_expert_classes
        assert ExpertClass.QA_VALIDATION in policy.mandatory_expert_classes
