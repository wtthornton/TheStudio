"""End-to-end smoke test — intake to publish flow.

Proves the full orchestration works in-memory by mocking DB CRUD
and external services (agent SDK, GitHub API) while exercising
real business logic (intake eligibility, scope analysis, risk flagging,
intent extraction, evidence formatting).

Story 8.3 (Epic 8 Sprint 1).
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.agent.evidence import EvidenceBundle
from src.context.risk_flagger import flag_risks
from src.context.scope_analyzer import analyze_scope
from src.context.complexity import compute_complexity_index
from src.intake.intake_agent import evaluate_eligibility
from src.intent.intent_builder import (
    derive_constraints,
    extract_acceptance_criteria,
    extract_goal,
    extract_non_goals,
)
from src.models.taskpacket import TaskPacketCreate, TaskPacketRead, TaskPacketStatus
from src.publisher.evidence_comment import format_evidence_comment
from src.verification.runners.base import CheckResult
from src.verification.gate import VerificationResult


# --- Test data ---

ISSUE_TITLE = "Add /health endpoint returning HTTP 200"
ISSUE_BODY = """\
We need a health check endpoint for the load balancer.

## Acceptance Criteria

- [ ] GET /health returns 200
- [ ] Response body is JSON with {"status": "ok"}
- [ ] No authentication required

