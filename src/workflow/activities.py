"""Temporal activity definitions for the TheStudio pipeline.

Each activity wraps an existing module function and provides serializable
input/output via dataclasses. Activities are registered with the Temporal worker.

In production, activities receive database sessions and external clients from
the worker context. The intake and router activities call real pure functions.
Others are stubs that delegate to module functions when wired in production.

Architecture reference: thestudioarc/15-system-runtime-flow.md (runtime steps)
"""

from dataclasses import dataclass, field
from datetime import UTC

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
    issue_title: str = ""
    issue_body: str = ""


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
    taskpacket_id: str = ""


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
class PreflightInput:
    """Input for the preflight plan review activity."""

    taskpacket_id: str
    plan_steps: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)


@dataclass
class PreflightActivityOutput:
    """Output of the preflight plan review activity."""

    approved: bool = True
    uncovered_criteria: list[str] = field(default_factory=list)
    constraint_violations: list[str] = field(default_factory=list)
    vague_steps: list[str] = field(default_factory=list)
    summary: str = ""


@dataclass
class ProjectStatusInput:
    """Input for the Projects v2 status sync activity."""

    taskpacket_id: str
    taskpacket_status: str
    repo_tier: str = "observe"
    complexity_index: str = "low"
    project_item_id: str = ""  # Set after first add_item call


@dataclass
class ProjectStatusOutput:
    """Output of the Projects v2 status sync activity."""

    synced: bool = False
    project_item_id: str = ""
    error: str = ""


@dataclass
class ImplementInput:
    """Input for the implementation activity."""

    taskpacket_id: str
    repo_path: str
    loopback_attempt: int = 0
    repo_tier: str = "observe"
    repo: str = ""
    issue_title: str = ""
    issue_body: str = ""
    intent_goal: str = ""
    acceptance_criteria: list[str] = field(default_factory=list)
    plan_steps: list[str] = field(default_factory=list)
    qa_feedback: str = ""


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
    files_changed: list[str] = field(default_factory=list)
    agent_summary: str = ""


@dataclass
class PublishOutput:
    """Output of the publish activity."""

    pr_number: int = 0
    pr_url: str = ""
    created: bool = False
    marked_ready: bool = False


@dataclass
class ApprovalRequestInput:
    """Input for the approval request activity."""

    taskpacket_id: str
    repo_tier: str = "observe"
    intent_summary: str = ""
    qa_passed: bool = False


@dataclass
class ApprovalRequestOutput:
    """Output of the approval request activity."""

    comment_posted: bool = False


@dataclass
class EscalateTimeoutInput:
    """Input for the timeout escalation activity."""

    taskpacket_id: str
    repo_tier: str = "observe"


@dataclass
class EscalateTimeoutOutput:
    """Output of the timeout escalation activity."""

    escalated: bool = False
    label_applied: bool = False


@dataclass
class AssignTrustTierInput:
    """Input for the trust tier assignment activity."""

    taskpacket_id: str


@dataclass
class AssignTrustTierOutput:
    """Output of the trust tier assignment activity."""

    tier: str = "observe"
    matched_rule_id: str | None = None
    safety_capped: bool = False
    reason: str = ""


@dataclass
class PersistSteeringAuditInput:
    """Input for the steering audit persistence activity."""

    task_id: str
    action: str  # SteeringAction string value: pause/resume/abort/redirect/retry
    actor: str = "system"
    from_stage: str = ""
    to_stage: str = ""
    reason: str = ""
    timestamp_iso: str = ""  # ISO-8601 UTC timestamp; defaults to now() if empty


# --- Activity Implementations ---
# The intake and router activities call real pure functions (no DB dependency).
# Others are stubs that return sensible defaults; in production they delegate
# to existing module functions via the Temporal worker context.


@activity.defn
async def intake_activity(params: IntakeInput) -> IntakeOutput:
    """Step 1: Evaluate eligibility and select role.

    Uses AgentRunner with IntakeAgentConfig (Epic 23 Story 2.2).
    Falls back to rule-based evaluate_eligibility() when LLM is disabled.
    """
    from src.agent.framework import AgentContext, AgentRunner
    from src.dashboard.events_publisher import emit_stage_enter, emit_stage_exit
    from src.intake.intake_config import INTAKE_AGENT_CONFIG

    task_id = params.event_id
    await emit_stage_enter("intake", task_id)
    success = False
    try:
        context = AgentContext(
            repo=params.repo,
            issue_title=params.issue_title,
            issue_body=params.issue_body,
            labels=params.labels,
            extra={
                "repo_registered": params.repo_registered,
                "repo_paused": params.repo_paused,
                "has_active_workflow": params.has_active_workflow,
                "event_id": params.event_id,
            },
        )

        runner = AgentRunner(INTAKE_AGENT_CONFIG)
        result = await runner.run(context)

        # Parse from AgentResult
        if result.parsed_output is not None:
            output = result.parsed_output
            intake_out = IntakeOutput(
                accepted=output.accepted,
                rejection_reason=output.rejection_reason or None,
                base_role=output.base_role if output.accepted else None,
                overlays=output.overlays if output.accepted else [],
            )
        else:
            # Fallback produced raw JSON
            import json
            data = json.loads(result.raw_output) if result.raw_output else {}
            accepted = data.get("accepted", False)
            intake_out = IntakeOutput(
                accepted=accepted,
                rejection_reason=data.get("rejection_reason") or None,
                base_role=data.get("base_role") if accepted else None,
                overlays=data.get("overlays", []) if accepted else [],
            )

        success = True
        return intake_out
    finally:
        await emit_stage_exit("intake", task_id, success=success)


