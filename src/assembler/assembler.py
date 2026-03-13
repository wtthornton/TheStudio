"""Assembler Agent — merges expert outputs into a single executable plan.

Architecture reference: thestudioarc/07-assembler.md

The Assembler:
1. Normalizes and merges expert outputs
2. Resolves conflicts using intent as tie-breaker
3. Creates an implementation plan with checkpoints
4. Maps plan validation steps to acceptance criteria (QA handoff)
5. Generates provenance minimum record
6. Triggers intent refinement when needed
"""

import logging
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from src.models.escalation import EscalationRequest

logger = logging.getLogger(__name__)


# Signals emitted by the Assembler (per 07-assembler.md)
SIGNAL_PLAN_CREATED = "plan_created"
SIGNAL_CONFLICT_DETECTED = "conflict_detected"
SIGNAL_INTENT_REFINEMENT_REQUESTED = "intent_refinement_requested"
SIGNAL_QA_HANDOFF_CREATED = "qa_handoff_created"


@dataclass(frozen=True)
class ExpertOutput:
    """Structured output from a single expert consultation."""

    expert_id: UUID
    expert_version: int
    expert_name: str
    recommendations: list[str]
    risks: list[str]
    validations: list[str]
    assumptions: list[str]


@dataclass(frozen=True)
class PlanStep:
    """A single step in the implementation plan."""

    step_id: int
    description: str
    source_expert: str  # Expert name that contributed this step
    is_checkpoint: bool = False


@dataclass(frozen=True)
class Conflict:
    """A conflict between expert recommendations."""

    expert_a: str
    expert_b: str
    description: str
    resolution: str
    resolved_by: str  # "intent", "risk_priority", "unresolved"


@dataclass(frozen=True)
class RiskItem:
    """A risk identified by experts with mitigation."""

    description: str
    source_expert: str
    mitigation: str
    severity: str  # "high", "medium", "low"


@dataclass(frozen=True)
class QAHandoffMapping:
    """Maps an acceptance criterion to its validation steps."""

    criterion: str
    validation_steps: list[str]
    source_experts: list[str]


@dataclass(frozen=True)
class ProvenanceRecord:
    """Minimum provenance record per 07-assembler.md."""

    taskpacket_id: UUID
    correlation_id: UUID
    intent_version: int
    experts_consulted: list[dict[str, object]]  # [{id, version, name}]
    plan_id: UUID
    decision_provenance: list[dict[str, str]]  # [{decision, source, rationale}]


@dataclass(frozen=True)
class IntentRefinementRequest:
    """Request to refine intent when ambiguity blocks decisions."""

    questions: list[str]
    triggering_conflict: str
    source: str  # "assembler"


@dataclass
class AssemblyPlan:
    """Complete output of the Assembler."""

    plan_id: UUID = field(default_factory=uuid4)
    steps: list[PlanStep] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    risks: list[RiskItem] = field(default_factory=list)
    qa_handoff: list[QAHandoffMapping] = field(default_factory=list)
    provenance: ProvenanceRecord | None = None
    intent_refinement: IntentRefinementRequest | None = None
    escalations: list[EscalationRequest] = field(default_factory=list)


