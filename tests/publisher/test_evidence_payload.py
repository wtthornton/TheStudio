"""Unit tests for EvidencePayload Pydantic model (Epic 38 — Story 38.5).

Tests cover:
- All section models: TaskSummary, IntentSummary, GateResults, CostBreakdown, Provenance
- Enum/field validation and defaults
- Optional sections (None is fine)
- from_attributes ORM-style loading via model_validate
- Forward-compat extra dict
- schema_version default
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from src.publisher.evidence_payload import (
    CostBreakdown,
    CostEntry,
    EvidencePayload,
    GateResult,
    GateResults,
    IntentSummary,
    Provenance,
    ProvenanceEntry,
    TaskSummary,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TASK_ID = UUID("00000000-0000-0000-0000-000000000001")
CORR_ID = UUID("00000000-0000-0000-0000-000000000002")
NOW = datetime(2026, 3, 22, 12, 0, 0, tzinfo=timezone.utc)


def _task_summary(**overrides: object) -> TaskSummary:
    data: dict = {
        "taskpacket_id": TASK_ID,
        "correlation_id": CORR_ID,
        "repo": "org/repo",
        "issue_id": 42,
        "status": "published",
    }
    data.update(overrides)
    return TaskSummary(**data)


# ---------------------------------------------------------------------------
# TaskSummary
# ---------------------------------------------------------------------------


class TestTaskSummary:
    def test_required_fields(self) -> None:
        ts = _task_summary()
        assert ts.taskpacket_id == TASK_ID
        assert ts.correlation_id == CORR_ID
        assert ts.repo == "org/repo"
        assert ts.issue_id == 42
        assert ts.status == "published"

    def test_optional_fields_default_none(self) -> None:
        ts = _task_summary()
        assert ts.issue_title is None
        assert ts.trust_tier is None
        assert ts.pr_number is None
        assert ts.pr_url is None
        assert ts.created_at is None
        assert ts.updated_at is None

    def test_loopback_count_defaults_zero(self) -> None:
        assert _task_summary().loopback_count == 0

    def test_optional_fields_set(self) -> None:
        ts = _task_summary(
            issue_title="Fix the bug",
            trust_tier="suggest",
            loopback_count=2,
            pr_number=99,
            pr_url="https://github.com/org/repo/pull/99",
            created_at=NOW,
            updated_at=NOW,
        )
        assert ts.issue_title == "Fix the bug"
        assert ts.trust_tier == "suggest"
        assert ts.loopback_count == 2
        assert ts.pr_number == 99
        assert ts.pr_url == "https://github.com/org/repo/pull/99"

    def test_invalid_issue_id_type(self) -> None:
        with pytest.raises(Exception):
            TaskSummary(
                taskpacket_id=TASK_ID,
                correlation_id=CORR_ID,
                repo="org/repo",
                issue_id="not-an-int",  # type: ignore[arg-type]
                status="published",
            )

    def test_missing_required_fields_raises(self) -> None:
        with pytest.raises(Exception):
            TaskSummary(taskpacket_id=TASK_ID)  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# IntentSummary
# ---------------------------------------------------------------------------


class TestIntentSummary:
    def test_required_fields(self) -> None:
        intent = IntentSummary(goal="Fix the login bug", version=3)
        assert intent.goal == "Fix the login bug"
        assert intent.version == 3

    def test_list_fields_default_empty(self) -> None:
        intent = IntentSummary(goal="Goal", version=1)
        assert intent.acceptance_criteria == []
        assert intent.constraints == []
        assert intent.non_goals == []

    def test_list_fields_populated(self) -> None:
        intent = IntentSummary(
            goal="Fix bug",
            version=2,
            acceptance_criteria=["AC1", "AC2"],
            constraints=["must not break auth"],
            non_goals=["performance improvements"],
        )
        assert len(intent.acceptance_criteria) == 2
        assert len(intent.constraints) == 1
        assert len(intent.non_goals) == 1


# ---------------------------------------------------------------------------
# GateResult / GateResults
# ---------------------------------------------------------------------------


class TestGateResult:
    def test_passed(self) -> None:
        g = GateResult(name="lint", passed=True)
        assert g.passed is True
        assert g.details is None

    def test_failed_with_details(self) -> None:
        g = GateResult(name="pytest", passed=False, details="3 tests failed")
        assert g.passed is False
        assert g.details == "3 tests failed"


class TestGateResults:
    def test_defaults(self) -> None:
        gr = GateResults()
        assert gr.verification_passed is False
        assert gr.qa_passed is None
        assert gr.checks == []
        assert gr.defect_count == 0
        assert gr.defect_categories == []

    def test_with_checks(self) -> None:
        gr = GateResults(
            verification_passed=True,
            qa_passed=True,
            checks=[
                GateResult(name="lint", passed=True),
                GateResult(name="pytest", passed=True),
            ],
        )
        assert len(gr.checks) == 2
        assert all(c.passed for c in gr.checks)

    def test_failed_with_defects(self) -> None:
        gr = GateResults(
            verification_passed=False,
            defect_count=2,
            defect_categories=["logic", "test_coverage"],
        )
        assert gr.defect_count == 2
        assert "logic" in gr.defect_categories


# ---------------------------------------------------------------------------
# CostBreakdown / CostEntry
# ---------------------------------------------------------------------------


class TestCostBreakdown:
    def test_defaults(self) -> None:
        cb = CostBreakdown()
        assert cb.total_cost_usd == 0.0
        assert cb.total_tokens_in == 0
        assert cb.total_tokens_out == 0
        assert cb.entries == []

    def test_with_entries(self) -> None:
        cb = CostBreakdown(
            total_cost_usd=0.025,
            total_tokens_in=5000,
            total_tokens_out=2000,
            entries=[
                CostEntry(label="context", tokens_in=2000, tokens_out=0, cost_usd=0.01),
                CostEntry(label="agent", tokens_in=3000, tokens_out=2000, cost_usd=0.015),
            ],
        )
        assert cb.total_cost_usd == pytest.approx(0.025)
        assert len(cb.entries) == 2
        assert cb.entries[0].label == "context"


# ---------------------------------------------------------------------------
# Provenance / ProvenanceEntry
# ---------------------------------------------------------------------------


class TestProvenance:
    def test_defaults(self) -> None:
        p = Provenance()
        assert p.experts_consulted == []
        assert p.agent_model is None
        assert p.loopback_stages == []

    def test_with_experts(self) -> None:
        p = Provenance(
            agent_model="claude-3-5-sonnet",
            experts_consulted=[
                ProvenanceEntry(name="SecurityExpert", version="1.2", role="security"),
                ProvenanceEntry(name="TestingExpert", role="testing", policy_triggers=["test_coverage"]),
            ],
            loopback_stages=["verification", "qa"],
        )
        assert p.agent_model == "claude-3-5-sonnet"
        assert len(p.experts_consulted) == 2
        assert p.experts_consulted[0].name == "SecurityExpert"
        assert "test_coverage" in p.experts_consulted[1].policy_triggers
        assert len(p.loopback_stages) == 2


# ---------------------------------------------------------------------------
# EvidencePayload — top-level
# ---------------------------------------------------------------------------


class TestEvidencePayload:
    def _minimal(self) -> EvidencePayload:
        return EvidencePayload(task_summary=_task_summary())

    def test_schema_version_default(self) -> None:
        payload = self._minimal()
        assert payload.schema_version == "1.0"

    def test_optional_sections_default_none(self) -> None:
        payload = self._minimal()
        assert payload.intent is None
        assert payload.gate_results is None
        assert payload.cost_breakdown is None
        assert payload.provenance is None
        assert payload.generated_at is None

    def test_files_changed_default_empty(self) -> None:
        assert self._minimal().files_changed == []

    def test_extra_dict_default_empty(self) -> None:
        assert self._minimal().extra == {}

    def test_full_payload(self) -> None:
        payload = EvidencePayload(
            generated_at=NOW,
            task_summary=_task_summary(issue_title="Fix bug", loopback_count=1),
            intent=IntentSummary(goal="Fix the login bug", version=2, acceptance_criteria=["AC1"]),
            gate_results=GateResults(verification_passed=True, qa_passed=True),
            cost_breakdown=CostBreakdown(total_cost_usd=0.01),
            provenance=Provenance(agent_model="claude-3-opus"),
            files_changed=["src/auth/middleware.py"],
            extra={"sprint": "sprint-1"},
        )
        assert payload.task_summary.issue_title == "Fix bug"
        assert payload.intent is not None
        assert payload.intent.goal == "Fix the login bug"
        assert payload.gate_results is not None
        assert payload.gate_results.verification_passed is True
        assert payload.cost_breakdown is not None
        assert payload.cost_breakdown.total_cost_usd == pytest.approx(0.01)
        assert payload.provenance is not None
        assert payload.provenance.agent_model == "claude-3-opus"
        assert payload.files_changed == ["src/auth/middleware.py"]
        assert payload.extra["sprint"] == "sprint-1"
        assert payload.generated_at == NOW

    def test_serialization_round_trip(self) -> None:
        """EvidencePayload should serialize to dict and reconstruct cleanly."""
        original = EvidencePayload(
            generated_at=NOW,
            task_summary=_task_summary(),
            intent=IntentSummary(goal="Goal", version=1),
            files_changed=["a.py", "b.py"],
        )
        data = original.model_dump()
        restored = EvidencePayload.model_validate(data)
        assert restored.task_summary.taskpacket_id == TASK_ID
        assert restored.files_changed == ["a.py", "b.py"]
        assert restored.intent is not None
        assert restored.intent.goal == "Goal"

    def test_json_serialization(self) -> None:
        """model_dump_json should produce valid JSON string."""
        payload = self._minimal()
        json_str = payload.model_dump_json()
        assert isinstance(json_str, str)
        assert "taskpacket_id" in json_str
        assert "schema_version" in json_str

    def test_task_summary_required(self) -> None:
        """task_summary is required — omitting it raises ValidationError."""
        with pytest.raises(Exception):
            EvidencePayload()  # type: ignore[call-arg]

    def test_uuid_generation(self) -> None:
        """Different payloads should work with distinct UUIDs."""
        id1 = uuid4()
        id2 = uuid4()
        p1 = EvidencePayload(
            task_summary=TaskSummary(
                taskpacket_id=id1, correlation_id=CORR_ID,
                repo="org/repo", issue_id=1, status="received"
            )
        )
        p2 = EvidencePayload(
            task_summary=TaskSummary(
                taskpacket_id=id2, correlation_id=CORR_ID,
                repo="org/repo", issue_id=2, status="received"
            )
        )
        assert p1.task_summary.taskpacket_id != p2.task_summary.taskpacket_id