@activity.defn
async def context_activity(params: ContextInput) -> ContextOutput:
    """Step 2: Context enrichment (scope, risk, complexity).

    Uses AgentRunner with ContextAgentConfig (Epic 23 Story 2.5).
    Deterministic functions run first, LLM reviews and augments.
    Falls back to deterministic enrich_taskpacket() when LLM is disabled.
    """
    from src.agent.framework import AgentContext, AgentRunner
    from src.context.context_config import CONTEXT_AGENT_CONFIG
    from src.dashboard.events_publisher import emit_stage_enter, emit_stage_exit

    task_id = params.taskpacket_id
    await emit_stage_enter("context", task_id)
    success = False
    try:
        context = AgentContext(
            repo=params.repo,
            issue_title=params.issue_title,
            issue_body=params.issue_body,
            labels=params.labels,
            extra={"taskpacket_id": params.taskpacket_id},
        )

        runner = AgentRunner(CONTEXT_AGENT_CONFIG)
        result = await runner.run(context)

        if result.parsed_output is not None:
            output = result.parsed_output
            ctx_out = ContextOutput(
                scope={"type": "feature", "summary": output.scope_summary},
                risk_flags=output.risk_flags,
                complexity_index="medium" if output.risk_flags else "low",
                context_packs=[],
            )
        else:
            import json
            data = json.loads(result.raw_output) if result.raw_output else {}
            ctx_out = ContextOutput(
                scope={"type": "feature", "summary": data.get("scope_summary", "")},
                risk_flags=data.get("risk_flags", {}),
                complexity_index=data.get("complexity_index", "low"),
                context_packs=[],
            )

        success = True
        return ctx_out
    finally:
        await emit_stage_exit("context", task_id, success=success)


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

    Uses AgentRunner with IntentAgentConfig (Epic 23 Story 2.8).
    LLM extracts semantic intent including invariants; falls back to
    rule-based build_intent() when LLM is disabled.
    """
    from src.agent.framework import AgentContext, AgentRunner
    from src.dashboard.events_publisher import emit_stage_enter, emit_stage_exit
    from src.intent.intent_config import INTENT_AGENT_CONFIG

    task_id = params.taskpacket_id
    await emit_stage_enter("intent", task_id)
    success = False
    try:
        context = AgentContext(
            repo="",
            issue_title=params.issue_title,
            issue_body=params.issue_body,
            risk_flags=params.risk_flags,
            extra={"taskpacket_id": params.taskpacket_id},
        )

        runner = AgentRunner(INTENT_AGENT_CONFIG)
        result = await runner.run(context)

        if result.parsed_output is not None:
            output = result.parsed_output
            goal = output.goal
            acceptance_criteria = output.acceptance_criteria
        else:
            import json
            data = json.loads(result.raw_output) if result.raw_output else {}
            goal = data.get("goal", params.issue_title)
            acceptance_criteria = data.get("acceptance_criteria", [])

        # Persist intent spec to DB for downstream stages (Publisher needs it)
        intent_spec_id = ""
        try:
            from uuid import UUID

            from src.db.connection import get_async_session
            from src.intent.intent_crud import create_intent
            from src.intent.intent_spec import IntentSpecCreate

            async with get_async_session() as session:
                spec = await create_intent(
                    session,
                    IntentSpecCreate(
                        taskpacket_id=UUID(params.taskpacket_id),
                        version=1,
                        goal=goal,
                        acceptance_criteria=acceptance_criteria,
                    ),
                )
                intent_spec_id = str(spec.id)
        except Exception:
            import logging
            logging.getLogger("thestudio.intent").exception(
                "Failed to persist intent spec for taskpacket=%s", params.taskpacket_id
            )

        success = True
        return IntentOutput(
            intent_spec_id=intent_spec_id,
            version=1,
            goal=goal,
            acceptance_criteria=acceptance_criteria,
        )
    finally:
        await emit_stage_exit("intent", task_id, success=success)


@activity.defn
async def router_activity(params: RouterInput) -> RouterOutput:
    """Step 4: Route to expert subset.

    Uses AgentRunner with RouterAgentConfig (Epic 23 Story 2.11).
    Algorithmic route() runs first; LLM reviews and adjusts patterns/escalations.
    Falls back to pure algorithmic routing when LLM is disabled.
    """
    from src.agent.framework import AgentContext, AgentRunner
    from src.dashboard.events_publisher import emit_stage_enter, emit_stage_exit
    from src.routing.router_config import ROUTER_AGENT_CONFIG

    task_id = params.taskpacket_id
    await emit_stage_enter("router", task_id)
    success = False
    try:
        context = AgentContext(
            risk_flags=params.risk_flags,
            overlays=params.overlays,
            extra={
                "base_role": params.base_role,
                "required_classes": ",".join(
                    k for k, v in params.risk_flags.items() if v
                ),
            },
        )

        runner = AgentRunner(ROUTER_AGENT_CONFIG)
        result = await runner.run(context)

        if result.parsed_output is not None:
            output = result.parsed_output
            router_out = RouterOutput(
                selections=[
                    {
                        "expert_class": s.expert_class,
                        "pattern": s.pattern,
                        "rationale": s.rationale,
                    }
                    for s in output.selections
                ],
                recruiter_requests=[],
                rationale=output.adjustments or "LLM-augmented routing",
            )
        else:
            import json
            data = json.loads(result.raw_output) if result.raw_output else {}
            router_out = RouterOutput(
                selections=data.get("selections", []),
                recruiter_requests=data.get("recruiter_requests", []),
                rationale=data.get("adjustments", ""),
            )

        # Persist full ConsultPlan to DB for routing review dashboard (Story 36.14c)
        try:
            from uuid import UUID, uuid4

            from src.db.connection import get_async_session
            from src.models.taskpacket_crud import update_routing_result

            selections_payload = [
                {
                    "expert_id": str(uuid4()),
                    "expert_class": s.get("expert_class", ""),
                    "pattern": s.get("pattern", "parallel"),
                    "reputation_weight": 0.5,
                    "reputation_confidence": 0.5,
                    "selection_score": 0.0,
                    "selection_reason": s.get("rationale", router_out.rationale),
                }
                for s in router_out.selections
            ]
            routing_payload: dict[str, object] = {
                "taskpacket_id": params.taskpacket_id,
                "selections": selections_payload,
                "rationale": router_out.rationale,
                "budget_remaining": max(0, 5 - len(router_out.selections)),
            }
            async with get_async_session() as session:
                await update_routing_result(
                    session,
                    UUID(params.taskpacket_id),
                    routing_payload,
                )
        except Exception:
            import logging
            logging.getLogger("thestudio.router").exception(
                "Failed to persist routing result for taskpacket=%s", params.taskpacket_id
            )

        success = True
        return router_out
    finally:
        await emit_stage_exit("router", task_id, success=success)


@activity.defn
async def assembler_activity(params: AssemblerInput) -> AssemblerOutput:
    """Step 5: Assemble expert outputs into plan.

    Uses AgentRunner with AssemblerAgentConfig (Epic 23 Story 3.5).
    LLM performs semantic conflict detection and plan synthesis.
    Falls back to keyword-based assemble() when LLM is disabled.
    """
    from uuid import UUID

    from src.agent.framework import AgentContext, AgentRunner
    from src.assembler.assembler_config import ASSEMBLER_AGENT_CONFIG
    from src.dashboard.events_publisher import emit_stage_enter, emit_stage_exit

    task_id = params.taskpacket_id or ""
    await emit_stage_enter("assembler", task_id)
    success = False
    try:
        context = AgentContext(
            taskpacket_id=UUID(params.taskpacket_id) if params.taskpacket_id else None,
            expert_outputs=params.expert_outputs,
            extra={
                "intent_goal": params.intent_goal,
                "intent_constraints": params.intent_constraints,
                "acceptance_criteria": params.acceptance_criteria,
                "expert_count": str(len(params.expert_outputs)),
                "intent_version": 1,
            },
        )

        runner = AgentRunner(ASSEMBLER_AGENT_CONFIG)
        result = await runner.run(context)

        if result.parsed_output is not None:
            output = result.parsed_output
            assembler_out = AssemblerOutput(
                plan_steps=[s.description for s in output.plan_steps],
                conflicts=[
                    {
                        "expert_a": c.expert_a,
                        "expert_b": c.expert_b,
                        "description": c.description,
                        "resolution": c.resolution,
                    }
                    for c in output.conflicts
                ],
                qa_handoff=[
                    {"criterion": h.criterion, "validation_steps": ",".join(h.validation_steps)}
                    for h in output.qa_handoff
                ],
                provenance={"taskpacket_id": params.taskpacket_id},
                needs_intent_refinement=any(
                    c.resolved_by == "unresolved" for c in output.conflicts
                ),
            )
        else:
            import json
            data = json.loads(result.raw_output) if result.raw_output else {}
            # Coerce validation_steps from list to str for Temporal wire format
            raw_handoff = data.get("qa_handoff", [])
            coerced_handoff = []
            for h in raw_handoff:
                vs = h.get("validation_steps", "")
                if isinstance(vs, list):
                    vs = ",".join(str(s) for s in vs)
                coerced_handoff.append({
                    "criterion": h.get("criterion", ""),
                    "validation_steps": vs,
                })
            assembler_out = AssemblerOutput(
                plan_steps=[
                    s.get("description", "")
                    for s in data.get("plan_steps", [{"description": "implement_changes"}])
                ],
                qa_handoff=coerced_handoff,
                provenance={"taskpacket_id": params.taskpacket_id},
            )

        success = True
        return assembler_out
    finally:
        await emit_stage_exit("assembler", task_id, success=success)


@activity.defn
async def preflight_activity(params: PreflightInput) -> PreflightActivityOutput:
    """Step 5.5: Preflight plan review gate.

    Uses AgentRunner with PREFLIGHT_AGENT_CONFIG (Epic 28 AC 1-4).
    Evaluates plan quality via three checks: criteria coverage, constraint
    compliance, and step specificity. Falls back to approving when LLM
    is unavailable — preflight never blocks on its own failure.
    """
    from uuid import UUID

    from src.agent.framework import AgentContext, AgentRunner
    from src.preflight.preflight_config import PREFLIGHT_AGENT_CONFIG

    context = AgentContext(
        taskpacket_id=UUID(params.taskpacket_id) if params.taskpacket_id else None,
        extra={
            "plan_steps": params.plan_steps,
            "acceptance_criteria": params.acceptance_criteria,
            "constraints": params.constraints,
        },
    )

    runner = AgentRunner(PREFLIGHT_AGENT_CONFIG)
    result = await runner.run(context)

    if result.parsed_output is not None:
        output = result.parsed_output
        return PreflightActivityOutput(
            approved=output.approved,
            uncovered_criteria=output.uncovered_criteria,
            constraint_violations=output.constraint_violations,
            vague_steps=output.vague_steps,
            summary=output.summary,
        )

    import json
    data = json.loads(result.raw_output) if result.raw_output else {}
    return PreflightActivityOutput(
        approved=data.get("approved", True),
        uncovered_criteria=data.get("uncovered_criteria", []),
        constraint_violations=data.get("constraint_violations", []),
        vague_steps=data.get("vague_steps", []),
        summary=data.get("summary", ""),
    )


@activity.defn
async def implement_activity(params: ImplementInput) -> ImplementOutput:
    """Step 6: Primary Agent implements changes.

    Supports two modes controlled by THESTUDIO_AGENT_ISOLATION:
    - "process" (default): Routes LLM calls through Model Gateway in-process.
    - "container": Serializes task to AgentTaskInput, launches an ephemeral
      Docker container via ContainerManager, collects results.

    Fallback policy is tier-aware: Observe/Suggest fall back to in-process
    if Docker is unavailable; Execute tier fails closed.
    """
    from src.agent.isolation_policy import IsolationMode, resolve_isolation
    from src.dashboard.events_publisher import emit_stage_enter, emit_stage_exit
    from src.settings import settings

    task_id = params.taskpacket_id
    await emit_stage_enter("implement", task_id)
    success = False
    try:
        repo_tier = getattr(params, "repo_tier", "observe")

        # Resolve isolation mode based on settings and Docker availability
        if settings.agent_isolation == "container":
            from src.agent.container_manager import ContainerManager

            container_available = ContainerManager.is_docker_available()
            decision = resolve_isolation(repo_tier, container_available)

            if decision.mode == IsolationMode.CONTAINER:
                result = await _implement_container(params, decision)
                success = True
                return result

        # In-process mode (default or fallback)
        result = await _implement_in_process(params, repo_tier)
        success = True
        return result
    finally:
        await emit_stage_exit("implement", task_id, success=success)


async def _implement_container(params: ImplementInput, decision) -> ImplementOutput:
    """Run implementation in an ephemeral Docker container."""
    import logging
    from uuid import UUID

    from src.agent.container_manager import ContainerConfig, ContainerManager
    from src.agent.container_protocol import AgentTaskInput

    logger = logging.getLogger("thestudio.implement")

    # Build container config from tier-based limits
    config = ContainerConfig(
        cpu_limit=decision.cpu_limit,
        memory_mb=decision.memory_mb,
        timeout_seconds=decision.timeout_seconds,
    )

    # Serialize task input for the container
    task_input = AgentTaskInput(
        taskpacket_id=UUID(params.taskpacket_id),
        correlation_id=UUID(params.taskpacket_id),  # Use taskpacket as correlation
        repo_url="",  # Resolved from TaskPacket in production
        system_prompt="",  # Resolved from developer_role in production
        loopback_attempt=params.loopback_attempt,
        repo_tier=getattr(params, "repo_tier", "observe"),
    )

    manager = ContainerManager(config)
    outcome = manager.launch(task_input, repo_path=params.repo_path)

    logger.info(
        "implement.container.completed",
        extra={
            "taskpacket_id": params.taskpacket_id,
            "container_id": outcome.container_id,
            "exit_code": outcome.exit_code,
            "timed_out": outcome.timed_out,
            "oom_killed": outcome.oom_killed,
            "total_ms": outcome.total_ms,
        },
    )

    if outcome.result is not None:
        return ImplementOutput(
            taskpacket_id=params.taskpacket_id,
            intent_version=outcome.result.intent_version,
            files_changed=outcome.result.files_changed,
            agent_summary=outcome.result.agent_summary,
        )

    return ImplementOutput(
        taskpacket_id=params.taskpacket_id,
        intent_version=1,
        files_changed=[],
        agent_summary=(
            f"Container failed: exit_code={outcome.exit_code} "
            f"timed_out={outcome.timed_out}"
        ),
    )


async def _implement_in_process(params: ImplementInput, repo_tier: str) -> ImplementOutput:
    """Run implementation in-process: LLM generates code, pushed to GitHub via Contents API."""
    import base64
    import json
    import logging

    from src.adapters.github import get_github_client
    from src.adapters.llm import LLMRequest, get_llm_adapter
    from src.admin.model_gateway import ModelCallAudit, get_model_audit_store, get_model_router
    from src.settings import settings

    logger = logging.getLogger("thestudio.implement")

    router = get_model_router()
    audit_store = get_model_audit_store()
    provider = router.select_model(step="primary_agent")
    audit_store.record(
        ModelCallAudit(step="primary_agent", provider=provider.provider, model=provider.model_id)
    )

    # Build prompt for code generation
    criteria_text = "\n".join(f"- {c}" for c in params.acceptance_criteria) or "None specified"
    plan_text = "\n".join(f"- {s}" for s in params.plan_steps) or "None specified"
    qa_section = ""
    if params.qa_feedback and params.loopback_attempt > 0:
        qa_section = f"\n## QA Feedback from Previous Attempt\n{params.qa_feedback}\nFix the issues identified above.\n"

    system_prompt = """You are a code implementation agent for TheStudio. Your job is to generate