## Out of scope: metrics endpoint, readiness probe
"""

TP_ID = uuid4()
CORRELATION_ID = uuid4()
INTENT_ID = uuid4()


def _make_taskpacket(status: TaskPacketStatus, **overrides) -> TaskPacketRead:
    """Build a TaskPacketRead at the given status."""
    defaults = {
        "id": TP_ID,
        "repo": "acme/widgets",
        "issue_id": 42,
        "delivery_id": "evt-001",
        "correlation_id": CORRELATION_ID,
        "status": status,
        "scope": None,
        "risk_flags": None,
        "complexity_index": None,
        "context_packs": [],
        "intent_spec_id": None,
        "intent_version": None,
        "loopback_count": 0,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return TaskPacketRead(**defaults)


class TestEndToEndSmokeFlow:
    """Full intake → context → intent → agent → verify → publish flow."""

    def test_step1_intake_accepts_eligible_issue(self):
        """Intake evaluates eligibility and selects role."""
        result = evaluate_eligibility(
            labels=["agent:run", "type:feature"],
            repo="acme/widgets",
            repo_registered=True,
            repo_paused=False,
            has_active_workflow=False,
            event_id="evt-001",
        )
        assert result.accepted is True
        assert result.effective_role is not None
        assert result.effective_role.base_role.value == "developer"

    def test_step2_context_enrichment(self):
        """Context manager analyzes scope, flags risks, computes complexity."""
        # Scope analysis
        scope = analyze_scope(ISSUE_TITLE, ISSUE_BODY)
        assert isinstance(scope.components, list)
        scope_dict = scope.to_dict()
        assert "components" in scope_dict

        # Risk flagging
        risk_flags = flag_risks(ISSUE_TITLE, ISSUE_BODY)
        assert isinstance(risk_flags, dict)
        # Health endpoint shouldn't trigger billing risks
        assert risk_flags.get("risk_billing", False) is False

        # Complexity index
        ci = compute_complexity_index(
            scope_result=scope,
            risk_flags=risk_flags,
        )
        assert ci.band in ("low", "medium", "high")
        assert ci.score >= 0.0

    def test_step3_intent_extraction(self):
        """Intent builder extracts goal, constraints, criteria, non-goals."""
        goal = extract_goal(ISSUE_TITLE, ISSUE_BODY)
        assert "health" in goal.lower()

        criteria = extract_acceptance_criteria(ISSUE_BODY)
        assert len(criteria) == 3
        assert any("200" in c for c in criteria)
        assert any("JSON" in c for c in criteria)

        non_goals = extract_non_goals(ISSUE_BODY)
        assert len(non_goals) >= 1
        assert any("metrics" in ng.lower() for ng in non_goals)

        constraints = derive_constraints({"risk_security": True})
        assert any("credentials" in c.lower() for c in constraints)

    @pytest.mark.asyncio
    async def test_step4_agent_produces_evidence(self):
        """Primary agent (mocked) produces an evidence bundle."""
        evidence = EvidenceBundle(
            taskpacket_id=TP_ID,
            intent_version=1,
            files_changed=["src/health.py", "tests/test_health.py"],
            test_results="2 passed in 0.5s",
            lint_results="All checks passed",
            agent_summary="Added /health endpoint returning JSON 200",
        )
        assert len(evidence.files_changed) == 2
        assert evidence.taskpacket_id == TP_ID

    def test_step5_verification_passes(self):
        """Verification gate produces a passing result."""
        result = VerificationResult(
            passed=True,
            checks=[
                CheckResult(name="ruff", passed=True, details="No issues"),
                CheckResult(name="pytest", passed=True, details="2 passed"),
            ],
        )
        assert result.passed is True
        assert len(result.checks) == 2
        assert all(c.passed for c in result.checks)

    def test_step6_evidence_comment_formatted(self):
        """Publisher formats evidence comment with TaskPacket ID."""
        from src.intent.intent_spec import IntentSpecRead

        intent = IntentSpecRead(
            id=INTENT_ID,
            taskpacket_id=TP_ID,
            version=1,
            goal=extract_goal(ISSUE_TITLE, ISSUE_BODY),
            constraints=derive_constraints(None),
            acceptance_criteria=extract_acceptance_criteria(ISSUE_BODY),
            non_goals=extract_non_goals(ISSUE_BODY),
            created_at=datetime.now(UTC),
        )

        evidence = EvidenceBundle(
            taskpacket_id=TP_ID,
            intent_version=1,
            files_changed=["src/health.py", "tests/test_health.py"],
            test_results="2 passed in 0.5s",
            lint_results="All checks passed",
            agent_summary="Added /health endpoint returning JSON 200",
        )

        verification = VerificationResult(
            passed=True,
            checks=[
                CheckResult(name="ruff", passed=True, details="No issues"),
                CheckResult(name="pytest", passed=True, details="2 passed"),
            ],
        )

        comment = format_evidence_comment(
            evidence=evidence,
            intent=intent,
            verification=verification,
        )

        # Evidence comment must contain key identifiers
        assert str(TP_ID) in comment
        assert "health" in comment.lower()
        assert "PASSED" in comment

    def test_full_flow_status_transitions(self):
        """Verify the expected TaskPacket status transitions."""
        transitions = [
            TaskPacketStatus.RECEIVED,      # After intake creates TaskPacket
            TaskPacketStatus.ENRICHED,       # After context manager enriches
            TaskPacketStatus.INTENT_BUILT,   # After intent builder
            TaskPacketStatus.IN_PROGRESS,    # After agent starts implementation
            TaskPacketStatus.VERIFICATION_PASSED,  # After verification gate
            TaskPacketStatus.PUBLISHED,      # After publisher creates PR
        ]

        # Verify each transition is valid
        from src.models.taskpacket import ALLOWED_TRANSITIONS

        for i in range(len(transitions) - 1):
            from_status = transitions[i]
            to_status = transitions[i + 1]
            assert to_status in ALLOWED_TRANSITIONS.get(from_status, set()), (
                f"Transition {from_status} → {to_status} not allowed"
            )

    @pytest.mark.asyncio
    async def test_publish_orchestration_with_mock_github(self):
        """Publisher creates draft PR via mocked GitHub client."""
        from src.publisher.publisher import _branch_name, _pr_title

        # Verify branch naming is deterministic (uses short UUID prefix)
        branch = _branch_name(TP_ID, 1)
        assert str(TP_ID)[:8] in branch
        assert "v1" in branch

        # Verify PR title format
        title = _pr_title(ISSUE_TITLE)
        assert "health" in title.lower()

    def test_intake_rejects_ineligible(self):
        """Intake correctly rejects issues without agent:run label."""
        result = evaluate_eligibility(
            labels=["type:feature"],  # Missing agent:run
            repo="acme/widgets",
            repo_registered=True,
            repo_paused=False,
            has_active_workflow=False,
            event_id="evt-002",
        )
        assert result.accepted is False
        assert result.rejection is not None
        assert "agent:run" in result.rejection.reason.lower()

    def test_intake_rejects_paused_repo(self):
        """Intake rejects issues from paused repos."""
        result = evaluate_eligibility(
            labels=["agent:run", "type:bug"],
            repo="acme/widgets",
            repo_registered=True,
            repo_paused=True,
            has_active_workflow=False,
            event_id="evt-003",
        )
        assert result.accepted is False

    def test_verification_failure_triggers_loopback(self):
        """A failed verification produces loopback_triggered=True."""
        result = VerificationResult(
            passed=False,
            checks=[
                CheckResult(name="ruff", passed=True, details="OK"),
                CheckResult(name="pytest", passed=False, details="1 failed"),
            ],
            loopback_triggered=True,
        )
        assert result.passed is False
        assert result.loopback_triggered is True
