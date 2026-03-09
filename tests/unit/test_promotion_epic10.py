"""Unit tests for Epic 10 additions to src/compliance/promotion.py.

Tests RemediationItem, TierTransition.to_dict, and blocked-transition
remediation storage. Core promotion logic is tested in test_promotion.py.
"""

from uuid import uuid4

import pytest

from src.compliance.promotion import (
    RemediationItem,
    TierTransition,
    clear,
    get_latest_transition,
    get_transitions,
    store_transition,
)
from src.repo.repo_profile import RepoTier


@pytest.fixture(autouse=True)
def _reset_state():
    clear()
    yield
    clear()


class TestRemediationItem:
    def test_defaults(self):
        item = RemediationItem(
            check_name="branch_protection",
            description="Enable branch protection",
        )
        assert item.severity == "required"
        assert item.resolved is False

    def test_to_dict(self):
        item = RemediationItem(
            check_name="ci_passing",
            description="CI must pass",
            severity="recommended",
            resolved=True,
        )
        d = item.to_dict()
        assert d["check_name"] == "ci_passing"
        assert d["description"] == "CI must pass"
        assert d["severity"] == "recommended"
        assert d["resolved"] is True


class TestTierTransition:
    def test_defaults(self):
        t = TierTransition()
        assert t.from_tier == RepoTier.OBSERVE
        assert t.to_tier == RepoTier.OBSERVE
        assert t.triggered_by == ""
        assert t.remediation_items == []

    def test_to_dict_basic(self):
        repo_id = uuid4()
        t = TierTransition(
            repo_id=repo_id,
            from_tier=RepoTier.OBSERVE,
            to_tier=RepoTier.SUGGEST,
            triggered_by="admin",
            compliance_score=85.0,
            reason="Promoted by admin",
        )
        d = t.to_dict()
        assert d["repo_id"] == str(repo_id)
        assert d["from_tier"] == "observe"
        assert d["to_tier"] == "suggest"
        assert d["triggered_by"] == "admin"
        assert d["compliance_score"] == 85.0
        assert d["reason"] == "Promoted by admin"
        assert d["remediation_items"] == []
        assert "transitioned_at" in d
        assert "id" in d

    def test_to_dict_with_remediation(self):
        items = [
            RemediationItem(check_name="ci", description="Fix CI"),
            RemediationItem(check_name="bp", description="Enable branch protection"),
        ]
        t = TierTransition(
            from_tier=RepoTier.SUGGEST,
            to_tier=RepoTier.EXECUTE,
            remediation_items=items,
        )
        d = t.to_dict()
        assert len(d["remediation_items"]) == 2
        assert d["remediation_items"][0]["check_name"] == "ci"
        assert d["remediation_items"][1]["check_name"] == "bp"

    def test_to_dict_compliance_score_none(self):
        t = TierTransition()
        d = t.to_dict()
        assert d["compliance_score"] is None


class TestTransitionStorage:
    def test_store_and_get(self):
        repo_id = uuid4()
        t = TierTransition(
            repo_id=repo_id,
            from_tier=RepoTier.OBSERVE,
            to_tier=RepoTier.SUGGEST,
            triggered_by="admin",
        )
        store_transition(t)
        transitions = get_transitions(repo_id)
        assert len(transitions) == 1
        assert transitions[0] is t

    def test_get_filters_by_repo(self):
        repo_a = uuid4()
        repo_b = uuid4()
        store_transition(TierTransition(repo_id=repo_a, triggered_by="a"))
        store_transition(TierTransition(repo_id=repo_b, triggered_by="b"))
        store_transition(TierTransition(repo_id=repo_a, triggered_by="a2"))
        assert len(get_transitions(repo_a)) == 2
        assert len(get_transitions(repo_b)) == 1

    def test_get_latest_transition(self):
        repo_id = uuid4()
        t1 = TierTransition(repo_id=repo_id, triggered_by="first")
        t2 = TierTransition(repo_id=repo_id, triggered_by="second")
        store_transition(t1)
        store_transition(t2)
        latest = get_latest_transition(repo_id)
        assert latest is t2

    def test_get_latest_none(self):
        assert get_latest_transition(uuid4()) is None

    def test_clear(self):
        repo_id = uuid4()
        store_transition(TierTransition(repo_id=repo_id))
        clear()
        assert get_transitions(repo_id) == []

    def test_blocked_transition_stores_remediation(self):
        """Epic 10: blocked promotion stores remediation items on the transition."""
        repo_id = uuid4()
        items = [
            RemediationItem(check_name="branch_protection", description="Enable it"),
            RemediationItem(check_name="ci_required", description="Require CI"),
        ]
        blocked = TierTransition(
            repo_id=repo_id,
            from_tier=RepoTier.SUGGEST,
            to_tier=RepoTier.EXECUTE,
            triggered_by="eligibility_check",
            reason="Blocked: branch_protection, ci_required",
            remediation_items=items,
        )
        store_transition(blocked)

        transitions = get_transitions(repo_id)
        assert len(transitions) == 1
        assert len(transitions[0].remediation_items) == 2
        assert transitions[0].remediation_items[0].check_name == "branch_protection"
        d = transitions[0].to_dict()
        assert len(d["remediation_items"]) == 2