def assemble(
    expert_outputs: list[ExpertOutput],
    intent_constraints: list[str],
    acceptance_criteria: list[str],
    taskpacket_id: UUID,
    correlation_id: UUID,
    intent_version: int,
) -> AssemblyPlan:
    """Merge expert outputs into a single plan with provenance.

    Args:
        expert_outputs: Structured outputs from expert consultations.
        intent_constraints: Constraints from Intent Specification.
        acceptance_criteria: Acceptance criteria from Intent Specification.
        taskpacket_id: TaskPacket being assembled for.
        correlation_id: Correlation ID for traceability.
        intent_version: Current intent version.

    Returns:
        AssemblyPlan with steps, conflicts, risks, QA handoff, and provenance.
    """
    plan = AssemblyPlan()

    # Step 1: Normalize and merge recommendations into plan steps
    step_counter = 0
    for output in expert_outputs:
        for rec in output.recommendations:
            step_counter += 1
            plan.steps.append(
                PlanStep(
                    step_id=step_counter,
                    description=rec,
                    source_expert=output.expert_name,
                )
            )

    # Step 2: Add checkpoints from validations
    for output in expert_outputs:
        for validation in output.validations:
            step_counter += 1
            plan.steps.append(
                PlanStep(
                    step_id=step_counter,
                    description=f"Checkpoint: {validation}",
                    source_expert=output.expert_name,
                    is_checkpoint=True,
                )
            )

    # Step 3: Detect and resolve conflicts
    plan.conflicts = _detect_conflicts(expert_outputs, intent_constraints)

    # Step 3b: Check for high-risk unresolved conflicts requiring escalation
    high_risk_terms = {"security", "compliance", "billing", "partner", "migration", "destructive"}
    unresolved_conflicts = [c for c in plan.conflicts if c.resolved_by == "unresolved"]
    for conflict in unresolved_conflicts:
        # Check if conflict involves high-risk domains by inspecting expert names and description
        conflict_text = (f"{conflict.expert_a} {conflict.expert_b} {conflict.description}").lower()
        detected_domain: str | None = None
        for term in high_risk_terms:
            if term in conflict_text:
                detected_domain = term
                break
        if detected_domain is not None:
            plan.escalations.append(
                EscalationRequest(
                    source="assembler",
                    reason=conflict.description,
                    risk_domain=detected_domain,
                    taskpacket_id=taskpacket_id,
                    correlation_id=correlation_id,
                    severity="high",
                )
            )

    # Step 4: Check for unresolved conflicts requiring intent refinement
    unresolved = [c for c in plan.conflicts if c.resolved_by == "unresolved"]
    if unresolved:
        questions = [
            f"Conflict between {c.expert_a} and {c.expert_b}: {c.description}" for c in unresolved
        ]
        plan.intent_refinement = IntentRefinementRequest(
            questions=questions,
            triggering_conflict=unresolved[0].description,
            source="assembler",
        )
        logger.info(
            "Intent refinement requested: %d unresolved conflicts",
            len(unresolved),
        )

    # Step 5: Collect risks with mitigations
    for output in expert_outputs:
        for risk in output.risks:
            plan.risks.append(
                RiskItem(
                    description=risk,
                    source_expert=output.expert_name,
                    mitigation="See expert recommendations",
                    severity="medium",
                )
            )

    # Step 6: Build QA handoff mapping (acceptance criteria → validations)
    plan.qa_handoff = _build_qa_handoff(
        acceptance_criteria,
        expert_outputs,
    )

    # Step 7: Build provenance minimum record
    plan.provenance = ProvenanceRecord(
        taskpacket_id=taskpacket_id,
        correlation_id=correlation_id,
        intent_version=intent_version,
        experts_consulted=[
            {
                "id": str(o.expert_id),
                "version": o.expert_version,
                "name": o.expert_name,
            }
            for o in expert_outputs
        ],
        plan_id=plan.plan_id,
        decision_provenance=[
            {
                "decision": step.description,
                "source": step.source_expert,
                "rationale": "Expert recommendation",
            }
            for step in plan.steps
            if not step.is_checkpoint
        ],
    )

    logger.info(
        "Assembled plan %s: %d steps, %d conflicts, %d risks, %d QA mappings",
        plan.plan_id,
        len(plan.steps),
        len(plan.conflicts),
        len(plan.risks),
        len(plan.qa_handoff),
    )

    return plan


