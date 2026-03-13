# Spike: Temporal Signals, Wait Conditions, and Timers

**Epic:** 21 — Human Approval Wait States (C6)
**Date:** 2026-03-12
**Status:** Complete

---

## 1. Objective

Determine the correct Temporal Python SDK patterns for:
- Signal handlers on running workflows
- `workflow.wait_condition()` with a timeout (7-day durable wait)
- Time-skipping in tests via `temporalio.testing.WorkflowEnvironment`

## 2. SDK Version Requirements

The `temporalio` Python SDK supports signals, `workflow.wait_condition`, and
time-skipping from version **1.0.0+**. Our project uses `temporalio >= 1.4.0`
(see `pyproject.toml`), which fully supports all required primitives.

Key imports:
```python
from temporalio import workflow
from datetime import timedelta
```

## 3. Signal Handler Pattern

Signals are defined as methods on the workflow class decorated with
`@workflow.signal`. They execute in the workflow's event loop and can modify
workflow state.

```python
@workflow.defn
class MyWorkflow:
    def __init__(self) -> None:
        self._approved = False
        self._approved_by: str | None = None

    @workflow.signal
    async def approve_publish(self, approved_by: str, approval_source: str) -> None:
        """Signal handler — sets approval flag and records approver."""
        self._approved = True
        self._approved_by = approved_by

    @workflow.run
    async def run(self, params: PipelineInput) -> PipelineOutput:
        # ... workflow logic ...
        pass
```

### Key constraints:
- Signal handlers **must not** raise exceptions (they run in the workflow's
  deterministic execution context)
- Signal handlers **can** modify instance state — this is the intended pattern
- Signal delivery is **at-least-once** — handlers must be idempotent
- Signals can be sent before the workflow reaches `wait_condition` — Temporal
  buffers them

## 4. Wait Condition with Timeout

`workflow.wait_condition(fn, timeout=timedelta)` blocks the workflow until
either the condition function returns `True` or the timeout expires.

```python
try:
    await workflow.wait_condition(
        lambda: self._approved,
        timeout=timedelta(days=7),
    )
    # Condition met — approved
    proceed_to_publish = True
except asyncio.TimeoutError:
    # 7-day timeout expired — escalate
    proceed_to_publish = False
```

### Key behaviors:
- `wait_condition` is **durable** — survives worker restarts, replays correctly
- The timeout is a **Temporal timer**, not a Python `asyncio.sleep` — it is
  tracked by the Temporal server and fires deterministically
- If the signal arrives at the exact moment of timeout, **Temporal resolves
  deterministically**: the timer fires first, then the signal is delivered. The
  workflow sees the timeout. This is safe — the signal is simply ignored.
- `wait_condition` raises `asyncio.TimeoutError` on timeout (not a Temporal-
  specific exception)
- The condition function is evaluated each time workflow state changes (after
  signal delivery, activity completion, etc.)

## 5. Signal-Timeout Race Condition

**Q:** What happens if `approve_publish` signal arrives at the exact tick of
the 7-day timer?

**A:** Temporal's deterministic scheduler resolves this consistently:
1. The timer fires first (timeout wins)
2. The signal is buffered and delivered after
3. The workflow sees `TimeoutError` from `wait_condition`
4. The signal handler still runs, setting `self._approved = True`
5. But the workflow has already moved past the wait — no double-publish

This is safe because:
- The workflow checks `proceed_to_publish` (set by try/except), not
  `self._approved`, for the publish decision after the wait
- Even if `self._approved` becomes `True` after timeout, the workflow is
  already on the escalation path

## 6. Workflow History Size

A 7-day wait with a single timer adds **2 events** to workflow history:
- `TimerStarted`
- `TimerFired` (or `TimerCanceled` if signal arrives first)

Plus signal events:
- `WorkflowSignalReceived` (one per signal)

This is negligible. The existing pipeline generates ~20-30 events per run.
Adding the wait state brings the total to ~25-35 events — well under
Temporal's 50,000-event limit.

**No `continue_as_new` needed** for this use case.

## 7. Workflow Execution Timeout

The default Temporal workflow execution timeout must accommodate the 7-day
wait. Current pipeline workflows complete in minutes. With the approval wait,
the worst case is 7 days + pipeline execution time.

**Action required:** Set `execution_timeout=timedelta(days=8)` on the workflow
starter (or leave it unset — Temporal defaults to no timeout, which is fine
for our use case since the 7-day timer handles expiry).

## 8. Time-Skipping in Tests

The `temporalio.testing.WorkflowEnvironment` supports time-skipping, which
allows testing 7-day timeouts in seconds.

```python
import asyncio
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

async def test_approval_timeout():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[TheStudioPipelineWorkflow],
            activities=[...all activities...],
        ):
            handle = await env.client.start_workflow(
                TheStudioPipelineWorkflow.run,
                PipelineInput(repo_tier="suggest", ...),
                id="test-wf",
                task_queue="test-queue",
            )

            # Time skips automatically — 7 days pass in ~1 second
            result = await handle.result()

            assert not result.success
            assert result.rejection_reason == "approval_timeout"


async def test_approval_signal():
    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[TheStudioPipelineWorkflow],
            activities=[...all activities...],
        ):
            handle = await env.client.start_workflow(
                TheStudioPipelineWorkflow.run,
                PipelineInput(repo_tier="suggest", ...),
                id="test-wf",
                task_queue="test-queue",
            )

            # Wait briefly for workflow to reach wait state
            await asyncio.sleep(1)

            # Send approval signal
            await handle.signal(
                TheStudioPipelineWorkflow.approve_publish,
                args=["admin@example.com", "api"],
            )

            result = await handle.result()
            assert result.success
            assert result.approved_by == "admin@example.com"
```

### Key notes:
- `WorkflowEnvironment.start_time_skipping()` uses the Temporal test server
  with time-skipping enabled
- Time advances automatically when the workflow is blocked on a timer
- `asyncio.sleep(1)` in test code allows the workflow to progress to the
  wait state before sending the signal
- All tests should complete in under 30 seconds total

## 9. Determinism Constraints

Temporal workflows must be deterministic. Key rules:
- **No `datetime.now()`** in workflow code — use `workflow.now()` instead
- **No `random`** — use `workflow.random()`
- **No I/O** in workflow code — all I/O goes in activities
- Signal handlers run in the workflow's deterministic context — they must only
  modify instance state, not perform I/O

Our implementation follows these rules:
- The signal handler only sets `self._approved` and `self._approved_by`
- The approval request comment and escalation are separate activities
- Timestamps use `workflow.now()` (not `datetime.now()`)

## 10. Conclusion

All required Temporal primitives are available and well-documented. The
implementation pattern is straightforward:

1. Add `@workflow.signal` handler that sets a flag
2. Use `workflow.wait_condition(lambda: self._approved, timeout=timedelta(days=7))`
3. Catch `asyncio.TimeoutError` for the escalation path
4. Use activities for all I/O (posting comments, applying labels)
5. Use `WorkflowEnvironment.start_time_skipping()` for tests

No SDK version upgrade needed. No `continue_as_new` needed. No execution
timeout change needed (default is unlimited).
