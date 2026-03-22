"""TheStudio Pipeline Workflow — Temporal workflow definition.

Wires the full 9-step runtime flow from GitHub issue to ready-for-review PR,
with a durable human approval wait state between QA and Publish for
Suggest/Execute tier repos.

Architecture reference: thestudioarc/15-system-runtime-flow.md

Steps:
1. Intake Agent — eligibility, role selection
2. Context Manager — scope, risk, complexity
2.5. Readiness Gate — score issue, hold/escalate/pass (feature-flagged)
3. Intent Builder — goal, constraints, acceptance criteria
4. Expert Router — select expert subset
4.5. Routing Review — human review of expert selection (feature-flagged)
5. Assembler — merge expert outputs into plan
5.5. Preflight — plan quality gate (feature-flagged, Epic 28)
6. Primary Agent — implement changes
7. Verification Gate — run checks, loopback on failure
8. QA Agent — validate against intent, loopback on failure
8.5. Approval Wait — durable pause for human approval (Suggest/Execute tier)
9. Publisher — create PR with evidence

Retry/timeout policy per the architecture table in 15-system-runtime-flow.md.
"""

from dataclasses import dataclass, field, replace
from datetime import timedelta
from enum import StrEnum

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from src.workflow.activities import (
        ApprovalRequestInput,
        AssemblerInput,
        AssemblerOutput,
        ContextInput,
        ContextOutput,
        EscalateTimeoutInput,
        ImplementInput,
        ImplementOutput,
        IntakeInput,
        IntakeOutput,
        IntentInput,
        IntentOutput,
        PersistSteeringAuditInput,
        PreflightActivityOutput,
        PreflightInput,
        ProjectStatusInput,
        PublishInput,
        PublishOutput,
        QAInput,
        QAOutput,
        ReadinessActivityOutput,
        ReadinessInput,
        RouterInput,
        VerifyInput,
        VerifyOutput,
        assembler_activity,
        context_activity,
        escalate_timeout_activity,
        implement_activity,
        intake_activity,
        intent_activity,
        persist_steering_audit_activity,
        post_approval_request_activity,
        preflight_activity,
        publish_activity,
        qa_activity,
        readiness_activity,
        router_activity,
        update_project_status_activity,
        verify_activity,
    )

# Tiers that require human approval before publish
APPROVAL_REQUIRED_TIERS = frozenset({"suggest", "execute"})

# Durable wait timeout — hard policy, not configurable
APPROVAL_TIMEOUT = timedelta(days=7)

# Intent review safety timeout — 30 days, escalates (does NOT auto-approve)
INTENT_REVIEW_TIMEOUT = timedelta(days=30)

# Routing review safety timeout — 30 days, escalates (does NOT auto-approve)
ROUTING_REVIEW_TIMEOUT = timedelta(days=30)

# Readiness re-evaluation wait timeout
READINESS_REEVALUATION_TIMEOUT = timedelta(days=7)

# Maximum re-evaluations before escalating to human review
MAX_READINESS_EVALUATIONS = 3


class WorkflowStep(StrEnum):
    """Named steps for observability and debugging."""

    INTAKE = "intake"
    CONTEXT = "context"
    READINESS = "readiness"
    INTENT = "intent"
    ROUTER = "router"
    ASSEMBLER = "assembler"
    PREFLIGHT = "preflight"
    IMPLEMENT = "implement"
    VERIFY = "verify"
    QA = "qa"
    AWAITING_INTENT_REVIEW = "awaiting_intent_review"
    AWAITING_ROUTING_REVIEW = "awaiting_routing_review"
    AWAITING_APPROVAL = "awaiting_approval"
    PUBLISH = "publish"
    PROJECTS_V2_SYNC = "projects_v2_sync"


# Ordered pipeline stage sequence for redirect validation.
# A redirect is only valid when target_stage < current_stage.
STAGE_ORDER: dict[str, int] = {
    WorkflowStep.INTAKE: 1,
    WorkflowStep.CONTEXT: 2,
    WorkflowStep.READINESS: 3,
    WorkflowStep.INTENT: 4,
    WorkflowStep.AWAITING_INTENT_REVIEW: 5,
    WorkflowStep.ROUTER: 6,
    WorkflowStep.AWAITING_ROUTING_REVIEW: 7,
    WorkflowStep.ASSEMBLER: 8,
    WorkflowStep.PREFLIGHT: 9,
    WorkflowStep.IMPLEMENT: 10,
    WorkflowStep.VERIFY: 11,
    WorkflowStep.QA: 12,
    WorkflowStep.AWAITING_APPROVAL: 13,
    WorkflowStep.PUBLISH: 14,
}


# --- Retry/Timeout Policy Table ---
# Per thestudioarc/15-system-runtime-flow.md


@dataclass(frozen=True)
class StepPolicy:
    """Timeout, retry, and backoff configuration for a workflow step."""

    timeout: timedelta
    max_retries: int
    initial_interval: timedelta = timedelta(seconds=1)
    backoff_coefficient: float = 2.0

    def to_retry_policy(self) -> RetryPolicy:
        return RetryPolicy(
            maximum_attempts=self.max_retries + 1,  # Temporal counts total attempts
            initial_interval=self.initial_interval,
            backoff_coefficient=self.backoff_coefficient,
        )


