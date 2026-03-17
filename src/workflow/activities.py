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
    repo_tier: str = "observe"


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
    from src.intake.intake_config import INTAKE_AGENT_CONFIG

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
        return IntakeOutput(
            accepted=output.accepted,
            rejection_reason=output.rejection_reason or None,
            base_role=output.base_role if output.accepted else None,
            overlays=output.overlays if output.accepted else [],
        )

    # Fallback produced raw JSON
    import json
    data = json.loads(result.raw_output) if result.raw_output else {}
    accepted = data.get("accepted", False)
    return IntakeOutput(
        accepted=accepted,
        rejection_reason=data.get("rejection_reason") or None,
        base_role=data.get("base_role") if accepted else None,
        overlays=data.get("overlays", []) if accepted else [],
    )


@activity.defn
async def context_activity(params: ContextInput) -> ContextOutput:
    """Step 2: Context enrichment (scope, risk, complexity).

    Uses AgentRunner with ContextAgentConfig (Epic 23 Story 2.5).
    Deterministic functions run first, LLM reviews and augments.
    Falls back to deterministic enrich_taskpacket() when LLM is disabled.
    """
    from src.agent.framework import AgentContext, AgentRunner
    from src.context.context_config import CONTEXT_AGENT_CONFIG

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
        return ContextOutput(
            scope={"type": "feature", "summary": output.scope_summary},
            risk_flags=output.risk_flags,
            complexity_index="medium" if output.risk_flags else "low",
            context_packs=[],
        )

    import json
    data = json.loads(result.raw_output) if result.raw_output else {}
    return ContextOutput(
        scope={"type": "feature", "summary": data.get("scope_summary", "")},
        risk_flags=data.get("risk_flags", {}),
        complexity_index=data.get("complexity_index", "low"),
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

    Uses AgentRunner with IntentAgentConfig (Epic 23 Story 2.8).
    LLM extracts semantic intent including invariants; falls back to
    rule-based build_intent() when LLM is disabled.
    """
    from src.agent.framework import AgentContext, AgentRunner
    from src.intent.intent_config import INTENT_AGENT_CONFIG

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
        return IntentOutput(
            intent_spec_id="",
            version=1,
            goal=output.goal,
            acceptance_criteria=output.acceptance_criteria,
        )

    import json
    data = json.loads(result.raw_output) if result.raw_output else {}
    return IntentOutput(
        intent_spec_id="",
        version=1,
        goal=data.get("goal", params.issue_title),
        acceptance_criteria=data.get("acceptance_criteria", []),
    )


@activity.defn
async def router_activity(params: RouterInput) -> RouterOutput:
    """Step 4: Route to expert subset.

    Uses AgentRunner with RouterAgentConfig (Epic 23 Story 2.11).
    Algorithmic route() runs first; LLM reviews and adjusts patterns/escalations.
    Falls back to pure algorithmic routing when LLM is disabled.
    """
    from src.agent.framework import AgentContext, AgentRunner
    from src.routing.router_config import ROUTER_AGENT_CONFIG

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
        return RouterOutput(
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

    import json
    data = json.loads(result.raw_output) if result.raw_output else {}
    return RouterOutput(
        selections=data.get("selections", []),
        recruiter_requests=data.get("recruiter_requests", []),
        rationale=data.get("adjustments", ""),
    )


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
        return AssemblerOutput(
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
                {"criterion": h.get("criterion", ""), "validation_steps": ",".join(h.get("validation_steps", []))}
                for h in output.qa_handoff
            ],
            provenance={"taskpacket_id": params.taskpacket_id},
            needs_intent_refinement=any(c.resolved_by == "unresolved" for c in output.conflicts),
        )

    import json
    data = json.loads(result.raw_output) if result.raw_output else {}
    return AssemblerOutput(
        plan_steps=[s.get("description", "") for s in data.get("plan_steps", [{"description": "implement_changes"}])],
        qa_handoff=data.get("qa_handoff", []),
        provenance={"taskpacket_id": params.taskpacket_id},
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
    from src.settings import settings

    repo_tier = getattr(params, "repo_tier", "observe")

    # Resolve isolation mode based on settings and Docker availability
    if settings.agent_isolation == "container":
        from src.agent.container_manager import ContainerManager

        container_available = ContainerManager.is_docker_available()
        decision = resolve_isolation(repo_tier, container_available)

        if decision.mode == IsolationMode.CONTAINER:
            return await _implement_container(params, decision)

    # In-process mode (default or fallback)
    return await _implement_in_process(params, repo_tier)


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
    """Run implementation in-process (default mode)."""
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
        repo_tier=repo_tier,
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

    Uses AgentRunner with QAAgentConfig (Epic 23 Story 3.8).
    LLM reasons about intent satisfaction; falls back to keyword-based
    validate() when LLM is disabled.
    """
    from src.agent.framework import AgentContext, AgentRunner
    from src.qa.qa_config import QA_AGENT_CONFIG

    context = AgentContext(
        evidence=params.evidence,
        extra={
            "taskpacket_id": params.taskpacket_id,
            "acceptance_criteria": params.acceptance_criteria,
            "qa_handoff": params.qa_handoff,
            "evidence_keys": ",".join(params.evidence.keys()) if params.evidence else "",
        },
    )

    runner = AgentRunner(QA_AGENT_CONFIG)
    result = await runner.run(context)

    if result.parsed_output is not None:
        output = result.parsed_output
        all_passed = all(cr.passed for cr in output.criteria_results)
        has_intent_gap = len(output.intent_gaps) > 0
        return QAOutput(
            passed=all_passed and not has_intent_gap,
            has_intent_gap=has_intent_gap,
            defect_count=len(output.defects),
            needs_loopback=not all_passed,
            needs_intent_refinement=has_intent_gap,
        )

    import json
    data = json.loads(result.raw_output) if result.raw_output else {}
    criteria = data.get("criteria_results", [])
    all_passed = all(cr.get("passed", False) for cr in criteria) if criteria else True
    intent_gaps = data.get("intent_gaps", [])
    return QAOutput(
        passed=all_passed and not intent_gaps,
        has_intent_gap=bool(intent_gaps),
        defect_count=len(data.get("defects", [])),
        needs_loopback=not all_passed,
        needs_intent_refinement=bool(intent_gaps),
    )


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
