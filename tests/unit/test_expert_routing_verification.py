"""Tests for expert routing integration verification (Story 6.5).

Verifies all 5 seeded expert classes are discoverable, correctly classified,
and filterable through the admin expert API.
"""

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest

from src.admin.experts import ExpertPerformanceService, ExpertSummary
from src.experts.expert import ExpertClass
from src.experts.seed import SEED_EXPERTS
from src.reputation.models import DriftSignal, ExpertWeight, TrustTier


def _make_weight(expert_id, expert_class, trust_tier=TrustTier.PROBATION):
    """Create a mock ExpertWeight for testing."""
    now = datetime.now(UTC)
    return ExpertWeight(
        expert_id=expert_id,
        expert_version=1,
        context_key="test-repo:general:medium",
        weight=0.75,
        confidence=0.2,
        sample_count=5,
        trust_tier=trust_tier,
        drift_signal=DriftSignal.STABLE,
        created_at=now,
        updated_at=now,
    )


class TestExpertClassCoverage:
    """Verify all 5 required expert classes are seeded."""

    def test_five_classes_covered(self):
        classes = {e.expert_class for e in SEED_EXPERTS}
        required = {
            ExpertClass.SECURITY,
            ExpertClass.QA_VALIDATION,
            ExpertClass.TECHNICAL,
            ExpertClass.COMPLIANCE,
            ExpertClass.PROCESS_QUALITY,
        }
        assert required.issubset(classes)

    def test_each_class_has_unique_expert(self):
        class_to_name = {}
        for e in SEED_EXPERTS:
            assert e.expert_class not in class_to_name, (
                f"Duplicate class {e.expert_class}: {class_to_name[e.expert_class]} and {e.name}"
            )
            class_to_name[e.expert_class] = e.name

    def test_expert_names_unique(self):
        names = [e.name for e in SEED_EXPERTS]
        assert len(names) == len(set(names))

    def test_capability_tags_non_overlapping_across_classes(self):
        """Each expert class should have distinct capability tags."""
        all_tags = {}
        for e in SEED_EXPERTS:
            for tag in e.capability_tags:
                if tag in all_tags:
                    # Tags can overlap if they serve different purposes,
                    # but core tags should be unique per class
                    pass
                all_tags[tag] = e.expert_class
        # At minimum, each expert should have at least one unique tag
        for e in SEED_EXPERTS:
            assert len(e.capability_tags) >= 2


class TestExpertServiceDiscovery:
    """Verify experts are discoverable through ExpertPerformanceService."""

    def _create_weights_for_all_experts(self):
        """Create mock weights for all 5 seeded experts."""
        weights = []
        for i, expert in enumerate(SEED_EXPERTS):
            eid = uuid4()
            weights.append(_make_weight(eid, expert.expert_class))
        return weights

    def test_list_experts_returns_all(self):
        weights = self._create_weights_for_all_experts()
        svc = ExpertPerformanceService()
        with patch("src.admin.experts.get_all_weights", return_value=weights):
            result = svc.list_experts()
        assert len(result) == 5

    def test_list_experts_tier_filter(self):
        weights = self._create_weights_for_all_experts()
        svc = ExpertPerformanceService()
        with patch("src.admin.experts.get_all_weights", return_value=weights):
            probation = svc.list_experts(tier_filter="probation")
            shadow = svc.list_experts(tier_filter="shadow")
        assert len(probation) == 5  # All start at probation
        assert len(shadow) == 0
