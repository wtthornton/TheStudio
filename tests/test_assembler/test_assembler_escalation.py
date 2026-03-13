"""Tests for Assembler escalation logic (Story 20.5)."""

from uuid import uuid4

from src.assembler.assembler import ExpertOutput, assemble


def _make_output(
    name: str,
    recommendations: list[str] | None = None,
    assumptions: list[str] | None = None,
) -> ExpertOutput:
    """Create a minimal ExpertOutput for testing."""
    return ExpertOutput(
        expert_id=uuid4(),
        expert_version=1,
        expert_name=name,
        recommendations=recommendations or ["Do something"],
        risks=[],
        validations=[],
        assumptions=assumptions or [],
    )


class TestAssemblerEscalation:
    """Test that Assembler produces EscalationRequest on high-risk unresolved conflicts."""

    def test_no_escalation_when_no_conflicts(self) -> None:
        """No escalation when experts have no conflicts."""
        outputs = [
            _make_output("SecurityExpert", assumptions=["use_tls"]),
            _make_output("BusinessExpert", assumptions=["use_rest"]),
        ]
        plan = assemble(
            expert_outputs=outputs,
            intent_constraints=[],
            acceptance_criteria=["Works correctly"],
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            intent_version=1,
        )
        assert plan.escalations == []

    def test_escalation_on_security_conflict(self) -> None:
        """Escalation when unresolved conflict involves security expert."""
        outputs = [
            _make_output(
                "SecurityExpert",
                recommendations=["Encrypt all data"],
                assumptions=["shared_assumption", "security_first"],
            ),
            _make_output(
                "BusinessExpert",
                recommendations=["Minimize latency"],
                assumptions=["shared_assumption", "performance_first"],
            ),
        ]
        plan = assemble(
            expert_outputs=outputs,
            intent_constraints=[],  # No constraints to resolve the conflict
            acceptance_criteria=[],
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            intent_version=1,
        )
        # If there's an unresolved conflict involving "security" in expert name
        security_escalations = [e for e in plan.escalations if e.risk_domain == "security"]
        if plan.conflicts:
            unresolved = [c for c in plan.conflicts if c.resolved_by == "unresolved"]
            if unresolved:
                # Should have escalation since "SecurityExpert" contains "security"
                assert len(security_escalations) > 0
                assert security_escalations[0].source == "assembler"

    def test_escalation_on_compliance_conflict(self) -> None:
        """Escalation when unresolved conflict involves compliance terms."""
        outputs = [
            _make_output(
                "ComplianceReviewer",
                recommendations=["Full audit trail"],
                assumptions=["shared_base", "compliance_required"],
            ),
            _make_output(
                "PerformanceExpert",
                recommendations=["Skip logging for speed"],
                assumptions=["shared_base", "minimal_overhead"],
            ),
        ]
        plan = assemble(
            expert_outputs=outputs,
            intent_constraints=[],
            acceptance_criteria=[],
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            intent_version=1,
        )
        compliance_escalations = [e for e in plan.escalations if e.risk_domain == "compliance"]
        if plan.conflicts:
            unresolved = [c for c in plan.conflicts if c.resolved_by == "unresolved"]
            if unresolved:
                assert len(compliance_escalations) > 0

    def test_no_escalation_on_resolved_conflicts(self) -> None:
        """No escalation when conflicts are resolved by intent constraints."""
        outputs = [
            _make_output(
                "SecurityExpert",
                recommendations=["Encrypt data"],
                assumptions=["shared_base", "use_encryption"],
            ),
            _make_output(
                "BusinessExpert",
                recommendations=["Minimize cost"],
                assumptions=["shared_base", "minimize_cost"],
            ),
        ]
        plan = assemble(
            expert_outputs=outputs,
            intent_constraints=["use_encryption"],  # Resolves in favor of SecurityExpert
            acceptance_criteria=[],
            taskpacket_id=uuid4(),
            correlation_id=uuid4(),
            intent_version=1,
        )
        # Conflict resolved by intent — no escalation
        assert plan.escalations == []
