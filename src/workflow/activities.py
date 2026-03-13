"""Temporal activity definitions for the TheStudio pipeline.

Each activity wraps an existing module function and provides serializable
input/output via dataclasses. Activities are registered with the Temporal worker.

In production, activities receive database sessions and external clients from
the worker context. The intake and router activities call real pure functions.
Others are stubs that delegate to module functions when wired in production.

Architecture reference: thestudioarc/15-system-runtime-flow.md (runtime steps)
"""

from dataclasses import dataclass, field

from temporalio import activity

# --- Activity Input/Output Models ---
# All models use primitive/JSON-serializable types for Temporal wire format.


@dataclass
class IntakeInput:
    """Input for the intake activity."""

    labels: list[str]
    repo: str
    repo_registered: bool
    repo_paused: bool
    has_active_workflow: bool
    event_id: str


@dataclass
class IntakeOutput:
    """Output of the intake activity."""

    accepted: bool
    rejection_reason: str | None = None
    base_role: str | None = None
    overlays: list[str] = field(default_factory=list)


@dataclass
class ContextInput:
    """Input for the context enrichment activity."""

    taskpacket_id: str
    repo: str
    issue_title: str
    issue_body: str
    labels: list[str]


@dataclass
class ContextOutput:
    """Output of context enrichment."""

    scope: dict[str, str] = field(default_factory=dict)
    risk_flags: dict[str, bool] = field(default_factory=dict)
    complexity_index: str = "low"
    context_packs: list[dict[str, str]] = field(default_factory=list)


@dataclass
class ReadinessInput:
    """Input for the readiness gate activity."""

    taskpacket_id: str
    issue_title: str
    issue_body: str
    complexity_index: str = "low"
    risk_flags: dict[str, bool] = field(default_factory=dict)
    labels: list[str] = field(default_factory=list)
    trust_tier: str = "observe"


@dataclass
class ReadinessActivityOutput:
    """Output of the readiness gate activity."""

    proceed: bool = True
    overall_score: float = 1.0
    gate_decision: str = "pass"
    clarification_questions: list[str] = field(default_factory=list)
    missing_dimensions: list[str] = field(default_factory=list)
    hold_reason: str | None = None


@dataclass
class IntentInput:
    """Input for the intent building activity."""

    taskpacket_id: str
    issue_title: str
    issue_body: str
    risk_flags: dict[str, bool] = field(default_factory=dict)


@dataclass
class IntentOutput:
    """Output of intent building."""

    intent_spec_id: str
    version: int
    goal: str
    acceptance_criteria: list[str] = field(default_factory=list)


@dataclass
class RouterInput:
    """Input for the expert routing activity."""

    base_role: str
    overlays: list[str]
    risk_flags: dict[str, bool] = field(default_factory=dict)


@dataclass
class RouterOutput:
    """Output of expert routing."""

    selections: list[dict[str, str]] = field(default_factory=list)
    recruiter_requests: list[dict[str, str]] = field(default_factory=list)
    rationale: str = ""


@dataclass
class AssemblerInput:
    """Input for the assembler activity."""

    taskpacket_id: str
    expert_outputs: list[dict[str, str]] = field(default_factory=list)
    intent_goal: str = ""
    intent_constraints: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)


@dataclass
class AssemblerOutput:
    """Output of the assembler."""

    plan_steps: list[str] = field(default_factory=list)
    conflicts: list[dict[str, str]] = field(default_factory=list)
    qa_handoff: list[dict[str, str]] = field(default_factory=list)
    provenance: dict[str, str] = field(default_factory=dict)
    needs_intent_refinement: bool = False


@dataclass
class ImplementInput:
    """Input for the implementation activity."""

    taskpacket_id: str
    repo_path: str
    loopback_attempt: int = 0


@dataclass
class ImplementOutput:
    """Output of the implementation activity."""

    taskpacket_id: str
    intent_version: int = 1
    files_changed: list[str] = field(default_factory=list)
    agent_summary: str = ""


@dataclass
class VerifyInput:
    """Input for the verification activity."""

    taskpacket_id: str
    changed_files: list[str] = field(default_factory=list)
    repo_path: str = ""


@dataclass
class VerifyOutput:
    """Output of the verification activity."""

    passed: bool = False
    loopback_triggered: bool = False
    exhausted: bool = False
    checks: list[dict[str, str]] = field(default_factory=list)


@dataclass
class QAInput:
    """Input for the QA validation activity."""

    taskpacket_id: str
    acceptance_criteria: list[str] = field(default_factory=list)
    qa_handoff: list[dict[str, str]] = field(default_factory=list)
    evidence: dict[str, str] = field(default_factory=dict)


@dataclass
class QAOutput:
    """Output of the QA validation activity."""

    passed: bool = False
    has_intent_gap: bool = False
    defect_count: int = 0
    needs_loopback: bool = False
    needs_intent_refinement: bool = False


@dataclass
class PublishInput:
    """Input for the publish activity."""

    taskpacket_id: str
    repo_tier: str = "observe"
    qa_passed: bool = False


