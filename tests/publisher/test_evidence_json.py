"""Tests for format_evidence_json() — Epic 38 Story 38.6.

Tests cover:
- Minimal call (evidence-only); all optional sections default to None
- Full call with all sections populated
- Intent section mapping (goal, version, AC, constraints, non-goals)
- Verification-only → gate_results with checks, verification_passed
- QA-only → gate_results with qa_passed + defect fields
- Verification + QA together
- Provenance from agent_model, expert_coverage, loopback
- files_changed propagated from EvidenceBundle
- Missing / None inputs handled gracefully (no exceptions)
- generated_at is set; schema_version defaults to "1.0"
- correlation_id defaults to nil UUID when omitted
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.agent.evidence import EvidenceBundle
from src.intent.intent_spec import IntentSpecRead
from src.publisher.evidence_comment import (
    ExpertCoverageSummary,
    LoopbackSummary,
    QAResultSummary,
    format_evidence_json,
)
from src.publisher.evidence_payload import EvidencePayload
from src.verification.gate import VerificationResult
from src.verification.runners.base import CheckResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TASK_ID = UUID("00000000-0000-0000-0000-000000000001")
CORR_ID = UUID("00000000-0000-0000-0000-000000000002")
NIL_UUID = UUID("00000000-0000-0000-0000-000000000000")
NOW = datetime(2026, 3, 22, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bundle(**overrides: object) -> EvidenceBundle:
    data: dict = {
        "taskpacket_id": TASK_ID,
        "intent_version": 1,
        "files_changed": [],
        "loopback_attempt": 0,
    }
    data.update(overrides)
    return EvidenceBundle(**data)


def _intent(**overrides: object) -> IntentSpecRead:
    data: dict = {
        "id": uuid4(),
        "taskpacket_id": TASK_ID,
        "version": 2,
        "goal": "Fix the login bug",
        "constraints": ["must not break auth"],
        "acceptance_criteria": ["AC1", "AC2"],
        "non_goals": ["performance improvements"],
        "source": "auto",
        "created_at": NOW,
    }
    data.update(overrides)
    return IntentSpecRead(**data)


def _verification(passed: bool = True, checks: list[CheckResult] | None = None) -> VerificationResult:
    if checks is None:
        checks = [
            CheckResult(name="ruff", passed=True, details=""),
            CheckResult(name="pytest", passed=passed, details="" if passed else "3 failed"),
        ]
    return VerificationResult(passed=passed, checks=checks)


# ---------------------------------------------------------------------------
# Minimal / defaults
# ---------------------------------------------------------------------------


class TestMinimalCall:
    def test_returns_evidence_payload(self) -> None:
        result = format_evidence_json(_bundle())
        assert isinstance(result, EvidencePayload)

    def test_schema_version_default(self) -> None:
        result = format_evidence_json(_bundle())
        assert result.schema_version == "1.0"

    def test_generated_at_set(self) -> None:
        result = format_evidence_json(_bundle())
        assert result.generated_at is not None
        assert isinstance(result.generated_at, datetime)

    def test_optional_sections_none_when_not_provided(self) -> None:
        result = format_evidence_json(_bundle())
        assert result.intent is None
        assert result.gate_results is None
        assert result.cost_breakdown is None
        assert result.provenance is None

    def test_files_changed_empty_by_default(self) -> None:
        result = format_evidence_json(_bundle())
        assert result.files_changed == []

    def test_task_summary_taskpacket_id(self) -> None:
        result = format_evidence_json(_bundle())
        assert result.task_summary.taskpacket_id == TASK_ID

    def test_correlation_id_defaults_to_nil_uuid(self) -> None:
        result = format_evidence_json(_bundle())
        assert result.task_summary.correlation_id == NIL_UUID

    def test_task_summary_default_status(self) -> None:
        result = format_evidence_json(_bundle())
        assert result.task_summary.status == "unknown"

    def test_task_summary_default_repo_and_issue(self) -> None:
        result = format_evidence_json(_bundle())
        assert result.task_summary.repo == ""
        assert result.task_summary.issue_id == 0


# ---------------------------------------------------------------------------
# TaskSummary fields
# ---------------------------------------------------------------------------


class TestTaskSummaryFields:
    def test_correlation_id_passed(self) -> None:
        result = format_evidence_json(_bundle(), correlation_id=CORR_ID)
        assert result.task_summary.correlation_id == CORR_ID

    def test_repo_and_issue_id(self) -> None:
        result = format_evidence_json(_bundle(), repo="org/repo", issue_id=42)
        assert result.task_summary.repo == "org/repo"
        assert result.task_summary.issue_id == 42

    def test_status_propagated(self) -> None:
        result = format_evidence_json(_bundle(), status="published")
        assert result.task_summary.status == "published"

    def test_trust_tier_propagated(self) -> None:
        result = format_evidence_json(_bundle(), trust_tier="suggest")
        assert result.task_summary.trust_tier == "suggest"

    def test_pr_number_and_url(self) -> None:
        result = format_evidence_json(
            _bundle(), pr_number=99, pr_url="https://github.com/org/repo/pull/99"
        )
        assert result.task_summary.pr_number == 99
        assert result.task_summary.pr_url == "https://github.com/org/repo/pull/99"

    def test_loopback_count_from_bundle(self) -> None:
        result = format_evidence_json(_bundle(loopback_attempt=3))
        assert result.task_summary.loopback_count == 3

    def test_created_at_from_bundle(self) -> None:
        bundle = _bundle()
        result = format_evidence_json(bundle)
        assert result.task_summary.created_at == bundle.created_at


# ---------------------------------------------------------------------------
# files_changed
# ---------------------------------------------------------------------------


class TestFilesChanged:
    def test_files_propagated(self) -> None:
        bundle = _bundle(files_changed=["src/auth/middleware.py", "tests/test_auth.py"])
        result = format_evidence_json(bundle)
        assert result.files_changed == ["src/auth/middleware.py", "tests/test_auth.py"]

    def test_files_empty_list(self) -> None:
        result = format_evidence_json(_bundle(files_changed=[]))
        assert result.files_changed == []

    def test_original_list_not_mutated(self) -> None:
        original = ["a.py", "b.py"]
        bundle = _bundle(files_changed=original)
        result = format_evidence_json(bundle)
        result.files_changed.append("c.py")
        assert original == ["a.py", "b.py"]


# ---------------------------------------------------------------------------
# IntentSummary
# ---------------------------------------------------------------------------


class TestIntentSection:
    def test_intent_none_when_not_provided(self) -> None:
        result = format_evidence_json(_bundle())
        assert result.intent is None

    def test_intent_populated(self) -> None:
        result = format_evidence_json(_bundle(), intent=_intent())
        assert result.intent is not None
        assert result.intent.goal == "Fix the login bug"
        assert result.intent.version == 2
        assert result.intent.acceptance_criteria == ["AC1", "AC2"]
        assert result.intent.constraints == ["must not break auth"]
        assert result.intent.non_goals == ["performance improvements"]

    def test_intent_empty_lists(self) -> None:
        intent = _intent(acceptance_criteria=[], constraints=[], non_goals=[])
        result = format_evidence_json(_bundle(), intent=intent)
        assert result.intent is not None
        assert result.intent.acceptance_criteria == []
        assert result.intent.constraints == []
        assert result.intent.non_goals == []


# ---------------------------------------------------------------------------
# GateResults — verification
# ---------------------------------------------------------------------------


class TestGateResultsVerification:
    def test_gate_results_none_without_inputs(self) -> None:
        result = format_evidence_json(_bundle())
        assert result.gate_results is None

    def test_verification_passed(self) -> None:
        result = format_evidence_json(_bundle(), verification=_verification(passed=True))
        assert result.gate_results is not None
        assert result.gate_results.verification_passed is True

    def test_verification_failed(self) -> None:
        result = format_evidence_json(_bundle(), verification=_verification(passed=False))
        assert result.gate_results is not None
        assert result.gate_results.verification_passed is False

    def test_checks_mapped(self) -> None:
        result = format_evidence_json(_bundle(), verification=_verification(passed=True))
        assert result.gate_results is not None
        assert len(result.gate_results.checks) == 2
        names = {c.name for c in result.gate_results.checks}
        assert names == {"ruff", "pytest"}

    def test_check_details_propagated(self) -> None:
        checks = [CheckResult(name="pytest", passed=False, details="3 failed")]
        result = format_evidence_json(
            _bundle(), verification=_verification(passed=False, checks=checks)
        )
        assert result.gate_results is not None
        assert result.gate_results.checks[0].details == "3 failed"

    def test_check_empty_details_becomes_none(self) -> None:
        checks = [CheckResult(name="ruff", passed=True, details="")]
        result = format_evidence_json(
            _bundle(), verification=_verification(passed=True, checks=checks)
        )
        assert result.gate_results is not None
        assert result.gate_results.checks[0].details is None

    def test_qa_passed_none_without_qa_result(self) -> None:
        result = format_evidence_json(_bundle(), verification=_verification())
        assert result.gate_results is not None
        assert result.gate_results.qa_passed is None


# ---------------------------------------------------------------------------
# GateResults — QA result
# ---------------------------------------------------------------------------


class TestGateResultsQA:
    def test_qa_only_creates_gate_results(self) -> None:
        qa = QAResultSummary(passed=True)
        result = format_evidence_json(_bundle(), qa_result=qa)
        assert result.gate_results is not None

    def test_qa_passed_true(self) -> None:
        qa = QAResultSummary(passed=True)
        result = format_evidence_json(_bundle(), qa_result=qa)
        assert result.gate_results is not None
        assert result.gate_results.qa_passed is True

    def test_qa_passed_false(self) -> None:
        qa = QAResultSummary(passed=False, defect_count=2, defect_categories=["logic", "coverage"])
        result = format_evidence_json(_bundle(), qa_result=qa)
        assert result.gate_results is not None
        assert result.gate_results.qa_passed is False
        assert result.gate_results.defect_count == 2
        assert result.gate_results.defect_categories == ["logic", "coverage"]

    def test_verification_and_qa_together(self) -> None:
        qa = QAResultSummary(passed=True)
        result = format_evidence_json(
            _bundle(), verification=_verification(passed=True), qa_result=qa
        )
        assert result.gate_results is not None
        assert result.gate_results.verification_passed is True
        assert result.gate_results.qa_passed is True
        assert len(result.gate_results.checks) == 2


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


class TestProvenance:
    def test_provenance_none_without_inputs(self) -> None:
        result = format_evidence_json(_bundle())
        assert result.provenance is None

    def test_agent_model_creates_provenance(self) -> None:
        result = format_evidence_json(_bundle(), agent_model="claude-3-5-sonnet")
        assert result.provenance is not None
        assert result.provenance.agent_model == "claude-3-5-sonnet"

    def test_expert_coverage_mapped(self) -> None:
        coverage = ExpertCoverageSummary(
            experts_consulted=[
                {"name": "SecurityExpert", "version": "1.2", "role": "security"},
                {"name": "TestingExpert", "role": "testing"},
            ]
        )
        result = format_evidence_json(_bundle(), expert_coverage=coverage)
        assert result.provenance is not None
        assert len(result.provenance.experts_consulted) == 2
        assert result.provenance.experts_consulted[0].name == "SecurityExpert"
        assert result.provenance.experts_consulted[0].version == "1.2"
        assert result.provenance.experts_consulted[0].role == "security"
        assert result.provenance.experts_consulted[1].version is None

    def test_expert_policy_triggers_mapped(self) -> None:
        coverage = ExpertCoverageSummary(
            experts_consulted=[
                {"name": "SecurityExpert", "policy_triggers": ["sql_injection", "auth"]},
            ]
        )
        result = format_evidence_json(_bundle(), expert_coverage=coverage)
        assert result.provenance is not None
        assert result.provenance.experts_consulted[0].policy_triggers == ["sql_injection", "auth"]

    def test_loopback_stages_from_loopback_summary(self) -> None:
        loopback = LoopbackSummary(
            verification_failure_categories=["lint"],
            qa_defect_categories=["test_coverage"],
        )
        result = format_evidence_json(_bundle(), loopback=loopback)
        assert result.provenance is not None
        assert "lint" in result.provenance.loopback_stages
        assert "test_coverage" in result.provenance.loopback_stages

    def test_empty_loopback_creates_provenance(self) -> None:
        loopback = LoopbackSummary()
        result = format_evidence_json(_bundle(), loopback=loopback)
        assert result.provenance is not None
        assert result.provenance.loopback_stages == []

    def test_no_experts_empty_list(self) -> None:
        result = format_evidence_json(_bundle(), agent_model="claude-3-opus")
        assert result.provenance is not None
        assert result.provenance.experts_consulted == []


# ---------------------------------------------------------------------------
# Cost breakdown passthrough
# ---------------------------------------------------------------------------


class TestCostBreakdown:
    def test_cost_breakdown_none_by_default(self) -> None:
        result = format_evidence_json(_bundle())
        assert result.cost_breakdown is None

    def test_cost_breakdown_passed_through(self) -> None:
        from src.publisher.evidence_payload import CostBreakdown, CostEntry

        cb = CostBreakdown(
            total_cost_usd=0.05,
            total_tokens_in=10000,
            total_tokens_out=4000,
            entries=[CostEntry(label="context", tokens_in=5000, tokens_out=0, cost_usd=0.02)],
        )
        result = format_evidence_json(_bundle(), cost_breakdown=cb)
        assert result.cost_breakdown is not None
        assert result.cost_breakdown.total_cost_usd == pytest.approx(0.05)
        assert len(result.cost_breakdown.entries) == 1


# ---------------------------------------------------------------------------
# Full integration
# ---------------------------------------------------------------------------


class TestFullPayload:
    def test_full_round_trip(self) -> None:
        """All sections populated; payload serialises to JSON cleanly."""
        bundle = _bundle(
            files_changed=["src/auth/login.py", "tests/test_login.py"],
            loopback_attempt=1,
        )
        intent = _intent()
        verification = _verification(passed=True)
        qa = QAResultSummary(passed=True, defect_count=0)
        coverage = ExpertCoverageSummary(
            experts_consulted=[{"name": "SecurityExpert", "version": "1.0"}],
            policy_triggers=["auth"],
        )
        loopback = LoopbackSummary(
            verification_loop_count=1,
            verification_failure_categories=["lint"],
        )

        result = format_evidence_json(
            bundle,
            intent=intent,
            verification=verification,
            correlation_id=CORR_ID,
            repo="org/repo",
            issue_id=42,
            status="published",
            trust_tier="suggest",
            pr_number=7,
            pr_url="https://github.com/org/repo/pull/7",
            qa_result=qa,
            expert_coverage=coverage,
            loopback=loopback,
            agent_model="claude-3-opus",
        )

        # Top-level
        assert result.schema_version == "1.0"
        assert result.generated_at is not None

        # TaskSummary
        assert result.task_summary.taskpacket_id == TASK_ID
        assert result.task_summary.correlation_id == CORR_ID
        assert result.task_summary.repo == "org/repo"
        assert result.task_summary.issue_id == 42
        assert result.task_summary.status == "published"
        assert result.task_summary.trust_tier == "suggest"
        assert result.task_summary.loopback_count == 1
        assert result.task_summary.pr_number == 7

        # Intent
        assert result.intent is not None
        assert result.intent.goal == "Fix the login bug"
        assert result.intent.version == 2

        # GateResults
        assert result.gate_results is not None
        assert result.gate_results.verification_passed is True
        assert result.gate_results.qa_passed is True

        # Provenance
        assert result.provenance is not None
        assert result.provenance.agent_model == "claude-3-opus"
        assert len(result.provenance.experts_consulted) == 1
        assert "lint" in result.provenance.loopback_stages

        # files_changed
        assert result.files_changed == ["src/auth/login.py", "tests/test_login.py"]

        # JSON serialisable
        json_str = result.model_dump_json()
        assert "taskpacket_id" in json_str
        assert "schema_version" in json_str
