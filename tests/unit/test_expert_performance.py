"""Tests for Expert Performance API (Story 5.6)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.admin.experts import ExpertPerformanceService
from src.reputation.engine import clear as clear_engine, update_weight
from src.reputation.models import WeightUpdate


@pytest.fixture(autouse=True)
def _clean_stores():
    clear_engine()
    yield
    clear_engine()


def _seed_expert(expert_id=None, repo="repo-1", risk="general", band="medium", count=5):
    """Seed an expert with weight updates."""
    eid = expert_id or uuid4()
    for _ in range(count):
        update_weight(WeightUpdate(
            expert_id=eid,
            expert_version=1,
            context_key=f"{repo}:{risk}:{band}",
            normalized_weight=0.5,
            timestamp=datetime.now(UTC),
        ))
    return eid


class TestExpertPerformanceService:
    """Tests for ExpertPerformanceService."""

    def test_list_experts_empty(self):
        svc = ExpertPerformanceService()
        result = svc.list_experts()
        assert result == []

    def test_list_experts_with_data(self):
        eid1 = _seed_expert()
        eid2 = _seed_expert()

        svc = ExpertPerformanceService()
        result = svc.list_experts()
        assert len(result) == 2
        ids = {e.expert_id for e in result}
        assert str(eid1) in ids
        assert str(eid2) in ids

    def test_list_experts_repo_filter(self):
        eid1 = _seed_expert(repo="repo-1")
        _seed_expert(repo="repo-2")

        svc = ExpertPerformanceService()
        result = svc.list_experts(repo_filter="repo-1")
        assert len(result) == 1
        assert result[0].expert_id == str(eid1)

    def test_list_experts_tier_filter(self):
        eid1 = _seed_expert(count=3)

        svc = ExpertPerformanceService()
        # All experts start as shadow
        result = svc.list_experts(tier_filter="shadow")
        assert len(result) == 1
        assert result[0].expert_id == str(eid1)

        # No probation experts exist
        result = svc.list_experts(tier_filter="probation")
        assert len(result) == 0

    def test_get_expert_found(self):
        eid = _seed_expert(repo="repo-1", count=5)

        svc = ExpertPerformanceService()
        detail = svc.get_expert(str(eid))
        assert detail is not None
        assert detail.expert_id == str(eid)
        assert len(detail.repos) >= 1
        assert detail.repos[0].repo == "repo-1"
        assert detail.sample_count >= 5

    def test_get_expert_not_found(self):
        svc = ExpertPerformanceService()
        detail = svc.get_expert(str(uuid4()))
        assert detail is None

    def test_get_expert_multi_repo(self):
        eid = uuid4()
        _seed_expert(expert_id=eid, repo="repo-1", count=3)
        _seed_expert(expert_id=eid, repo="repo-2", count=4)

        svc = ExpertPerformanceService()
        detail = svc.get_expert(str(eid))
        assert detail is not None
        assert len(detail.repos) == 2
        repos = {r.repo for r in detail.repos}
        assert "repo-1" in repos
        assert "repo-2" in repos

    def test_get_expert_drift_found(self):
        eid = _seed_expert(count=5)

        svc = ExpertPerformanceService()
        drift = svc.get_expert_drift(str(eid))
        assert drift is not None
        assert drift.expert_id == str(eid)
        assert drift.trend in ("improving", "stable", "declining")

    def test_get_expert_drift_not_found(self):
        svc = ExpertPerformanceService()
        drift = svc.get_expert_drift(str(uuid4()))
        assert drift is None

    def test_summary_to_dict(self):
        eid = _seed_expert()
        svc = ExpertPerformanceService()
        result = svc.list_experts()
        d = result[0].to_dict()
        assert "expert_id" in d
        assert "trust_tier" in d
        assert "confidence" in d
        assert "weight" in d
        assert "drift_signal" in d
        assert "context_count" in d

    def test_detail_to_dict(self):
        eid = _seed_expert()
        svc = ExpertPerformanceService()
        detail = svc.get_expert(str(eid))
        d = detail.to_dict()
        assert "expert_id" in d
        assert "repos" in d
        assert "sample_count" in d

    def test_drift_to_dict(self):
        eid = _seed_expert()
        svc = ExpertPerformanceService()
        drift = svc.get_expert_drift(str(eid))
        d = drift.to_dict()
        assert "expert_id" in d
        assert "trend" in d
        assert "change_pct" in d
