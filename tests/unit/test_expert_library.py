"""Unit tests for Expert Library (Story 1.2)."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.experts.expert import (
    TRUST_TIER_ORDER,
    ExpertClass,
    ExpertCreate,
    ExpertRead,
    ExpertVersionRead,
    LifecycleState,
    TrustTier,
)
from src.experts.seed import SEED_EXPERTS


class TestExpertEnums:
    def test_expert_class_values(self) -> None:
        assert ExpertClass.TECHNICAL == "technical"
        assert ExpertClass.SECURITY == "security"
        assert ExpertClass.QA_VALIDATION == "qa_validation"
        assert len(ExpertClass) == 8

    def test_trust_tier_values(self) -> None:
        assert TrustTier.SHADOW == "shadow"
        assert TrustTier.PROBATION == "probation"
        assert TrustTier.TRUSTED == "trusted"

    def test_lifecycle_state_values(self) -> None:
        assert LifecycleState.ACTIVE == "active"
        assert LifecycleState.DEPRECATED == "deprecated"
        assert LifecycleState.RETIRED == "retired"

    def test_trust_tier_ordering(self) -> None:
        assert TRUST_TIER_ORDER[TrustTier.TRUSTED] > TRUST_TIER_ORDER[TrustTier.PROBATION]
        assert TRUST_TIER_ORDER[TrustTier.PROBATION] > TRUST_TIER_ORDER[TrustTier.SHADOW]

    def test_invalid_expert_class(self) -> None:
        with pytest.raises(ValueError, match="nonexistent"):
            ExpertClass("nonexistent")


class TestExpertCreate:
    def test_valid_create(self) -> None:
        data = ExpertCreate(
            name="test-expert",
            expert_class=ExpertClass.TECHNICAL,
            capability_tags=["auth", "crypto"],
            scope_description="Test expert scope",
        )
        assert data.name == "test-expert"
        assert data.expert_class == ExpertClass.TECHNICAL
        assert data.capability_tags == ["auth", "crypto"]
        assert data.trust_tier == TrustTier.SHADOW
        assert data.tool_policy == {}
        assert data.definition == {}

    def test_create_with_all_fields(self) -> None:
        data = ExpertCreate(
            name="full-expert",
            expert_class=ExpertClass.SECURITY,
            capability_tags=["secrets"],
            scope_description="Full expert",
            tool_policy={"read_only": True},
            trust_tier=TrustTier.PROBATION,
            definition={"scope_boundaries": ["auth"]},
        )
        assert data.trust_tier == TrustTier.PROBATION
        assert data.tool_policy == {"read_only": True}
        assert data.definition == {"scope_boundaries": ["auth"]}

    def test_missing_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            ExpertCreate()  # type: ignore[call-arg]

    def test_missing_name(self) -> None:
        with pytest.raises(ValidationError):
            ExpertCreate(  # type: ignore[call-arg]
                expert_class=ExpertClass.TECHNICAL,
                capability_tags=["x"],
                scope_description="test",
            )


class TestExpertRead:
    def test_from_attributes(self) -> None:
        fake_id = uuid4()
        row = type(
            "FakeRow", (), {
                "id": fake_id, "name": "test",
                "expert_class": ExpertClass.TECHNICAL,
                "capability_tags": ["auth"], "scope_description": "test",
                "tool_policy": {}, "trust_tier": TrustTier.SHADOW,
                "lifecycle_state": LifecycleState.ACTIVE, "current_version": 1,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            },
        )()
        result = ExpertRead.model_validate(row, from_attributes=True)
        assert result.id == fake_id
        assert result.name == "test"
        assert result.lifecycle_state == LifecycleState.ACTIVE


class TestExpertVersionRead:
    def test_from_attributes(self) -> None:
        eid = uuid4()
        row = type(
            "FakeRow", (), {
                "id": uuid4(), "expert_id": eid, "version": 1,
                "definition": {"scope_boundaries": ["auth"]},
                "created_at": "2026-01-01T00:00:00+00:00",
            },
        )()
        result = ExpertVersionRead.model_validate(row, from_attributes=True)
        assert result.expert_id == eid
        assert result.version == 1


class TestSeedExperts:
    def test_seed_has_two_templates(self) -> None:
        assert len(SEED_EXPERTS) == 2

    def test_security_review_template(self) -> None:
        security = next(e for e in SEED_EXPERTS if e.name == "security-review")
        assert security.expert_class == ExpertClass.SECURITY
        assert security.trust_tier == TrustTier.PROBATION
        assert "auth" in security.capability_tags
        assert "secrets" in security.capability_tags
        assert security.definition.get("scope_boundaries") is not None
        assert security.definition.get("expected_outputs") is not None

    def test_qa_validation_template(self) -> None:
        qa = next(e for e in SEED_EXPERTS if e.name == "qa-validation")
        assert qa.expert_class == ExpertClass.QA_VALIDATION
        assert qa.trust_tier == TrustTier.PROBATION
        assert "intent_validation" in qa.capability_tags
        assert "defect_classification" in qa.capability_tags
        assert qa.definition.get("scope_boundaries") is not None
        assert qa.definition.get("expected_outputs") is not None

    def test_no_seed_starts_as_trusted(self) -> None:
        for expert in SEED_EXPERTS:
            assert expert.trust_tier != TrustTier.TRUSTED

    def test_all_seeds_have_tool_policy(self) -> None:
        for expert in SEED_EXPERTS:
            assert expert.tool_policy.get("read_only") is True
            assert "repo_write" in expert.tool_policy.get("denied_suites", [])