@dataclass
class PublishOutput:
    """Output of the publish activity."""

    pr_number: int = 0
    pr_url: str = ""
    created: bool = False
    marked_ready: bool = False


# --- Activity Implementations ---
# The intake and router activities call real pure functions (no DB dependency).
# Others are stubs that return sensible defaults; in production they delegate
# to existing module functions via the Temporal worker context.


@activity.defn
async def intake_activity(params: IntakeInput) -> IntakeOutput:
    """Step 1: Evaluate eligibility and select role.

    Calls the real evaluate_eligibility() — it is pure (no DB).
    """
    from src.intake.intake_agent import evaluate_eligibility

    result = evaluate_eligibility(
        labels=params.labels,
        repo=params.repo,
        repo_registered=params.repo_registered,
        repo_paused=params.repo_paused,
        has_active_workflow=params.has_active_workflow,
        event_id=params.event_id,
    )

    if not result.accepted:
        return IntakeOutput(
            accepted=False,
            rejection_reason=result.rejection.reason if result.rejection else "Unknown",
        )

    policy = result.effective_role
    if policy is None:
        msg = "Accepted intake result must have effective_role"
        raise RuntimeError(msg)
    return IntakeOutput(
        accepted=True,
        base_role=policy.base_role.value,
        overlays=[o.value for o in policy.overlays],
    )


@activity.defn
async def context_activity(params: ContextInput) -> ContextOutput:
    """Step 2: Context enrichment (scope, risk, complexity).

    Routes LLM calls through Model Gateway; checks Tool Hub access for
    context-retrieval tools. In production, delegates to
    context_manager.enrich_taskpacket() with a real database session.
    """
    from src.admin.model_gateway import ModelCallAudit, get_model_audit_store, get_model_router
    from src.admin.tool_catalog import get_tool_policy_engine

    router = get_model_router()
    audit_store = get_model_audit_store()
    policy = get_tool_policy_engine()

    # Select model via gateway (no direct provider calls)
    provider = router.select_model(step="context")
    audit_store.record(
        ModelCallAudit(step="context", provider=provider.provider, model=provider.model_id)
    )

    # Verify tool access for context-retrieval suite
    policy.check_access(
        role="developer",
        overlays=[],
        repo_tier="observe",
        suite_name="context-retrieval",
        tool_name="pack-lookup",
    )

    return ContextOutput(
        scope={"type": "feature", "components": ""},
        risk_flags={},
        complexity_index="low",
        context_packs=[],
    )


@activity.defn
async def readiness_activity(params: ReadinessInput) -> ReadinessActivityOutput:
    """Step 2.5: Readiness gate — score issue quality before intent building.

    Calls the pure scoring engine (no I/O). Gate decision determines whether
    the pipeline proceeds to Intent or holds for clarification.
    """
    import logging

    from src.readiness.models import ComplexityTier
    from src.readiness.scorer import score_readiness

    logger = logging.getLogger("thestudio.readiness")

    # Map complexity_index string to tier
    tier_map = {
        "low": ComplexityTier.LOW,
        "medium": ComplexityTier.MEDIUM,
        "high": ComplexityTier.HIGH,
    }
    complexity_tier = tier_map.get(params.complexity_index, ComplexityTier.LOW)

    result = score_readiness(
        issue_title=params.issue_title,
        issue_body=params.issue_body,
        complexity_tier=complexity_tier,
        risk_flags=params.risk_flags or None,
        labels=params.labels,
        trust_tier=params.trust_tier,
    )

    proceed = result.gate_decision.value == "pass"

    logger.info(
        "readiness.gate.evaluated",
        extra={
            "taskpacket_id": params.taskpacket_id,
            "overall_score": result.overall_score,
            "gate_decision": result.gate_decision.value,
            "missing_dimensions": [d.value for d in result.missing_dimensions],
            "proceed": proceed,
        },
    )

    hold_reason = None
    if not proceed:
        hold_reason = (
            f"Readiness score {result.overall_score:.2f} below threshold; "
            f"missing: {', '.join(d.value for d in result.missing_dimensions)}"
        )

    return ReadinessActivityOutput(
        proceed=proceed,
        overall_score=result.overall_score,
        gate_decision=result.gate_decision.value,
        clarification_questions=list(result.recommended_questions),
        missing_dimensions=[d.value for d in result.missing_dimensions],
        hold_reason=hold_reason,
    )


@activity.defn
async def intent_activity(params: IntentInput) -> IntentOutput:
    """Step 3: Build intent specification.

    Routes LLM calls through Model Gateway. In production, delegates to
    intent_builder.build_intent() with a real database session.
    """
    from src.admin.model_gateway import ModelCallAudit, get_model_audit_store, get_model_router

    router = get_model_router()
    audit_store = get_model_audit_store()

    # All LLM calls go through gateway — no direct provider access
    overlays = [k for k, v in params.risk_flags.items() if v]
    provider = router.select_model(step="intent", overlays=overlays)
    audit_store.record(
        ModelCallAudit(
            step="intent", provider=provider.provider, model=provider.model_id, overlays=overlays
        )
    )

    return IntentOutput(
        intent_spec_id="",
        version=1,
        goal=params.issue_title,
        acceptance_criteria=[],
    )