# Policy table from 15-system-runtime-flow.md
STEP_POLICIES: dict[WorkflowStep, StepPolicy] = {
    WorkflowStep.INTAKE: StepPolicy(
        timeout=timedelta(minutes=2), max_retries=2,
    ),
    WorkflowStep.CONTEXT: StepPolicy(
        timeout=timedelta(minutes=10), max_retries=3,
    ),
    WorkflowStep.READINESS: StepPolicy(
        timeout=timedelta(minutes=2), max_retries=2,
    ),
    WorkflowStep.INTENT: StepPolicy(
        timeout=timedelta(minutes=10), max_retries=2,
    ),
    WorkflowStep.ROUTER: StepPolicy(
        timeout=timedelta(minutes=15), max_retries=2,
    ),
    WorkflowStep.ASSEMBLER: StepPolicy(
        timeout=timedelta(minutes=10), max_retries=2,
    ),
    WorkflowStep.PREFLIGHT: StepPolicy(
        timeout=timedelta(minutes=2), max_retries=1,
        backoff_coefficient=2.0,
    ),
    WorkflowStep.IMPLEMENT: StepPolicy(
        timeout=timedelta(minutes=60), max_retries=2,
    ),
    WorkflowStep.VERIFY: StepPolicy(
        timeout=timedelta(minutes=45), max_retries=3,
        backoff_coefficient=1.5,  # bounded backoff for flake policy
    ),
    WorkflowStep.QA: StepPolicy(
        timeout=timedelta(minutes=30), max_retries=2,
    ),
    WorkflowStep.AWAITING_INTENT_REVIEW: StepPolicy(
        timeout=timedelta(days=30), max_retries=0,  # safety timeout, not auto-approve
    ),
    WorkflowStep.AWAITING_ROUTING_REVIEW: StepPolicy(
        timeout=timedelta(days=30), max_retries=0,  # safety timeout, not auto-approve
    ),
    WorkflowStep.AWAITING_APPROVAL: StepPolicy(
        timeout=timedelta(days=7), max_retries=0,  # managed by workflow.wait_condition
    ),
    WorkflowStep.PUBLISH: StepPolicy(
        timeout=timedelta(minutes=5), max_retries=5,
        initial_interval=timedelta(seconds=0.5),  # fast retry
        backoff_coefficient=1.5,
    ),
    WorkflowStep.PROJECTS_V2_SYNC: StepPolicy(
        timeout=timedelta(seconds=30), max_retries=2,
        backoff_coefficient=1.5,
    ),
}

# Loopback caps
MAX_VERIFICATION_LOOPBACKS = 2
MAX_QA_LOOPBACKS = 2

# Audit activity policy — fast write, 3 attempts total (2 retries)
_STEERING_AUDIT_POLICY = StepPolicy(
    timeout=timedelta(seconds=30),
    max_retries=2,
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
)


@dataclass
class PipelineInput:
    """Input for the TheStudio pipeline workflow."""

    taskpacket_id: str
    correlation_id: str
    labels: list[str] = field(default_factory=list)
    repo: str = ""
    repo_registered: bool = True
    repo_paused: bool = False
    has_active_workflow: bool = False
    event_id: str = ""
    issue_title: str = ""
    issue_body: str = ""
    repo_path: str = ""
    repo_tier: str = "observe"
    readiness_gate_enabled: bool = False
    preflight_enabled: bool = False
    preflight_tiers: list[str] = field(default_factory=lambda: ["execute"])
    projects_v2_enabled: bool = False
    project_item_id: str = ""  # Populated after item is added to project
    approval_auto_bypass: bool = False
    intent_review_enabled: bool = False
    routing_review_enabled: bool = False
    # Set by redirect_task continue_as_new to indicate which stage to start from.
    # Stages before start_from_stage are still executed (activities are idempotent
    # and will fast-path based on existing TaskPacket state).
    start_from_stage: str = ""


@dataclass
class PipelineOutput:
    """Output of the TheStudio pipeline workflow."""

    success: bool = False
    step_reached: str = ""
    rejection_reason: str | None = None
    pr_number: int = 0
    pr_url: str = ""
    marked_ready: bool = False
    verification_loopbacks: int = 0
    qa_loopbacks: int = 0
    awaiting_approval: bool = False
    approved_by: str | None = None
    approval_bypassed: bool = False
    readiness_evaluations: int = 0
    readiness_escalated: bool = False
    preflight_approved: bool | None = None
    preflight_summary: str = ""
    intent_approved_by: str | None = None
    routing_approved_by: str | None = None