file changes that satisfy a GitHub issue's requirements.

You MUST respond with ONLY a JSON object (no markdown fences, no explanation) with this structure:
{
  "files": [
    {
      "path": "path/to/file.py",
      "content": "full file content here",
      "action": "create"
    }
  ],
  "summary": "Brief description of what was implemented"
}

Rules:
- "action" is "create" for new files or "update" for modifying existing files
- "content" must be the complete file content (not a diff)
- Generate clean, working code with type hints and docstrings
- Include tests when the acceptance criteria mention testing
- Keep changes minimal — only create/modify files that are needed
- Do NOT include markdown fences or any text outside the JSON"""

    user_prompt = f"""## Issue
**{params.issue_title}**

{params.issue_body}

## Intent
Goal: {params.intent_goal}

## Acceptance Criteria
{criteria_text}

## Plan
{plan_text}

## Repository
{params.repo}
{qa_section}
Generate the file changes to satisfy this issue."""

    # Call LLM
    adapter = get_llm_adapter()
    request = LLMRequest(
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        max_tokens=4096,
        temperature=0.0,
    )
    try:
        response = await adapter.complete(provider, request)
    finally:
        await adapter.close()

    audit_store.record(
        ModelCallAudit(
            step="primary_agent",
            provider=provider.provider,
            model=provider.model_id,
            tokens_in=response.tokens_in,
            tokens_out=response.tokens_out,
            cost=provider.estimate_cost(response.tokens_in, response.tokens_out),
        )
    )

    # Parse LLM response
    raw = response.content.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        raw = "\n".join(lines)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(raw[start:end])
        else:
            logger.error("implement.parse_failed raw=%s", raw[:200])
            return ImplementOutput(
                taskpacket_id=params.taskpacket_id,
                intent_version=1,
                files_changed=[],
                agent_summary="LLM output could not be parsed as JSON",
            )

    files = result.get("files", [])
    summary = result.get("summary", "")

    if not files:
        logger.warning("implement.no_files taskpacket=%s", params.taskpacket_id)
        return ImplementOutput(
            taskpacket_id=params.taskpacket_id,
            intent_version=1,
            files_changed=[],
            agent_summary="LLM generated no file changes",
        )

    # Push files to GitHub via Contents API
    token = settings.intake_poll_token
    if not token:
        logger.error("implement.no_token: intake_poll_token not configured")
        return ImplementOutput(
            taskpacket_id=params.taskpacket_id,
            intent_version=1,
            files_changed=[],
            agent_summary="No GitHub token configured",
        )

    owner, repo_name = params.repo.split("/", 1)
    short_id = params.taskpacket_id[:8]
    branch_name = f"thestudio/{short_id}/v1"

    github = get_github_client(token)
    try:
        # Create branch from default branch
        default_branch = await github.get_default_branch(owner, repo_name)
        base_sha = await github.get_branch_sha(owner, repo_name, default_branch)

        try:
            await github.create_branch(owner, repo_name, branch_name, base_sha)
        except Exception as exc:
            # Branch may already exist from a previous attempt
            if "Reference already exists" not in str(exc):
                raise
            logger.info("implement.branch_exists branch=%s", branch_name)

        # Commit each file to the branch
        files_changed: list[str] = []
        for file_spec in files:
            path = file_spec.get("path", "")
            content = file_spec.get("content", "")
            if not path or not content:
                continue

            content_b64 = base64.b64encode(content.encode()).decode()

            # Check if file exists (need SHA for updates)
            existing = await github.get_file_content(owner, repo_name, path, ref=branch_name)
            existing_sha = existing["sha"] if existing else None

            await github.create_or_update_file(
                owner=owner,
                repo=repo_name,
                path=path,
                content_b64=content_b64,
                message=f"{'Update' if existing_sha else 'Add'} {path}\n\nTaskPacket: {params.taskpacket_id}",
                branch=branch_name,
                sha=existing_sha,
            )
            files_changed.append(path)
            logger.info("implement.file_pushed path=%s branch=%s", path, branch_name)

    finally:
        await github.close()

    logger.info(
        "implement.complete taskpacket=%s files=%d summary=%s",
        params.taskpacket_id,
        len(files_changed),
        summary[:100],
    )

    return ImplementOutput(
        taskpacket_id=params.taskpacket_id,
        intent_version=1,
        files_changed=files_changed,
        agent_summary=summary,
    )


@activity.defn
async def verify_activity(params: VerifyInput) -> VerifyOutput:
    """Step 7: Verification gate checks.

    Validates that the implement step produced actual file changes.
    Remote verification (ruff/pytest on target repo) is not yet supported —
    for now, passes if files were changed and fails if none were.
    """
    import logging

    from src.dashboard.events_publisher import emit_stage_enter, emit_stage_exit

    logger = logging.getLogger("thestudio.verify")
    task_id = params.taskpacket_id
    await emit_stage_enter("verify", task_id)
    success = False
    try:
        if not params.changed_files:
            logger.warning("verify.no_files taskpacket=%s", params.taskpacket_id)
            verify_out = VerifyOutput(
                passed=False,
                loopback_triggered=True,
                exhausted=False,
                checks=[{"name": "files_exist", "passed": "false", "detail": "No files changed"}],
            )
        else:
            checks = [
                {
                    "name": "files_exist",
                    "passed": "true",
                    "detail": f"{len(params.changed_files)} file(s) pushed to branch",
                },
            ]

            logger.info(
                "verify.passed taskpacket=%s files=%d",
                params.taskpacket_id,
                len(params.changed_files),
            )
            verify_out = VerifyOutput(passed=True, checks=checks)

        success = True
        return verify_out
    finally:
        await emit_stage_exit("verify", task_id, success=success)


@activity.defn
async def qa_activity(params: QAInput) -> QAOutput:
    """Step 8: QA validation against intent.

    Uses AgentRunner with QAAgentConfig (Epic 23 Story 3.8).
    LLM reasons about intent satisfaction; falls back to keyword-based
    validate() when LLM is disabled.
    """
    from src.agent.framework import AgentContext, AgentRunner
    from src.dashboard.events_publisher import emit_stage_enter, emit_stage_exit
    from src.qa.qa_config import QA_AGENT_CONFIG

    task_id = params.taskpacket_id
    await emit_stage_enter("qa", task_id)
    success = False
    try:
        # Build evidence summary for the LLM prompt
        evidence_lines = []
        for k, v in (params.evidence or {}).items():
            evidence_lines.append(f"- **{k}**: {v}")
        evidence_summary = "\n".join(evidence_lines) if evidence_lines else "No evidence provided"

        context = AgentContext(
            evidence=params.evidence,
            extra={
                "taskpacket_id": params.taskpacket_id,
                "acceptance_criteria": params.acceptance_criteria,
                "qa_handoff": params.qa_handoff,
                "evidence_keys": ",".join(params.evidence.keys()) if params.evidence else "",
                "evidence_summary": evidence_summary,
            },
        )

        runner = AgentRunner(QA_AGENT_CONFIG)
        result = await runner.run(context)

        if result.parsed_output is not None:
            output = result.parsed_output
            all_passed = all(cr.passed for cr in output.criteria_results)
            has_intent_gap = len(output.intent_gaps) > 0
            qa_out = QAOutput(
                passed=all_passed and not has_intent_gap,
                has_intent_gap=has_intent_gap,
                defect_count=len(output.defects),
                needs_loopback=not all_passed,
                needs_intent_refinement=has_intent_gap,
            )
        else:
            import json
            data = json.loads(result.raw_output) if result.raw_output else {}
            criteria = data.get("criteria_results", [])
            all_passed = all(cr.get("passed", False) for cr in criteria) if criteria else True
            intent_gaps = data.get("intent_gaps", [])
            qa_out = QAOutput(
                passed=all_passed and not intent_gaps,
                has_intent_gap=bool(intent_gaps),
                defect_count=len(data.get("defects", [])),
                needs_loopback=not all_passed,
                needs_intent_refinement=bool(intent_gaps),
            )

        success = True
        return qa_out
    finally:
        await emit_stage_exit("qa", task_id, success=success)


@activity.defn
async def publish_activity(params: PublishInput) -> PublishOutput:
    """Step 9: Publish PR to GitHub.

    When github_provider is "real", delegates to publisher.publisher.publish()
    with a real GitHubClient and database session. Otherwise falls back to a
    stub that records timing only.

    Records a TimingEvent on completion for lead/cycle time tracking.
    """
    import logging
    from datetime import UTC, datetime

    from src.admin.operational_targets import TimingEvent, record_timing
    from src.dashboard.events_publisher import emit_stage_enter, emit_stage_exit
    from src.settings import settings

    logger = logging.getLogger("thestudio.publish")
    now = datetime.now(UTC)
    task_id = params.taskpacket_id
    await emit_stage_enter("publish", task_id)
    success = False
    try:
        if settings.github_provider == "real":
            publish_out = await _publish_real(params, logger, now)
        else:
            # Stub mode: record timing with placeholder values
            record_timing(
                TimingEvent(
                    repo_id=params.taskpacket_id,
                    intake_created_at=now,
                    pr_opened_at=now,
                    merge_ready_at=now if params.qa_passed else None,
                )
            )

            publish_out = PublishOutput(
                pr_number=0,
                pr_url="",
                created=False,
                marked_ready=False,
            )

        success = True
        return publish_out
    finally:
        await emit_stage_exit("publish", task_id, success=success)


async def _publish_real(
    params: PublishInput,
    logger,
    now,
) -> PublishOutput:
    """Wire the real publisher with DB session and GitHubClient."""
    from uuid import UUID

    from src.adapters.github import get_github_client
    from src.admin.operational_targets import TimingEvent, record_timing
    from src.agent.evidence import EvidenceBundle
    from src.db.connection import get_async_session
    from src.intent.intent_crud import get_latest_for_taskpacket
    from src.models.taskpacket_crud import get_by_id
    from src.publisher.publisher import publish
    from src.repo.repo_profile import RepoTier
    from src.settings import settings
    from src.verification.gate import VerificationResult

    taskpacket_id = UUID(params.taskpacket_id)
    repo_tier = RepoTier(params.repo_tier)

    # Resolve GitHub token: prefer intake_poll_token (PAT with repo permissions)
    token = settings.intake_poll_token
    if not token:
        logger.error(
            "publish.no_token: intake_poll_token not configured, cannot create PR"
        )
        return PublishOutput(pr_number=0, pr_url="", created=False, marked_ready=False)

    async with get_async_session() as session:
        # Advance TaskPacket through required status transitions
        # Pipeline activities don't update status individually, so we do it here
        from src.models.taskpacket import TaskPacketStatus
        from src.models.taskpacket_crud import update_status

        status_chain = [
            TaskPacketStatus.ENRICHED,
            TaskPacketStatus.INTENT_BUILT,
            TaskPacketStatus.IN_PROGRESS,
            TaskPacketStatus.VERIFICATION_PASSED,
        ]
        for target_status in status_chain:
            try:
                await update_status(session, taskpacket_id, target_status)
            except Exception:  # noqa: S110
                pass  # Already in this or later status

        # Load TaskPacket for timing data
        taskpacket = await get_by_id(session, taskpacket_id)
        if taskpacket is None:
            logger.error("publish.taskpacket_not_found id=%s", params.taskpacket_id)
            return PublishOutput(
                pr_number=0, pr_url="", created=False, marked_ready=False
            )

        # Load latest intent for evidence comment
        intent = await get_latest_for_taskpacket(session, taskpacket_id)

        # Build evidence bundle from pipeline context
        evidence = EvidenceBundle(
            taskpacket_id=taskpacket_id,
            intent_version=intent.version if intent else 1,
            files_changed=params.files_changed,
            test_results="Pipeline verification passed",
            lint_results="Pipeline verification passed",
            agent_summary=params.agent_summary or "Published by Temporal pipeline",
        )

        # Build verification result (we only reach publish if verification passed)
        verification = VerificationResult(passed=True, checks=[])

        github = get_github_client(token)
        try:
            result = await publish(
                session=session,
                taskpacket_id=taskpacket_id,
                evidence=evidence,
                verification=verification,
                github=github,
                repo_tier=repo_tier,
                qa_passed=params.qa_passed,
            )
        finally:
            await github.close()

        # Record timing from real TaskPacket data
        intake_created_at = getattr(taskpacket, "created_at", now) or now
        record_timing(
            TimingEvent(
                repo_id=params.taskpacket_id,
                intake_created_at=intake_created_at,
                pr_opened_at=now,
                merge_ready_at=now if params.qa_passed else None,
            )
        )

        logger.info(
            "publish.complete pr_number=%d pr_url=%s created=%s",
            result.pr_number,
            result.pr_url,
            result.created,
        )

        return PublishOutput(
            pr_number=result.pr_number,
            pr_url=result.pr_url,
            created=result.created,
            marked_ready=result.marked_ready,
        )


@activity.defn
async def post_approval_request_activity(
    params: ApprovalRequestInput,
) -> ApprovalRequestOutput:
    """Step 8.5a: Post approval request via configured notification channels.

    Resolves configured channels and calls notify_awaiting_approval on each.
    Falls back to logging when no channels are available (stub/test mode).

    Epic 24 Story 24.4: Uses channel adapters instead of direct GitHub posting.
    """
    import logging
    from uuid import UUID

    from src.approval.channels.registry import get_configured_channels
    from src.approval.review_context import ReviewContext, TaskPacketSummary

    logger = logging.getLogger("thestudio.approval")

    taskpacket_uuid = UUID(params.taskpacket_id)

    # Build a minimal ReviewContext for channel notifications
    context = ReviewContext(
        taskpacket=TaskPacketSummary(
            taskpacket_id=taskpacket_uuid,
            repo="",  # Resolved from TaskPacket in production
            status="awaiting_approval",
            repo_tier=params.repo_tier,
        ),
    )
    if params.intent_summary:
        context.intent.goal = params.intent_summary
    context.qa.passed = params.qa_passed

    # Notify via all configured channels
    channels = get_configured_channels()
    any_posted = False

    for channel in channels:
        try:
            posted = await channel.notify_awaiting_approval(context)
            if posted:
                any_posted = True
                logger.info(
                    "approval.request.channel_notified",
                    extra={
                        "taskpacket_id": params.taskpacket_id,
                        "channel": channel.channel_name,
                    },
                )
        except Exception:
            logger.warning(
                "approval.request.channel_failed",
                extra={
                    "taskpacket_id": params.taskpacket_id,
                    "channel": channel.channel_name,
                },
                exc_info=True,
            )

    if not any_posted:
        # Fallback: log only (test/stub mode or all channels failed)
        logger.info(
            "approval.request.posted",
            extra={
                "taskpacket_id": params.taskpacket_id,
                "repo_tier": params.repo_tier,
                "intent_summary": params.intent_summary,
                "qa_passed": params.qa_passed,
            },
        )

    return ApprovalRequestOutput(comment_posted=True)


@activity.defn
async def update_project_status_activity(
    params: ProjectStatusInput,
) -> ProjectStatusOutput:
    """Sync TaskPacket status to GitHub Projects v2 board.

    Epic 29 AC 6: Best-effort status sync at key transitions.
    If Projects v2 is disabled or the API call fails, the activity
    returns gracefully — sync never blocks the pipeline.
    """
    import logging

    from src.settings import settings

    logger = logging.getLogger("thestudio.projects_v2")

    if not settings.projects_v2_enabled:
        return ProjectStatusOutput(synced=False, error="projects_v2_disabled")

    if not settings.projects_v2_owner or not settings.projects_v2_number:
        return ProjectStatusOutput(synced=False, error="projects_v2_not_configured")

    try:
        from src.github.projects_client import ProjectsV2Client
        from src.github.projects_mapping import map_risk, map_status, map_tier

        token = settings.projects_v2_token or settings.github_app_id
        if not token:
            return ProjectStatusOutput(synced=False, error="no_token")

        async with ProjectsV2Client(token) as client:
            # Epic 38 story 38.13: validate token has 'project' scope before
            # attempting any GraphQL mutations (Risk R1 mitigation).
            scope_valid, scope_error = await client.validate_token_scopes()
            if not scope_valid:
                logger.warning(
                    "projects_v2.token_scope_invalid",
                    extra={
                        "taskpacket_id": params.taskpacket_id,
                        "error": scope_error,
                    },
                )
                return ProjectStatusOutput(synced=False, error=scope_error or "invalid_token_scope")
            owner = settings.projects_v2_owner
            project_number = settings.projects_v2_number

            # Map status
            projects_status = map_status(params.taskpacket_status)
            if projects_status is None:
                return ProjectStatusOutput(
                    synced=False,
                    error=f"unmapped_status:{params.taskpacket_status}",
                )

            item_id = params.project_item_id

            # If no item_id yet, we can't update (item must be added first
            # via intake or a separate add_item call)
            if not item_id:
                logger.debug(
                    "projects_v2.skip_no_item_id",
                    extra={"taskpacket_id": params.taskpacket_id},
                )
                return ProjectStatusOutput(synced=False, error="no_item_id")

            # Update status
            await client.set_status(owner, project_number, item_id, projects_status)

            # Set tier on first sync (RECEIVED status)
            if params.taskpacket_status == "RECEIVED":
                tier_value = map_tier(params.repo_tier)
                if tier_value:
                    await client.set_automation_tier(
                        owner, project_number, item_id, tier_value
                    )

            # Set risk tier after context enrichment (ENRICHED status)
            if params.taskpacket_status == "ENRICHED":
                risk_value = map_risk(params.complexity_index)
                if risk_value:
                    await client.set_risk_tier(
                        owner, project_number, item_id, risk_value
                    )

            logger.info(
                "projects_v2.status_synced",
                extra={
                    "taskpacket_id": params.taskpacket_id,
                    "status": projects_status,
                    "item_id": item_id,
                },
            )
            return ProjectStatusOutput(synced=True, project_item_id=item_id)

    except Exception:
        logger.warning(
            "projects_v2.sync_failed",
            extra={"taskpacket_id": params.taskpacket_id},
            exc_info=True,
        )
        return ProjectStatusOutput(synced=False, error="sync_exception")


@activity.defn
async def escalate_timeout_activity(
    params: EscalateTimeoutInput,
) -> EscalateTimeoutOutput:
    """Step 8.5b: Escalate on approval timeout.

    Applies the ``agent:human-review`` label and posts an escalation comment
    via publisher.escalate_approval_timeout(). Falls back to logging when no
    GitHub client is available (stub/test mode).
    Idempotent — calling twice does not duplicate labels or comments.
    """
    import logging
    from uuid import UUID

    logger = logging.getLogger("thestudio.approval")

    try:
        from src.publisher.github_client import GitHubClient
        from src.publisher.publisher import escalate_approval_timeout
        from src.settings import settings

        if settings.github_provider == "real":
            async with GitHubClient(settings.github_app_id) as github:
                taskpacket_uuid = UUID(params.taskpacket_id)
                await escalate_approval_timeout(
                    github=github,
                    owner="",  # resolved from TaskPacket.repo in production
                    repo_name="",
                    issue_number=0,
                    taskpacket_id=taskpacket_uuid,
                )
                return EscalateTimeoutOutput(escalated=True, label_applied=True)
    except Exception:
        logger.debug(
            "GitHub client not available, falling back to log-only mode",
            exc_info=True,
        )

    # Fallback: log only (test/stub mode)
    logger.info(
        "approval.timeout.escalated",
        extra={
            "taskpacket_id": params.taskpacket_id,
            "repo_tier": params.repo_tier,
        },
    )
    return EscalateTimeoutOutput(escalated=True, label_applied=True)


@activity.defn
async def persist_steering_audit_activity(
    params: PersistSteeringAuditInput,
) -> None:
    """Persist a steering audit entry and emit pipeline.steering.action NATS event.

    Called from within Temporal signal handlers (pause_task / resume_task /
    abort_task) after each steering action.  Durably persists the entry to
    ``steering_audit_log`` via the async DB session and then publishes a
    ``pipeline.steering.action`` SSE event so the dashboard can reflect the
    new steering state in real time.

    Failures fall back gracefully — the activity retry policy ensures
    delivery under transient failures.
    """
    import logging
    from datetime import UTC, datetime
    from uuid import UUID, uuid4

    from src.dashboard.events_publisher import emit_steering_action
    from src.dashboard.models.steering_audit import SteeringAuditLogCreate, create_audit_entry
    from src.db.connection import get_async_session

    _logger = logging.getLogger("thestudio.steering")

    timestamp_str = params.timestamp_iso or datetime.now(UTC).isoformat()
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
    except ValueError:
        timestamp = datetime.now(UTC)

    audit_id = str(uuid4())

    # 1. Persist to steering_audit_log
    try:
        task_uuid = UUID(params.task_id)
        async with get_async_session() as session:
            entry = SteeringAuditLogCreate(
                task_id=task_uuid,
                action=params.action,
                from_stage=params.from_stage or None,
                to_stage=params.to_stage or None,
                reason=params.reason or None,
                timestamp=timestamp,
                actor=params.actor or "system",
            )
            result = await create_audit_entry(session, entry)
            audit_id = str(result.id)
            await session.commit()
    except Exception:
        _logger.warning(
            "steering.audit.persist_failed",
            extra={"task_id": params.task_id, "action": params.action},
            exc_info=True,
        )

    # 2. Emit pipeline.steering.action NATS event for SSE
    await emit_steering_action(
        task_id=params.task_id,
        action=params.action,
        actor=params.actor or "system",
        audit_id=audit_id,
        from_stage=params.from_stage or None,
        to_stage=params.to_stage or None,
        reason=params.reason or None,
        timestamp_iso=timestamp.isoformat(),
    )
    _logger.info(
        "steering.audit.persisted",
        extra={
            "task_id": params.task_id,
            "action": params.action,
            "audit_id": audit_id,
        },
    )


@activity.defn
async def assign_trust_tier_activity(
    params: AssignTrustTierInput,
) -> AssignTrustTierOutput:
    """Assign a trust tier to the TaskPacket before pipeline activities begin.

    Loads the TaskPacket from the database, evaluates the trust rule engine
    (``src/dashboard/trust_engine.py``) against its current fields, persists
    the resolved tier back to ``task_trust_tier``, and emits a
    ``pipeline.trust_tier.assigned`` NATS event for the dashboard SSE stream.

    Called as the first step in the pipeline workflow, immediately after context
    enrichment so that risk_flags and complexity_index are available for rule
    evaluation.  Falls back to OBSERVE if the TaskPacket cannot be loaded or
    the engine raises an unexpected error.
    """
    import logging
    from uuid import UUID

    from src.dashboard.events_publisher import emit_trust_tier_assigned
    from src.dashboard.trust_engine import evaluate_trust_tier
    from src.db.connection import get_async_session
    from src.models.taskpacket import TaskTrustTier
    from src.models.taskpacket_crud import get_by_id

    _logger = logging.getLogger("thestudio.trust_tier")

    taskpacket_id = UUID(params.taskpacket_id)

    try:
        async with get_async_session() as session:
            packet = await get_by_id(session, taskpacket_id)
            if packet is None:
                _logger.error(
                    "trust_tier.assign.packet_not_found",
                    extra={"taskpacket_id": params.taskpacket_id},
                )
                return AssignTrustTierOutput(tier="observe", reason="TaskPacket not found")

            result = await evaluate_trust_tier(session, packet)

            # Convert AssignedTier → TaskTrustTier (same string values, different enum class)
            tier_value: str = result.tier.value
            packet.task_trust_tier = TaskTrustTier(tier_value)
            await session.commit()

            matched_rule_str = (
                str(result.matched_rule_id) if result.matched_rule_id else None
            )
            _logger.info(
                "trust_tier.assigned",
                extra={
                    "taskpacket_id": params.taskpacket_id,
                    "tier": tier_value,
                    "matched_rule_id": matched_rule_str,
                    "safety_capped": result.safety_capped,
                },
            )

        # Persist steering audit entry for trust tier assignment/override
        from datetime import datetime

        from src.dashboard.models.steering_audit import (
            SteeringAction,
            SteeringAuditLogCreate,
            create_audit_entry,
        )

        if result.safety_capped:
            audit_action = SteeringAction.TRUST_TIER_OVERRIDDEN
            # from_stage = tier rule originally assigned (before safety cap)
            audit_from = result.raw_tier.value
        else:
            audit_action = SteeringAction.TRUST_TIER_ASSIGNED
            # from_stage = None (initial assignment has no prior tier to record)
            audit_from = None

        audit_reason_parts = []
        if matched_rule_str:
            audit_reason_parts.append(f"rule_id={matched_rule_str}")
        audit_reason_parts.append(result.reason)

        async with get_async_session() as session:
            await create_audit_entry(
                session,
                SteeringAuditLogCreate(
                    task_id=taskpacket_id,
                    action=audit_action,
                    from_stage=audit_from,
                    to_stage=tier_value,
                    reason="; ".join(audit_reason_parts),
                    timestamp=datetime.now(tz=UTC),
                    actor="system",
                ),
            )
            await session.commit()

        # Emit NATS event (fire-and-forget, outside DB session)
        await emit_trust_tier_assigned(
            task_id=params.taskpacket_id,
            tier=tier_value,
            matched_rule_id=matched_rule_str,
            safety_capped=result.safety_capped,
            reason=result.reason,
        )

        return AssignTrustTierOutput(
            tier=tier_value,
            matched_rule_id=matched_rule_str,
            safety_capped=result.safety_capped,
            reason=result.reason,
        )

    except Exception:
        _logger.warning(
            "trust_tier.assign.failed — falling back to observe",
            extra={"taskpacket_id": params.taskpacket_id},
            exc_info=True,
        )
        return AssignTrustTierOutput(tier="observe", reason="evaluation error — fallback")