def _detect_conflicts(
    expert_outputs: list[ExpertOutput],
    intent_constraints: list[str],
) -> list[Conflict]:
    """Detect conflicts between expert recommendations.

    Uses intent constraints as tie-breaker per 07-assembler.md.
    """
    conflicts: list[Conflict] = []

    # Compare each pair of experts for contradictions in assumptions
    for i, output_a in enumerate(expert_outputs):
        for output_b in expert_outputs[i + 1 :]:
            # Check for contradictory assumptions
            common_assumptions = set(output_a.assumptions) & set(output_b.assumptions)
            if not common_assumptions:
                continue

            # If experts share assumptions, check if recommendations diverge
            # (simplified: if both have recommendations but different assumptions exist)
            contradicting_a = set(output_a.assumptions) - set(output_b.assumptions)
            contradicting_b = set(output_b.assumptions) - set(output_a.assumptions)

            if contradicting_a and contradicting_b:
                # Attempt intent-based resolution
                resolution, resolved_by = _resolve_with_intent(
                    contradicting_a,
                    contradicting_b,
                    intent_constraints,
                )
                conflicts.append(
                    Conflict(
                        expert_a=output_a.expert_name,
                        expert_b=output_b.expert_name,
                        description=(
                            f"Divergent assumptions: {output_a.expert_name} assumes "
                            f"{contradicting_a}, {output_b.expert_name} assumes "
                            f"{contradicting_b}"
                        ),
                        resolution=resolution,
                        resolved_by=resolved_by,
                    )
                )

    return conflicts


def _resolve_with_intent(
    assumptions_a: set[str],
    assumptions_b: set[str],
    intent_constraints: list[str],
) -> tuple[str, str]:
    """Attempt to resolve a conflict using intent constraints as tie-breaker.

    Returns (resolution_description, resolved_by).
    """
    # Check if any intent constraint matches one side
    for constraint in intent_constraints:
        constraint_lower = constraint.lower()
        for assumption in assumptions_a:
            if assumption.lower() in constraint_lower:
                return (
                    f"Resolved by intent constraint: '{constraint}' aligns with first expert",
                    "intent",
                )
        for assumption in assumptions_b:
            if assumption.lower() in constraint_lower:
                return (
                    f"Resolved by intent constraint: '{constraint}' aligns with second expert",
                    "intent",
                )

    # Unresolved — triggers intent refinement
    return "Unresolved — intent refinement required", "unresolved"


def _build_qa_handoff(
    acceptance_criteria: list[str],
    expert_outputs: list[ExpertOutput],
) -> list[QAHandoffMapping]:
    """Map acceptance criteria to expert validations for QA handoff."""
    mappings: list[QAHandoffMapping] = []

    for criterion in acceptance_criteria:
        validation_steps: list[str] = []
        source_experts: list[str] = []

        criterion_lower = criterion.lower()
        for output in expert_outputs:
            for validation in output.validations:
                # Simple keyword matching for mapping
                if _has_keyword_overlap(criterion_lower, validation.lower()):
                    validation_steps.append(validation)
                    if output.expert_name not in source_experts:
                        source_experts.append(output.expert_name)

        # If no expert validations match, create a generic mapping
        if not validation_steps:
            validation_steps = [f"Validate: {criterion}"]

        mappings.append(
            QAHandoffMapping(
                criterion=criterion,
                validation_steps=validation_steps,
                source_experts=source_experts,
            )
        )

    return mappings


def format_expert_context(definition: dict[str, object]) -> str:
    """Format expert context files for inclusion in the expert's prompt.

    Reads ``definition["context_files"]`` (a dict of filename -> content)
    and returns formatted text with clear delimiters. Returns empty string
    if no context files are present.
    """
    context_files = definition.get("context_files", {})
    if not context_files or not isinstance(context_files, dict):
        return ""

    sections: list[str] = []
    for filename, content in context_files.items():
        sections.append(
            f"--- Expert Context: {filename} ---\n"
            f"{content}\n"
            f"--- End Expert Context ---"
        )
    return "\n\n".join(sections)


def _has_keyword_overlap(text_a: str, text_b: str) -> bool:
    """Check if two texts share meaningful keywords."""
    # Extract words of 4+ chars as keywords
    words_a = {w for w in text_a.split() if len(w) >= 4}
    words_b = {w for w in text_b.split() if len(w) >= 4}
    return bool(words_a & words_b)
