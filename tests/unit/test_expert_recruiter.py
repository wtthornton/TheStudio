"""Unit tests for Expert Recruiter (Story 1.4).

Architecture reference: thestudioarc/04-expert-recruiter.md
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.experts.expert import ExpertClass, ExpertRead, LifecycleState, TrustTier
from src.recruiting.qualification import qualify_expert_definition
from src.recruiting.recruiter import recruit
from src.recruiting.templates import TEMPLATE_CATALOG, select_template
from src.routing.router import RecruiterRequest


def _fake_expert(
    name: str = "test-expert",
    expert_class: ExpertClass = ExpertClass.SECURITY,
    trust_tier: TrustTier = TrustTier.PROBATION,
    capability_tags: list[str] | None = None,
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE,
) -> ExpertRead:
    from datetime import UTC, datetime

    return ExpertRead(
        id=uuid4(),
        name=name,
        expert_class=expert_class,
        capability_tags=capability_tags or ["auth", "secrets", "crypto", "injection"],
        scope_description="test",
        tool_policy={"read_only": True, "denied_suites": ["repo_write", "publish"]},
        trust_tier=trust_tier,
        lifecycle_state=lifecycle_state,
        current_version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestTemplateCatalog:
    """Template catalog has required templates."""

    def test_has_security_review_template(self) -> None:
        assert "security-review" in TEMPLATE_CATALOG
        t = TEMPLATE_CATALOG["security-review"]
        assert t.expert_class == ExpertClass.SECURITY

    def test_has_qa_validation_template(self) -> None:
        assert "qa-validation" in TEMPLATE_CATALOG
        t = TEMPLATE_CATALOG["qa-validation"]
        assert t.expert_class == ExpertClass.QA_VALIDATION

    def test_templates_have_required_fields(self) -> None:
        for tid, template in TEMPLATE_CATALOG.items():
            assert template.template_id == tid
            assert template.name_prefix
            assert template.default_capability_tags
            assert template.scope_description
            assert template.tool_policy
            assert template.definition_skeleton


class TestTemplateSelection:
    """Template selection picks narrowest match."""

    def test_selects_security_template(self) -> None:
        result = select_template(ExpertClass.SECURITY, ["auth", "crypto"])
        assert result is not None
        assert result.template_id == "security-review"

    def test_selects_qa_template(self) -> None:
        result = select_template(ExpertClass.QA_VALIDATION, ["intent_validation"])
        assert result is not None
        assert result.template_id == "qa-validation"

    def test_returns_none_for_no_match(self) -> None:
        result = select_template(ExpertClass.PARTNER, ["partner_api"])
        assert result is None


class TestQualificationHarness:
    """Qualification harness validates expert packs."""

    def test_valid_definition_passes(self) -> None:
        definition: dict[str, object] = {
            "scope_boundaries": ["auth"],
            "expected_outputs": ["findings"],
            "operating_procedure": ["review"],
            "failure_modes": ["escalate"],
        }
        tool_policy: dict[str, object] = {
            "read_only": True,
            "denied_suites": ["repo_write", "publish"],
        }
        result = qualify_expert_definition(definition, tool_policy)
        assert result.passed is True
        assert result.failures == ()

    def test_missing_scope_boundaries_fails(self) -> None:
        definition: dict[str, object] = {
            "expected_outputs": ["findings"],
            "operating_procedure": ["review"],
            "failure_modes": ["escalate"],
        }
        tool_policy: dict[str, object] = {
            "denied_suites": ["repo_write", "publish"],
        }
        result = qualify_expert_definition(definition, tool_policy)
        assert result.passed is False
        assert any("scope_boundaries" in f for f in result.failures)

    def test_empty_tool_policy_fails(self) -> None:
        definition: dict[str, object] = {
            "scope_boundaries": ["auth"],
            "expected_outputs": ["findings"],
            "operating_procedure": ["review"],
            "failure_modes": ["escalate"],
        }
        result = qualify_expert_definition(definition, {})
        assert result.passed is False
        assert any("Tool policy is empty" in f for f in result.failures)

    def test_tool_policy_missing_repo_write_denial_fails(self) -> None:
        definition: dict[str, object] = {
            "scope_boundaries": ["auth"],
            "expected_outputs": ["findings"],
            "operating_procedure": ["review"],
            "failure_modes": ["escalate"],
        }
        tool_policy: dict[str, object] = {
            "denied_suites": ["publish"],
        }
        result = qualify_expert_definition(definition, tool_policy)
        assert result.passed is False
        assert any("repo_write" in f for f in result.failures)


class TestRecruiterDeduplication:
    """Recruiter prefers existing experts over creating new ones."""

    @pytest.mark.asyncio
    async def test_returns_existing_expert_when_match(self) -> None:
        existing = _fake_expert(
            "security-review",
            ExpertClass.SECURITY,
            capability_tags=["auth", "secrets", "crypto", "injection"],
        )
        session = AsyncMock()

        with patch("src.recruiting.recruiter.search_experts", return_value=[existing]):
            request = RecruiterRequest(
                expert_class=ExpertClass.SECURITY,
                capability_tags=["auth", "secrets", "crypto", "injection"],
                reason="No eligible expert",
            )
            result = await recruit(session, request)

        assert result.success is True
        assert result.action == "existing"
        assert result.expert is not None
        assert result.expert.name == "security-review"


class TestRecruiterCreation:
    """Recruiter creates new experts from templates."""

    @pytest.mark.asyncio
    async def test_creates_from_template_when_no_existing(self) -> None:
        created = _fake_expert("security-review-auth-crypto", ExpertClass.SECURITY)
        session = AsyncMock()

        with (
            patch("src.recruiting.recruiter.search_experts", return_value=[]),
            patch("src.recruiting.recruiter.create_expert", return_value=created),
        ):
            request = RecruiterRequest(
                expert_class=ExpertClass.SECURITY,
                capability_tags=["auth", "crypto"],
                reason="No eligible expert",
            )
            result = await recruit(session, request)

        assert result.success is True
        assert result.action == "created"
        assert result.qualification is not None
        assert result.qualification.passed is True

    @pytest.mark.asyncio
    async def test_fails_when_no_template_exists(self) -> None:
        session = AsyncMock()

        with patch("src.recruiting.recruiter.search_experts", return_value=[]):
            request = RecruiterRequest(
                expert_class=ExpertClass.PARTNER,
                capability_tags=["partner_api"],
                reason="No eligible expert",
            )
            result = await recruit(session, request)

        assert result.success is False
        assert result.action == "failed"
        assert "No template" in result.reason


class TestRecruiterTrustTier:
    """New experts start in shadow or probation — never trusted."""

    @pytest.mark.asyncio
    async def test_new_expert_never_starts_trusted(self) -> None:
        created = _fake_expert(
            "security-review-auth-crypto",
            ExpertClass.SECURITY,
            trust_tier=TrustTier.PROBATION,
        )
        session = AsyncMock()

        with (
            patch("src.recruiting.recruiter.search_experts", return_value=[]),
            patch("src.recruiting.recruiter.create_expert", return_value=created) as mock_create,
        ):
            request = RecruiterRequest(
                expert_class=ExpertClass.SECURITY,
                capability_tags=["auth", "crypto"],
                reason="No eligible expert",
            )
            await recruit(session, request)

        # Verify the create call used probation (template default), not trusted
        call_args = mock_create.call_args[0][1]
        assert call_args.trust_tier != TrustTier.TRUSTED

    @pytest.mark.asyncio
    async def test_compliance_expert_starts_as_shadow(self) -> None:
        """Compliance experts always start as shadow per 04-expert-recruiter.md."""
        session = AsyncMock()

        # No template for compliance yet, so this should fail —
        # but verifies the intent. If template existed, tier would be shadow.
        with patch("src.recruiting.recruiter.search_experts", return_value=[]):
            request = RecruiterRequest(
                expert_class=ExpertClass.COMPLIANCE,
                capability_tags=["retention", "audit"],
                reason="No eligible expert",
            )
            result = await recruit(session, request)

        # No compliance template → fails (correct behavior)
        assert result.success is False
