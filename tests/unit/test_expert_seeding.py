"""Tests for expert seeding with 5 expert classes (Story 6.4)."""

from unittest.mock import AsyncMock, patch

import pytest

from src.experts.expert import ExpertClass
from src.experts.seed import SEED_EXPERTS, seed_experts


class TestSeedExpertDefinitions:
    """Tests for the SEED_EXPERTS list."""

    def test_five_experts_defined(self):
        assert len(SEED_EXPERTS) == 5

    def test_five_distinct_classes(self):
        classes = {e.expert_class for e in SEED_EXPERTS}
        assert len(classes) == 5
        assert ExpertClass.SECURITY in classes
        assert ExpertClass.QA_VALIDATION in classes
        assert ExpertClass.TECHNICAL in classes
        assert ExpertClass.COMPLIANCE in classes
        assert ExpertClass.PROCESS_QUALITY in classes

    def test_all_have_names(self):
        names = [e.name for e in SEED_EXPERTS]
        assert "security-review" in names
        assert "qa-validation" in names
        assert "technical-review" in names
        assert "compliance-check" in names
        assert "process-quality" in names

    def test_all_have_capability_tags(self):
        for expert in SEED_EXPERTS:
            assert len(expert.capability_tags) > 0, f"{expert.name} has no capability_tags"

    def test_all_have_scope_description(self):
        for expert in SEED_EXPERTS:
            assert len(expert.scope_description) > 0, f"{expert.name} has no scope_description"

    def test_all_have_tool_policy(self):
        for expert in SEED_EXPERTS:
            assert "allowed_suites" in expert.tool_policy
            assert "denied_suites" in expert.tool_policy

    def test_all_have_definition_sections(self):
        required_keys = [
            "scope_boundaries", "expected_outputs", "operating_procedure",
            "edge_cases", "failure_modes",
        ]
        for expert in SEED_EXPERTS:
            for key in required_keys:
                assert key in expert.definition, (
                    f"{expert.name} missing definition key: {key}"
                )
                assert len(expert.definition[key]) > 0, (
                    f"{expert.name} has empty {key}"
                )

    def test_all_start_at_probation(self):
        from src.experts.expert import TrustTier
        for expert in SEED_EXPERTS:
            assert expert.trust_tier == TrustTier.PROBATION


@pytest.mark.asyncio
class TestSeedExperts:
    """Tests for the seed_experts function."""

    async def test_creates_all_five(self):
        mock_session = AsyncMock()
        with (
            patch("src.experts.seed.get_expert_by_name", new_callable=AsyncMock, return_value=None),
            patch("src.experts.seed.create_expert", new_callable=AsyncMock) as mock_create,
        ):
            created = await seed_experts(mock_session)
        assert len(created) == 5
        assert mock_create.call_count == 5

    async def test_skips_existing(self):
        mock_session = AsyncMock()
        call_count = 0

        async def mock_get_by_name(session, name):
            if name in ("security-review", "qa-validation"):
                return "existing"
            return None

        with (
            patch("src.experts.seed.get_expert_by_name", side_effect=mock_get_by_name),
            patch("src.experts.seed.create_expert", new_callable=AsyncMock) as mock_create,
        ):
            created = await seed_experts(mock_session)
        assert len(created) == 3
        assert "security-review" not in created
        assert "qa-validation" not in created
        assert mock_create.call_count == 3
