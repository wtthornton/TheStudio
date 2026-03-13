"""TheStudio Pipeline Workflow — Temporal workflow definition.

Wires the full 9-step runtime flow from GitHub issue to ready-for-review PR.

Architecture reference: thestudioarc/15-system-runtime-flow.md

Steps:
1. Intake Agent — eligibility, role selection
2. Context Manager — scope, risk, complexity
3. Intent Builder — goal, constraints, acceptance criteria
4. Expert Router — select expert subset
5. Assembler — merge expert outputs into plan
6. Primary Agent — implement changes
7. Verification Gate — run checks, loopback on failure
8. QA Agent — validate against intent, loopback on failure
9. Publisher — create PR with evidence

Retry/timeout policy per the architecture table in 15-system-runtime-flow.md.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from enum import StrEnum

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from src.workflow.activities import (
        AssemblerInput,
        AssemblerOutput,
        ContextInput,
        ContextOutput,
        ImplementInput,
        ImplementOutput,
        IntakeInput,
        IntakeOutput,
        IntentInput,
        IntentOutput,
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
        implement_activity,
        intake_activity,
        intent_activity,
        publish_activity,
        qa_activity,
        readiness_activity,
        router_activity,
        verify_activity,
    )


class WorkflowStep(StrEnum):
    """Named steps for observability and debugging."""

    INTAKE = "intake"
    CONTEXT = "context"
    READINESS = "readiness"
    INTENT = "intent"
    ROUTER = "router"
    ASSEMBLER = "assembler"
    IMPLEMENT = "implement"
    VERIFY = "verify"
    QA = "qa"
    PUBLISH = "publish"


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
    WorkflowStep.PUBLISH: StepPolicy(
        timeout=timedelta(minutes=5), max_retries=5,
        initial_interval=timedelta(seconds=0.5),  # fast retry
        backoff_coefficient=1.5,
    ),
}

# Loopback caps
MAX_VERIFICATION_LOOPBACKS = 2
MAX_QA_LOOPBACKS = 2


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


@workflow.defn
class TheStudioPipelineWorkflow:
    """Full 9-step runtime flow from GitHub issue to ready-for-review PR.

    Handles loopbacks for verification (max 2) and QA (max 2).
    Gates fail closed — exhaustion results in workflow failure.
    """

    @workflow.run
    async def run(self, params: PipelineInput) -> PipelineOutput:
        output = PipelineOutput()

        # Step 1: Intake
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

        # Step 2: Context Enrichment
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

        # Step 2.5: Readiness Gate (feature-flagged)
        if params.readiness_gate_enabled:
            readiness_policy = STEP_POLICIES[WorkflowStep.READINESS]
            readiness_result: ReadinessActivityOutput = (
                await workflow.execute_activity(
                    readiness_activity,
                    ReadinessInput(
                        taskpacket_id=params.taskpacket_id,
                        issue_title=params.issue_title,
                        issue_body=params.issue_body,
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

            if not readiness_result.proceed:
                output.rejection_reason = readiness_result.hold_reason
                return output

        # Step 3: Intent Building
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

        # Step 4: Expert Routing
        router_policy = STEP_POLICIES[WorkflowStep.ROUTER]
        await workflow.execute_activity(
            router_activity,
            RouterInput(
                base_role=base_role,
                overlays=overlays,
                risk_flags=context_result.risk_flags,
            ),
            start_to_close_timeout=router_policy.timeout,
            retry_policy=router_policy.to_retry_policy(),
        )
        output.step_reached = WorkflowStep.ROUTER

        # Step 5: Assembler
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

        # Steps 6-8: Implementation → Verification → QA loop
        verification_loopbacks = 0
        qa_loopbacks = 0
        qa_passed = False

        while True:
            # Step 6: Implementation
            impl_policy = STEP_POLICIES[WorkflowStep.IMPLEMENT]
            impl_result: ImplementOutput = await workflow.execute_activity(
                implement_activity,
                ImplementInput(
                    taskpacket_id=params.taskpacket_id,
                    repo_path=params.repo_path,
                    loopback_attempt=verification_loopbacks + qa_loopbacks,
                ),
                start_to_close_timeout=impl_policy.timeout,
                retry_policy=impl_policy.to_retry_policy(),
            )
            output.step_reached = WorkflowStep.IMPLEMENT

            # Step 7: Verification
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
                    # Gate fail closed — workflow fails
                    output.verification_loopbacks = verification_loopbacks
                    return output

                if verification_loopbacks >= MAX_VERIFICATION_LOOPBACKS:
                    # Cap reached — fail closed
                    output.verification_loopbacks = verification_loopbacks
                    return output

                verification_loopbacks += 1
                output.verification_loopbacks = verification_loopbacks
                continue  # Loop back to implementation

            # Step 8: QA Validation
            qa_policy = STEP_POLICIES[WorkflowStep.QA]
            qa_result: QAOutput = await workflow.execute_activity(
                qa_activity,
                QAInput(
                    taskpacket_id=params.taskpacket_id,
                    acceptance_criteria=intent_result.acceptance_criteria,
                    qa_handoff=assembler_result.qa_handoff,
                    evidence={"files_changed": ",".join(impl_result.files_changed)},
                ),
                start_to_close_timeout=qa_policy.timeout,
                retry_policy=qa_policy.to_retry_policy(),
            )
            output.step_reached = WorkflowStep.QA

            if qa_result.passed:
                qa_passed = True
                break

            if qa_loopbacks >= MAX_QA_LOOPBACKS:
                # QA cap reached — fail closed
                output.qa_loopbacks = qa_loopbacks
                return output

            qa_loopbacks += 1
            output.qa_loopbacks = qa_loopbacks
            # Loop back to implementation for QA rework

        # Step 9: Publish
        publish_policy = STEP_POLICIES[WorkflowStep.PUBLISH]
        publish_result: PublishOutput = await workflow.execute_activity(
            publish_activity,
            PublishInput(
                taskpacket_id=params.taskpacket_id,
                repo_tier=params.repo_tier,
                qa_passed=qa_passed,
            ),
            start_to_close_timeout=publish_policy.timeout,
            retry_policy=publish_policy.to_retry_policy(),
        )
        output.step_reached = WorkflowStep.PUBLISH
        output.success = True
        output.pr_number = publish_result.pr_number
        output.pr_url = publish_result.pr_url
        output.marked_ready = publish_result.marked_ready
        output.verification_loopbacks = verification_loopbacks
        output.qa_loopbacks = qa_loopbacks

        return output
