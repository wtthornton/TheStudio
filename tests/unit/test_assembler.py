"""Unit tests for Assembler (Story 1.5).

Architecture reference: thestudioarc/07-assembler.md
"""

from uuid import uuid4

from src.assembler.assembler import (
    ExpertOutput,
    assemble,
)


def _make_expert_output(
    name: str = "test-expert",
    recommendations: list[str] | None = None,
    risks: list[str] | None = None,
    validations: list[str] | None = None,
    assumptions: list[str] | None = None,
) -> ExpertOutput:
    return ExpertOutput(
        expert_id=uuid4(),
        expert_version=1,
        expert_name=name,
        recommendations=recommendations or ["Implement auth check"],
        risks=risks or ["Missing input validation"],
        validations=validations or ["Verify auth check works"],
        assumptions=assumptions or [],
    )


class TestAssemblerMerge:
    """Assembler merges expert outputs into a single plan."""

    def test_single_expert_produces_steps(self) -> None:
        output = _make_expert_output(
            recommendations=["Add auth middleware", "Add rate limiting"],
        )
        plan = assemble(
            expert_outputs=[output],
            intent_constraints=[],
            acceptance_criteria=[],
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            intent_version=1,
        )
        # 2 recommendations + 1 validation checkpoint
        assert len(plan.steps) == 3
        assert plan.steps[0].description == "Add auth middleware"
        assert plan.steps[1].description == "Add rate limiting"

    def test_multiple_experts_merged(self) -> None:
        sec = _make_expert_output("security", ["Check auth"], validations=["Verify auth"])
        qa = _make_expert_output("qa", ["Add tests"], validations=["Run tests"])
        plan = assemble(
            expert_outputs=[sec, qa],
            intent_constraints=[],
            acceptance_criteria=[],
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            intent_version=1,
        )
        # 2 recommendations + 2 validation checkpoints
        assert len(plan.steps) == 4
        sources = {s.source_expert for s in plan.steps}
        assert "security" in sources
        assert "qa" in sources

    def test_checkpoints_from_validations(self) -> None:
        output = _make_expert_output(validations=["Run security scan", "Verify encryption"])
        plan = assemble(
            expert_outputs=[output],
            intent_constraints=[],
            acceptance_criteria=[],
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            intent_version=1,
        )
        checkpoints = [s for s in plan.steps if s.is_checkpoint]
        assert len(checkpoints) == 2
        assert all(s.description.startswith("Checkpoint:") for s in checkpoints)


class TestAssemblerConflictResolution:
    """Conflicts resolved using intent as tie-breaker."""

    def test_no_conflicts_when_no_shared_assumptions(self) -> None:
        a = _make_expert_output("sec", assumptions=["uses JWT"])
        b = _make_expert_output("qa", assumptions=["uses session"])
        plan = assemble(
            expert_outputs=[a, b],
            intent_constraints=[],
            acceptance_criteria=[],
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            intent_version=1,
        )
        assert len(plan.conflicts) == 0

    def test_conflict_detected_with_divergent_assumptions(self) -> None:
        a = _make_expert_output("sec", assumptions=["uses JWT", "stateless auth"])
        b = _make_expert_output("qa", assumptions=["uses JWT", "session-based auth"])
        plan = assemble(
            expert_outputs=[a, b],
            intent_constraints=[],
            acceptance_criteria=[],
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            intent_version=1,
        )
        assert len(plan.conflicts) == 1
        assert plan.conflicts[0].expert_a == "sec"
        assert plan.conflicts[0].expert_b == "qa"

    def test_conflict_resolved_by_intent(self) -> None:
        a = _make_expert_output("sec", assumptions=["uses JWT", "stateless auth"])
        b = _make_expert_output("qa", assumptions=["uses JWT", "session-based auth"])
        plan = assemble(
            expert_outputs=[a, b],
            intent_constraints=["Must use stateless auth for API endpoints"],
            acceptance_criteria=[],
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            intent_version=1,
        )
        assert len(plan.conflicts) == 1
        assert plan.conflicts[0].resolved_by == "intent"

    def test_unresolved_conflict_triggers_intent_refinement(self) -> None:
        a = _make_expert_output("sec", assumptions=["uses JWT", "stateless auth"])
        b = _make_expert_output("qa", assumptions=["uses JWT", "session-based auth"])
        plan = assemble(
            expert_outputs=[a, b],
            intent_constraints=["Must be secure"],  # Too vague to resolve
            acceptance_criteria=[],
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            intent_version=1,
        )
        assert plan.intent_refinement is not None
        assert len(plan.intent_refinement.questions) > 0
        assert plan.intent_refinement.source == "assembler"


class TestAssemblerProvenance:
    """Provenance minimum record per 07-assembler.md."""

    def test_provenance_has_required_fields(self) -> None:
        tp_id = uuid4()
        corr_id = uuid4()
        output = _make_expert_output("sec-expert")
        plan = assemble(
            expert_outputs=[output],
            intent_constraints=[],
            acceptance_criteria=[],
            taskpacket_id=tp_id,
            correlation_id=corr_id,
            intent_version=2,
        )
        assert plan.provenance is not None
        assert plan.provenance.taskpacket_id == tp_id
        assert plan.provenance.correlation_id == corr_id
        assert plan.provenance.intent_version == 2
        assert len(plan.provenance.experts_consulted) == 1
        assert plan.provenance.experts_consulted[0]["name"] == "sec-expert"
        assert plan.provenance.plan_id == plan.plan_id

    def test_provenance_decision_links(self) -> None:
        output = _make_expert_output(
            "sec", recommendations=["Add auth", "Add encryption"],
        )
        plan = assemble(
            expert_outputs=[output],
            intent_constraints=[],
            acceptance_criteria=[],
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            intent_version=1,
        )
        assert plan.provenance is not None
        # Decision provenance only for non-checkpoint steps
        decisions = plan.provenance.decision_provenance
        assert len(decisions) == 2
        assert decisions[0]["source"] == "sec"


class TestAssemblerQAHandoff:
    """QA handoff maps acceptance criteria to validations."""

    def test_qa_handoff_maps_criteria(self) -> None:
        output = _make_expert_output(
            "sec",
            validations=["Verify authentication works", "Check encryption keys"],
        )
        plan = assemble(
            expert_outputs=[output],
            intent_constraints=[],
            acceptance_criteria=["Authentication must pass all tests"],
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            intent_version=1,
        )
        assert len(plan.qa_handoff) == 1
        mapping = plan.qa_handoff[0]
        assert mapping.criterion == "Authentication must pass all tests"
        assert len(mapping.validation_steps) >= 1

    def test_qa_handoff_generic_when_no_match(self) -> None:
        output = _make_expert_output("sec", validations=["Check X"])
        plan = assemble(
            expert_outputs=[output],
            intent_constraints=[],
            acceptance_criteria=["Completely unrelated criterion"],
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            intent_version=1,
        )
        assert len(plan.qa_handoff) == 1
        # Generic validation when no keyword match
        assert plan.qa_handoff[0].validation_steps[0].startswith("Validate:")


class TestAssemblerRisks:
    """Risk list with mitigations."""

    def test_risks_collected_from_experts(self) -> None:
        a = _make_expert_output("sec", risks=["SQL injection", "XSS"])
        b = _make_expert_output("qa", risks=["Missing tests"])
        plan = assemble(
            expert_outputs=[a, b],
            intent_constraints=[],
            acceptance_criteria=[],
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            intent_version=1,
        )
        assert len(plan.risks) == 3
        risk_descs = {r.description for r in plan.risks}
        assert "SQL injection" in risk_descs
        assert "Missing tests" in risk_descs