@workflow.defn
class TheStudioPipelineWorkflow:
    """Full pipeline from GitHub issue to ready-for-review PR.

    Handles loopbacks for verification (max 2) and QA (max 2).
    Gates fail closed — exhaustion results in workflow failure.

    For Suggest/Execute tier repos, a durable approval wait state is inserted
    between QA pass and Publish. The workflow pauses for up to 7 days waiting
    for an ``approve_publish`` signal. On timeout, the task is escalated and
    the workflow returns failure.

    When the readiness gate holds an issue, the workflow waits for a
    ``readiness_cleared`` signal. On signal, it re-evaluates. After 3 failed
    re-evaluations, the issue is escalated to human review.
    """

    def __init__(self) -> None:
        self._approved = False
        self._approved_by: str | None = None
        self._approval_source: str | None = None
        self._rejected = False
        self._rejected_by: str | None = None
        self._rejection_reason: str | None = None
        # Readiness re-evaluation state
        self._readiness_cleared = False
        self._updated_issue_title: str = ""
        self._updated_issue_body: str = ""
        # Intent review state
        self._intent_approved = False
        self._intent_approved_by: str | None = None
        self._intent_rejected = False
        self._intent_rejected_by: str | None = None
        self._intent_rejection_reason: str | None = None
        # Routing review state
        self._routing_approved = False
        self._routing_approved_by: str | None = None
        self._routing_rejected = False
        self._routing_rejected_by: str | None = None
        self._routing_rejection_reason: str | None = None
        # Steering state — pause/resume/abort (Slice 1, Epic 37)
        self._paused = False
        self._aborted = False
        self._abort_reason: str = ""
        # Redirect state — redirect/retry (Slice 2, Epic 37)
        self._redirect_target: str | None = None
        self._redirect_reason: str = ""
        # Tracks the last completed workflow step for steering audit from_stage
        self._current_step: str = ""
        # Cached workflow params — set at start of run() for use in signal handlers
        self._params: PipelineInput | None = None

    @workflow.signal
    async def approve_publish(self, approved_by: str, approval_source: str) -> None:
        """Signal handler — sets approval flag and records approver.

        Idempotent: calling twice is harmless (flag stays True).
        """
        self._approved = True
        self._approved_by = approved_by
        self._approval_source = approval_source

    @workflow.signal
    async def reject_publish(self, rejected_by: str, reason: str) -> None:
        """Signal handler — sets rejection flag and records reason.

        Idempotent: calling twice is harmless (flag stays True).
        """
        self._rejected = True
        self._rejected_by = rejected_by
        self._rejection_reason = reason

    @workflow.signal
    async def approve_intent(self, approved_by: str) -> None:
        """Signal handler — developer approves the intent spec.

        Idempotent: calling twice is harmless (flag stays True).
        """
        self._intent_approved = True
        self._intent_approved_by = approved_by

    @workflow.signal
    async def reject_intent(self, rejected_by: str, reason: str) -> None:
        """Signal handler — developer rejects the intent spec.

        Idempotent: calling twice is harmless (flag stays True).
        """
        self._intent_rejected = True
        self._intent_rejected_by = rejected_by
        self._intent_rejection_reason = reason

    @workflow.signal
    async def approve_routing(self, approved_by: str) -> None:
        """Signal handler — developer approves the expert routing selection.

        Idempotent: calling twice is harmless (flag stays True).
        """
        self._routing_approved = True
        self._routing_approved_by = approved_by

    @workflow.signal
    async def override_routing(self, rejected_by: str, reason: str) -> None:
        """Signal handler — developer overrides/rejects the expert routing selection.

        Idempotent: calling twice is harmless (flag stays True).
        """
        self._routing_rejected = True
        self._routing_rejected_by = rejected_by
        self._routing_rejection_reason = reason

    @workflow.signal
    async def readiness_cleared(self, issue_title: str = "", issue_body: str = "") -> None:
        """Signal handler — submitter updated the issue, re-evaluate readiness.

        Stores the latest issue content for re-scoring. Multiple signals
        before re-evaluation runs are fine — only the latest state matters.
        """
        self._readiness_cleared = True
        self._updated_issue_title = issue_title
        self._updated_issue_body = issue_body

    @workflow.signal
    async def pause_task(self, actor: str = "system", taskpacket_id: str = "") -> None:
        """Signal handler — pauses pipeline execution after current activity completes.

        The pause takes effect at the next inter-activity checkpoint; any
        in-flight activity is allowed to finish before the workflow holds.
        Idempotent: calling twice is harmless (flag stays True).

        Schedules ``persist_steering_audit_activity`` to durably record this
        action and emit ``pipeline.steering.action`` to NATS for SSE.
        """
        self._paused = True
        workflow.logger.info("pipeline.steering.paused")
        await workflow.execute_activity(
            persist_steering_audit_activity,
            PersistSteeringAuditInput(
                task_id=taskpacket_id,
                action="pause",
                actor=actor,
                from_stage=self._current_step,
                to_stage="paused",
            ),
            start_to_close_timeout=_STEERING_AUDIT_POLICY.timeout,
            retry_policy=_STEERING_AUDIT_POLICY.to_retry_policy(),
        )

    @workflow.signal
    async def resume_task(self, actor: str = "system", taskpacket_id: str = "") -> None:
        """Signal handler — resumes pipeline execution after a pause.

        Idempotent: calling twice is harmless (flag stays False).

        Schedules ``persist_steering_audit_activity`` to durably record this
        action and emit ``pipeline.steering.action`` to NATS for SSE.
        """
        self._paused = False
        workflow.logger.info("pipeline.steering.resumed")
        await workflow.execute_activity(
            persist_steering_audit_activity,
            PersistSteeringAuditInput(
                task_id=taskpacket_id,
                action="resume",
                actor=actor,
                from_stage="paused",
                to_stage=self._current_step,
            ),
            start_to_close_timeout=_STEERING_AUDIT_POLICY.timeout,
            retry_policy=_STEERING_AUDIT_POLICY.to_retry_policy(),
        )

    @workflow.signal
    async def abort_task(self, reason: str, actor: str = "system", taskpacket_id: str = "") -> None:
        """Signal handler — aborts pipeline execution with a user-provided reason.

        Sets the abort flag and clears any pause hold so the workflow can
        observe the abort at the next inter-activity checkpoint and return
        immediately. Stores the reason on workflow state for inclusion in
        PipelineOutput.rejection_reason.

        Idempotent: subsequent calls update the reason but do not change
        terminal behaviour.
        """
        self._aborted = True
        self._abort_reason = reason
        # Unblock any active pause hold so the abort is observed immediately.
        self._paused = False
        workflow.logger.info("pipeline.steering.aborted", extra={"reason": reason})
        await workflow.execute_activity(
            persist_steering_audit_activity,
            PersistSteeringAuditInput(
                task_id=taskpacket_id,
                action="abort",
                actor=actor,
                from_stage=self._current_step,
                to_stage="aborted",
                reason=reason,
            ),
            start_to_close_timeout=_STEERING_AUDIT_POLICY.timeout,
            retry_policy=_STEERING_AUDIT_POLICY.to_retry_policy(),
        )

    @workflow.signal
    async def redirect_task(
        self,
        target_stage: str,
        reason: str,
        actor: str = "system",
        taskpacket_id: str = "",
    ) -> None:
        """Signal handler — redirect the pipeline to re-enter at target_stage.

        The redirect takes effect at the next inter-activity checkpoint; any
        in-flight activity completes before the redirect is applied.

        Validates that:
        - ``target_stage`` is a known pipeline stage (in STAGE_ORDER).
        - ``target_stage`` is earlier than the current stage (cannot redirect
          forward — use ``retry_stage`` to re-run the current stage).

        When the redirect is observed, the workflow calls
        ``workflow.continue_as_new`` with ``start_from_stage=target_stage`` so
        the pipeline re-enters from that point. Activities are idempotent and
        will fast-path on existing TaskPacket state for stages before the target.

        Idempotent: subsequent calls before the redirect is applied will update
        the target stage to the latest value.
        """
        # Validate that the target stage is a known pipeline step.
        if target_stage not in STAGE_ORDER:
            workflow.logger.warning(
                "pipeline.steering.redirect_unknown_stage",
                extra={"target_stage": target_stage, "current_step": self._current_step},
            )
            return

        # Validate that target < current (redirect must go backward in the pipeline).
        target_order = STAGE_ORDER[target_stage]
        current_order = STAGE_ORDER.get(self._current_step, 999)
        if target_order >= current_order:
            workflow.logger.warning(
                "pipeline.steering.redirect_invalid_direction",
                extra={
                    "target_stage": target_stage,
                    "target_order": target_order,
                    "current_step": self._current_step,
                    "current_order": current_order,
                },
            )
            return

        self._redirect_target = target_stage
        self._redirect_reason = reason
        # Unblock any active pause hold so the redirect is observed immediately.
        self._paused = False
        workflow.logger.info(
            "pipeline.steering.redirect_set",
            extra={"target_stage": target_stage, "from_stage": self._current_step, "reason": reason},
        )
        await workflow.execute_activity(
            persist_steering_audit_activity,
            PersistSteeringAuditInput(
                task_id=taskpacket_id,
                action="redirect",
                actor=actor,
                from_stage=self._current_step,
                to_stage=target_stage,
                reason=reason,
            ),
            start_to_close_timeout=_STEERING_AUDIT_POLICY.timeout,
            retry_policy=_STEERING_AUDIT_POLICY.to_retry_policy(),
        )

    async def _await_if_paused(self, upcoming_step: str = "") -> bool:
        """Block at the next inter-activity checkpoint if a pause is requested.

        Called before each pipeline activity. If ``self._paused`` is True the
        workflow holds at this point until a ``resume_task``, ``abort_task``,
        or ``redirect_task`` signal is received. Because this check happens
        between activities, any in-flight work completes before the hold takes
        effect.

        ``upcoming_step`` is recorded on ``self._current_step`` so that
        steering signal handlers (pause / resume / abort / redirect) can include
        the current pipeline stage in the audit log entry.

        If a redirect is pending (``_redirect_target`` is set), this method
        calls ``workflow.continue_as_new`` to restart the workflow at the target
        stage. The ``ContinueAsNewError`` propagates up to the Temporal runtime
        automatically — callers do not need to handle it.

        Returns:
            True if an abort was requested (caller should return immediately),
            False if the workflow should continue normally.
            Note: if redirect is active this method never returns — it raises
            ``ContinueAsNewError`` instead.
        """
        if upcoming_step:
            self._current_step = upcoming_step
        if self._paused:
            workflow.logger.info("pipeline.steering.hold_start")
            await workflow.wait_condition(
                lambda: not self._paused or self._aborted or self._redirect_target is not None
            )
            workflow.logger.info("pipeline.steering.hold_end")
        # Apply pending redirect via continue_as_new (raises ContinueAsNewError).
        if self._redirect_target is not None and self._params is not None:
            target = self._redirect_target
            workflow.logger.info(
                "pipeline.steering.redirect_applying",
                extra={"target_stage": target, "reason": self._redirect_reason},
            )
            workflow.continue_as_new(replace(self._params, start_from_stage=target))
            # ContinueAsNewError is raised above — the line below is unreachable
            # but satisfies type checkers that expect a return.
        return self._aborted

    async def _sync_project_status(
        self,
        params: PipelineInput,
        status: str,
        complexity_index: str = "low",
    ) -> None:
        """Fire-and-forget Projects v2 status sync (best-effort, AC 6)."""
        if not params.projects_v2_enabled:
            return
        sync_policy = STEP_POLICIES[WorkflowStep.PROJECTS_V2_SYNC]
        try:
            await workflow.execute_activity(
                update_project_status_activity,
                ProjectStatusInput(
                    taskpacket_id=params.taskpacket_id,
                    taskpacket_status=status,
                    repo_tier=params.repo_tier,
                    complexity_index=complexity_index,
                    project_item_id=params.project_item_id,
                ),
                start_to_close_timeout=sync_policy.timeout,
                retry_policy=sync_policy.to_retry_policy(),
            )
        except Exception:
            # Best-effort — log but never fail the pipeline (AC 5, 6)
            workflow.logger.warning(
                "projects_v2.sync_failed",
                extra={"taskpacket_id": params.taskpacket_id, "status": status},
            )

    @workflow.run
    async def run(self, params: PipelineInput) -> PipelineOutput:
        output = PipelineOutput()

        # Cache params for use in redirect_task signal handler's continue_as_new call.
        self._params = params

        # Step 1: Intake
        if await self._await_if_paused(WorkflowStep.INTAKE):
            output.rejection_reason = f"aborted: {self._abort_reason}"
            return output
        intake_policy = STEP_POLICIES[WorkflowStep.INTAKE]
        intake_result: IntakeOutput = await workflow.execute_activity(
            intake_activity,
            IntakeInput(
                labels=params.labels,
                repo=params.repo,
                repo_registered=params.repo_registered,
                repo_paused=params.repo_paused,
                has_active_workflow=params.has_active_workflow,
                event_id=params.event_id,
            ),
            start_to_close_timeout=intake_policy.timeout,
            retry_policy=intake_policy.to_retry_policy(),
        )
        output.step_reached = WorkflowStep.INTAKE

        if not intake_result.accepted:
            output.rejection_reason = intake_result.rejection_reason
            return output

        base_role = intake_result.base_role or "developer"
        overlays = intake_result.overlays

        # Projects v2: sync RECEIVED → Queued
        await self._sync_project_status(params, "RECEIVED")

        # Step 2: Context Enrichment
        if await self._await_if_paused(WorkflowStep.CONTEXT):
            output.rejection_reason = f"aborted: {self._abort_reason}"
            return output
        context_policy = STEP_POLICIES[WorkflowStep.CONTEXT]
        context_result: ContextOutput = await workflow.execute_activity(
            context_activity,
            ContextInput(
                taskpacket_id=params.taskpacket_id,
                repo=params.repo,
                issue_title=params.issue_title,
                issue_body=params.issue_body,
                labels=params.labels,
            ),
            start_to_close_timeout=context_policy.timeout,
            retry_policy=context_policy.to_retry_policy(),
        )
        output.step_reached = WorkflowStep.CONTEXT

        # Projects v2: sync ENRICHED → Queued (sets Risk Tier from complexity)
        await self._sync_project_status(
            params, "ENRICHED", complexity_index=context_result.complexity_index
        )

        # Step 2.5: Readiness Gate (feature-flagged) with re-evaluation loop
        if params.readiness_gate_enabled:
            current_title = params.issue_title
            current_body = params.issue_body
            evaluation_count = 0

            while True:
                if await self._await_if_paused(WorkflowStep.READINESS):
                    output.rejection_reason = f"aborted: {self._abort_reason}"
                    return output
                readiness_policy = STEP_POLICIES[WorkflowStep.READINESS]
                readiness_result: ReadinessActivityOutput = (
                    await workflow.execute_activity(
                        readiness_activity,
                        ReadinessInput(
                            taskpacket_id=params.taskpacket_id,
                            issue_title=current_title,
                            issue_body=current_body,
                            complexity_index=context_result.complexity_index,
                            risk_flags=context_result.risk_flags,
                            labels=params.labels,
                            trust_tier=params.repo_tier,
                        ),
                        start_to_close_timeout=readiness_policy.timeout,
                        retry_policy=readiness_policy.to_retry_policy(),
                    )
                )
                output.step_reached = WorkflowStep.READINESS
                evaluation_count += 1
                output.readiness_evaluations = evaluation_count

                if readiness_result.proceed:
                    # Gate passed — continue to Intent
                    break

                # Gate failed — check escalation cap
                if evaluation_count >= MAX_READINESS_EVALUATIONS:
                    output.rejection_reason = (
                        f"Readiness gate failed after {evaluation_count} evaluations; "
                        "escalated to human review"
                    )
                    output.readiness_escalated = True
                    return output

                # Wait for readiness_cleared signal (submitter updates issue)
                self._readiness_cleared = False
                try:
                    await workflow.wait_condition(
                        lambda: self._readiness_cleared,
                        timeout=READINESS_REEVALUATION_TIMEOUT,
                    )
                except TimeoutError:
                    output.rejection_reason = "readiness_reevaluation_timeout"
                    return output

                # Use updated issue content for re-evaluation
                if self._updated_issue_title:
                    current_title = self._updated_issue_title
                if self._updated_issue_body:
                    current_body = self._updated_issue_body

        # Step 3: Intent Building
        if await self._await_if_paused(WorkflowStep.INTENT):
            output.rejection_reason = f"aborted: {self._abort_reason}"
            return output
        intent_policy = STEP_POLICIES[WorkflowStep.INTENT]
        intent_result: IntentOutput = await workflow.execute_activity(
            intent_activity,
            IntentInput(
                taskpacket_id=params.taskpacket_id,
                issue_title=params.issue_title,
                issue_body=params.issue_body,
                risk_flags=context_result.risk_flags,
            ),
            start_to_close_timeout=intent_policy.timeout,
            retry_policy=intent_policy.to_retry_policy(),
        )
        output.step_reached = WorkflowStep.INTENT

        # Projects v2: sync INTENT_BUILT → In Progress
        await self._sync_project_status(params, "INTENT_BUILT")

        # Step 3.5: Intent Review (feature-flagged)
        if params.intent_review_enabled:
            output.step_reached = WorkflowStep.AWAITING_INTENT_REVIEW

            try:
                await workflow.wait_condition(
                    lambda: self._intent_approved or self._intent_rejected,
                    timeout=INTENT_REVIEW_TIMEOUT,
                )
            except TimeoutError:
                # 30-day safety timeout — escalate, do NOT auto-approve
                workflow.logger.warning(
                    "intent_review.timeout",
                    extra={"taskpacket_id": params.taskpacket_id},
                )
                output.rejection_reason = "intent_review_timeout"
                return output

            if self._intent_rejected:
                output.rejection_reason = (
                    f"Intent rejected by {self._intent_rejected_by}: "
                    f"{self._intent_rejection_reason}"
                )
                return output

            # Approved — record approver
            output.intent_approved_by = self._intent_approved_by

        # Step 4: Expert Routing
        if await self._await_if_paused(WorkflowStep.ROUTER):
            output.rejection_reason = f"aborted: {self._abort_reason}"
            return output
        router_policy = STEP_POLICIES[WorkflowStep.ROUTER]
        await workflow.execute_activity(
            router_activity,
            RouterInput(
                base_role=base_role,
                overlays=overlays,
                risk_flags=context_result.risk_flags,
                taskpacket_id=params.taskpacket_id,
            ),
            start_to_close_timeout=router_policy.timeout,
            retry_policy=router_policy.to_retry_policy(),
        )
        output.step_reached = WorkflowStep.ROUTER

        # Step 4.5: Routing Review (feature-flagged)
        if params.routing_review_enabled:
            output.step_reached = WorkflowStep.AWAITING_ROUTING_REVIEW

            try:
                await workflow.wait_condition(
                    lambda: self._routing_approved or self._routing_rejected,
                    timeout=ROUTING_REVIEW_TIMEOUT,
                )
            except TimeoutError:
                # 30-day safety timeout — escalate, do NOT auto-approve
                workflow.logger.warning(
                    "routing_review.timeout",
                    extra={"taskpacket_id": params.taskpacket_id},
                )
                output.rejection_reason = "routing_review_timeout"
                return output

            if self._routing_rejected:
                output.rejection_reason = (
                    f"Routing overridden by {self._routing_rejected_by}: "
                    f"{self._routing_rejection_reason}"
                )
                return output

            # Approved — record approver
            output.routing_approved_by = self._routing_approved_by

        # Step 5: Assembler
        if await self._await_if_paused(WorkflowStep.ASSEMBLER):
            output.rejection_reason = f"aborted: {self._abort_reason}"
            return output
        assembler_policy = STEP_POLICIES[WorkflowStep.ASSEMBLER]
        assembler_result: AssemblerOutput = await workflow.execute_activity(
            assembler_activity,
            AssemblerInput(
                taskpacket_id=params.taskpacket_id,
                intent_goal=intent_result.goal,
                intent_constraints=[],
                acceptance_criteria=intent_result.acceptance_criteria,
            ),
            start_to_close_timeout=assembler_policy.timeout,
            retry_policy=assembler_policy.to_retry_policy(),
        )
        output.step_reached = WorkflowStep.ASSEMBLER

        # Step 5.5: Preflight Plan Review (Epic 28, feature-flagged)
        if params.preflight_enabled and params.repo_tier in [
            t.lower() for t in params.preflight_tiers
        ]:
            if await self._await_if_paused(WorkflowStep.PREFLIGHT):
                output.rejection_reason = f"aborted: {self._abort_reason}"
                return output
            preflight_policy = STEP_POLICIES[WorkflowStep.PREFLIGHT]
            preflight_result: PreflightActivityOutput = (
                await workflow.execute_activity(
                    preflight_activity,
                    PreflightInput(
                        taskpacket_id=params.taskpacket_id,
                        plan_steps=assembler_result.plan_steps,
                        acceptance_criteria=intent_result.acceptance_criteria,
                        constraints=[],
                    ),
                    start_to_close_timeout=preflight_policy.timeout,
                    retry_policy=preflight_policy.to_retry_policy(),
                )
            )
            output.step_reached = WorkflowStep.PREFLIGHT
            output.preflight_approved = preflight_result.approved
            output.preflight_summary = preflight_result.summary

            if not preflight_result.approved:
                # One loopback to Assembler with preflight feedback (AC 7)
                feedback_extra = []
                if preflight_result.uncovered_criteria:
                    feedback_extra.append(
                        f"Uncovered criteria: {', '.join(preflight_result.uncovered_criteria)}"
                    )
                if preflight_result.constraint_violations:
                    violations = ", ".join(preflight_result.constraint_violations)
                    feedback_extra.append(
                        f"Constraint violations: {violations}"
                    )
                if preflight_result.vague_steps:
                    feedback_extra.append(
                        f"Vague steps: {', '.join(preflight_result.vague_steps)}"
                    )

                assembler_result = await workflow.execute_activity(
                    assembler_activity,
                    AssemblerInput(
                        taskpacket_id=params.taskpacket_id,
                        intent_goal=intent_result.goal,
                        intent_constraints=feedback_extra,
                        acceptance_criteria=intent_result.acceptance_criteria,
                    ),
                    start_to_close_timeout=assembler_policy.timeout,
                    retry_policy=assembler_policy.to_retry_policy(),
                )

                # Second preflight check
                preflight_result2: PreflightActivityOutput = (
                    await workflow.execute_activity(
                        preflight_activity,
                        PreflightInput(
                            taskpacket_id=params.taskpacket_id,
                            plan_steps=assembler_result.plan_steps,
                            acceptance_criteria=intent_result.acceptance_criteria,
                            constraints=[],
                        ),
                        start_to_close_timeout=preflight_policy.timeout,
                        retry_policy=preflight_policy.to_retry_policy(),
                    )
                )
                output.preflight_approved = preflight_result2.approved
                output.preflight_summary = preflight_result2.summary

                if not preflight_result2.approved:
                    # Proceed with warning — preflight does not block indefinitely (AC 7)
                    workflow.logger.warning(
                        "preflight.proceeding_with_warning",
                        extra={
                            "taskpacket_id": params.taskpacket_id,
                            "summary": preflight_result2.summary,
                        },
                    )

        # Steps 6-8: Implementation -> Verification -> QA loop
        verification_loopbacks = 0
        qa_loopbacks = 0
        qa_passed = False
        qa_feedback = ""

        while True:
            # Step 6: Implementation
            if await self._await_if_paused(WorkflowStep.IMPLEMENT):
                output.rejection_reason = f"aborted: {self._abort_reason}"
                return output
            impl_policy = STEP_POLICIES[WorkflowStep.IMPLEMENT]
            impl_result: ImplementOutput = await workflow.execute_activity(
                implement_activity,
                ImplementInput(
                    taskpacket_id=params.taskpacket_id,
                    repo_path=params.repo_path,
                    loopback_attempt=verification_loopbacks + qa_loopbacks,
                    repo_tier=params.repo_tier,
                    repo=params.repo,
                    issue_title=params.issue_title,
                    issue_body=params.issue_body,
                    intent_goal=intent_result.goal,
                    acceptance_criteria=intent_result.acceptance_criteria,
                    plan_steps=assembler_result.plan_steps,
                    qa_feedback=qa_feedback if (verification_loopbacks + qa_loopbacks) > 0 else "",
                ),
                start_to_close_timeout=impl_policy.timeout,
                retry_policy=impl_policy.to_retry_policy(),
            )
            output.step_reached = WorkflowStep.IMPLEMENT

            # Step 7: Verification
            if await self._await_if_paused(WorkflowStep.VERIFY):
                output.rejection_reason = f"aborted: {self._abort_reason}"
                return output
            verify_policy = STEP_POLICIES[WorkflowStep.VERIFY]
            verify_result: VerifyOutput = await workflow.execute_activity(
                verify_activity,
                VerifyInput(
                    taskpacket_id=params.taskpacket_id,
                    changed_files=impl_result.files_changed,
                    repo_path=params.repo_path,
                ),
                start_to_close_timeout=verify_policy.timeout,
                retry_policy=verify_policy.to_retry_policy(),
            )
            output.step_reached = WorkflowStep.VERIFY

            if not verify_result.passed:
                if verify_result.exhausted:
                    output.verification_loopbacks = verification_loopbacks
                    return output

                if verification_loopbacks >= MAX_VERIFICATION_LOOPBACKS:
                    output.verification_loopbacks = verification_loopbacks
                    return output

                verification_loopbacks += 1
                output.verification_loopbacks = verification_loopbacks
                continue  # Loop back to implementation

            # Step 8: QA Validation
            if await self._await_if_paused(WorkflowStep.QA):
                output.rejection_reason = f"aborted: {self._abort_reason}"
                return output
            qa_policy = STEP_POLICIES[WorkflowStep.QA]
            qa_result: QAOutput = await workflow.execute_activity(
                qa_activity,
                QAInput(
                    taskpacket_id=params.taskpacket_id,
                    acceptance_criteria=intent_result.acceptance_criteria,
                    qa_handoff=assembler_result.qa_handoff,
                    evidence={
                        "files_changed": ",".join(impl_result.files_changed),
                        "agent_summary": impl_result.agent_summary,
                    },
                ),
                start_to_close_timeout=qa_policy.timeout,
                retry_policy=qa_policy.to_retry_policy(),
            )
            output.step_reached = WorkflowStep.QA

            if qa_result.passed:
                qa_passed = True
                break

            if qa_loopbacks >= MAX_QA_LOOPBACKS:
                output.qa_loopbacks = qa_loopbacks
                return output

            qa_loopbacks += 1
            output.qa_loopbacks = qa_loopbacks
            qa_feedback = f"QA failed: defects={qa_result.defect_count}, intent_gap={qa_result.has_intent_gap}"
            # Loop back to implementation for QA rework

        # Step 8.5: Approval Wait (Suggest/Execute tier only)
        if params.repo_tier in APPROVAL_REQUIRED_TIERS and not params.approval_auto_bypass:
            # Post approval request comment before entering wait
            if await self._await_if_paused(WorkflowStep.AWAITING_APPROVAL):
                output.rejection_reason = f"aborted: {self._abort_reason}"
                return output
            await workflow.execute_activity(
                post_approval_request_activity,
                ApprovalRequestInput(
                    taskpacket_id=params.taskpacket_id,
                    repo_tier=params.repo_tier,
                    intent_summary=intent_result.goal,
                    qa_passed=qa_passed,
                ),
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

            output.step_reached = WorkflowStep.AWAITING_APPROVAL
            output.awaiting_approval = True

            # Projects v2: sync AWAITING_APPROVAL → In Review
            await self._sync_project_status(params, "AWAITING_APPROVAL")
            approval_wait_start = workflow.now()

            # Durable wait: block until approved, rejected, or 7-day timeout
            try:
                await workflow.wait_condition(
                    lambda: self._approved or self._rejected,
                    timeout=APPROVAL_TIMEOUT,
                )
            except TimeoutError:
                # 7-day timeout expired — escalate, do NOT publish
                await workflow.execute_activity(
                    escalate_timeout_activity,
                    EscalateTimeoutInput(
                        taskpacket_id=params.taskpacket_id,
                        repo_tier=params.repo_tier,
                    ),
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=RetryPolicy(maximum_attempts=3),
                )
                # Approval baseline: record timeout event
                approval_wait_hours = (
                    (workflow.now() - approval_wait_start).total_seconds() / 3600.0
                )
                workflow.logger.info(
                    "approval.baseline.timeout",
                    extra={
                        "taskpacket_id": params.taskpacket_id,
                        "repo_tier": params.repo_tier,
                        "outcome": "timeout",
                        "wait_hours": f"{approval_wait_hours:.2f}",
                    },
                )
                output.rejection_reason = "approval_timeout"
                output.verification_loopbacks = verification_loopbacks
                output.qa_loopbacks = qa_loopbacks
                return output

            # Check if rejected
            if self._rejected:
                approval_wait_hours = (
                    (workflow.now() - approval_wait_start).total_seconds() / 3600.0
                )
                workflow.logger.info(
                    "approval.baseline.rejected",
                    extra={
                        "taskpacket_id": params.taskpacket_id,
                        "repo_tier": params.repo_tier,
                        "outcome": "rejected",
                        "rejected_by": self._rejected_by,
                        "wait_hours": f"{approval_wait_hours:.2f}",
                    },
                )
                output.rejection_reason = (
                    f"rejected by {self._rejected_by}: {self._rejection_reason}"
                )
                output.verification_loopbacks = verification_loopbacks
                output.qa_loopbacks = qa_loopbacks
                return output

            # Approved — record approver and baseline timing
            approval_wait_hours = (
                (workflow.now() - approval_wait_start).total_seconds() / 3600.0
            )
            workflow.logger.info(
                "approval.baseline.approved",
                extra={
                    "taskpacket_id": params.taskpacket_id,
                    "repo_tier": params.repo_tier,
                    "outcome": "approved",
                    "approved_by": self._approved_by,
                    "wait_hours": f"{approval_wait_hours:.2f}",
                },
            )
            output.approved_by = self._approved_by

        elif params.repo_tier in APPROVAL_REQUIRED_TIERS and params.approval_auto_bypass:
            workflow.logger.info(
                "approval.auto_bypass",
                extra={
                    "taskpacket_id": params.taskpacket_id,
                    "repo_tier": params.repo_tier,
                },
            )
            output.approval_bypassed = True

        # Step 9: Publish
        if await self._await_if_paused(WorkflowStep.PUBLISH):
            output.rejection_reason = f"aborted: {self._abort_reason}"
            return output
        publish_policy = STEP_POLICIES[WorkflowStep.PUBLISH]
        publish_result: PublishOutput = await workflow.execute_activity(
            publish_activity,
            PublishInput(
                taskpacket_id=params.taskpacket_id,
                repo_tier=params.repo_tier,
                qa_passed=qa_passed,
                files_changed=impl_result.files_changed,
                agent_summary=impl_result.agent_summary,
            ),
            start_to_close_timeout=publish_policy.timeout,
            retry_policy=publish_policy.to_retry_policy(),
        )
        output.step_reached = WorkflowStep.PUBLISH
        output.success = True

        # Projects v2: sync PUBLISHED → Done (AC 5)
        await self._sync_project_status(params, "PUBLISHED")
        output.pr_number = publish_result.pr_number
        output.pr_url = publish_result.pr_url
        output.marked_ready = publish_result.marked_ready
        output.verification_loopbacks = verification_loopbacks
        output.qa_loopbacks = qa_loopbacks

        return output