@activity.defn
async def router_activity(params: RouterInput) -> RouterOutput:
    """Step 4: Route to expert subset.

    Calls the real router.route() — it is pure (no DB dependency).
    """
    from src.intake.effective_role import BaseRole, EffectiveRolePolicy, Overlay
    from src.routing.router import route

    overlays = [Overlay(o) for o in params.overlays]
    policy = EffectiveRolePolicy.compute(BaseRole(params.base_role), overlays)
    plan = route(policy, params.risk_flags, [])

    return RouterOutput(
        selections=[
            {
                "expert_id": str(s.expert_id),
                "expert_version": s.expert_version,
                "expert_class": s.expert_class.value,
                "pattern": s.pattern,
            }
            for s in plan.selections
        ],
        recruiter_requests=[
            {
                "expert_class": r.expert_class.value,
                "capability_tags": ",".join(r.capability_tags),
                "reason": r.reason,
            }
            for r in plan.recruiter_requests
        ],
        rationale=plan.rationale,
    )


@activity.defn
async def assembler_activity(params: AssemblerInput) -> AssemblerOutput:
    """Step 5: Assemble expert outputs into plan.

    In production, delegates to assembler.assemble(). Stub returns defaults.
    """
    return AssemblerOutput(
        plan_steps=["implement_changes"],
        qa_handoff=[],
        provenance={"taskpacket_id": params.taskpacket_id},
    )


@activity.defn
async def implement_activity(params: ImplementInput) -> ImplementOutput:
    """Step 6: Primary Agent implements changes.

    Routes LLM calls through Model Gateway; checks Tool Hub access for
    code-quality tools. In production, delegates to
    primary_agent.implement() or handle_loopback().
    """
    from src.admin.model_gateway import ModelCallAudit, get_model_audit_store, get_model_router
    from src.admin.tool_catalog import get_tool_policy_engine

    router = get_model_router()
    audit_store = get_model_audit_store()
    policy = get_tool_policy_engine()

    # All LLM calls through gateway
    provider = router.select_model(step="primary_agent")
    audit_store.record(
        ModelCallAudit(step="primary_agent", provider=provider.provider, model=provider.model_id)
    )

    # Verify tool access for code-quality suite
    policy.check_access(
        role="developer",
        overlays=[],
        repo_tier="observe",
        suite_name="code-quality",
        tool_name="ruff",
    )

    return ImplementOutput(
        taskpacket_id=params.taskpacket_id,
        intent_version=1,
        files_changed=[],
        agent_summary="Implementation placeholder",
    )


@activity.defn
async def verify_activity(params: VerifyInput) -> VerifyOutput:
    """Step 7: Verification gate checks.

    Checks Tool Hub access for code-quality tools used during verification.
    In production, delegates to verification.gate.verify().
    """
    from src.admin.tool_catalog import get_tool_policy_engine

    policy = get_tool_policy_engine()

    # Verify tool access for code-quality suite (ruff, mypy)
    policy.check_access(
        role="developer",
        overlays=[],
        repo_tier="observe",
        suite_name="code-quality",
        tool_name="ruff",
    )

    return VerifyOutput(passed=True, checks=[])


@activity.defn
async def qa_activity(params: QAInput) -> QAOutput:
    """Step 8: QA validation against intent.

    Routes LLM calls through Model Gateway. In production, delegates to
    qa.qa_agent.validate().
    """
    from src.admin.model_gateway import ModelCallAudit, get_model_audit_store, get_model_router

    router = get_model_router()
    audit_store = get_model_audit_store()

    # All LLM calls through gateway
    provider = router.select_model(step="qa_eval")
    audit_store.record(
        ModelCallAudit(step="qa_eval", provider=provider.provider, model=provider.model_id)
    )

    return QAOutput(passed=True)


@activity.defn
async def publish_activity(params: PublishInput) -> PublishOutput:
    """Step 9: Publish PR to GitHub.

    In production, delegates to publisher.publisher.publish().
    Records a TimingEvent on completion for lead/cycle time tracking.
    """
    from datetime import UTC, datetime

    from src.admin.operational_targets import TimingEvent, record_timing

    now = datetime.now(UTC)

    # Record timing event for operational targets tracking.
    # In production, intake_created_at comes from the TaskPacket; here we
    # use 'now' as a placeholder since the stub has no DB access.
    record_timing(
        TimingEvent(
            repo_id=params.taskpacket_id,
            intake_created_at=now,
            pr_opened_at=now,
            merge_ready_at=now if params.qa_passed else None,
        )
    )

    return PublishOutput(
        pr_number=0,
        pr_url="",
        created=False,
        marked_ready=False,
    )
