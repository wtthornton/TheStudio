# Story 25.7 — Observability for Containerized Agents

> **As a** platform operator,
> **I want** OpenTelemetry spans, structured logs with correlation_id, and container lifecycle metrics for every containerized agent execution,
> **so that** I can trace, debug, and monitor container-isolated agent tasks with the same fidelity as in-process tasks.

**Purpose:** Container isolation introduces a new operational boundary. Without observability that spans that boundary, debugging a failed containerized task requires manually inspecting Docker logs, container state, and result files. This story ensures the container lifecycle is fully instrumented — launch through cleanup — with the same structured logging and tracing patterns the rest of the pipeline uses.

**Intent:** Add OpenTelemetry spans to every `ContainerManager` method (launch, wait, collect_results, cleanup). Capture container stdout/stderr after exit and emit as structured log entries with `correlation_id`. Define span attribute conventions for container lifecycle events. Add structured log events for container metrics (active count, duration by tier, timeout rate).

**Points:** 5 | **Size:** M
**Epic:** 25 — Container Isolation for Primary Agent
**Sprint:** 3 (Observability and Hardening)
**Depends on:** Stories 25.2 (ContainerManager), 25.4 (activity integration)

---

## Description

The container lifecycle has four phases that need instrumentation:

1. **Launch**: How long did container creation take? What image was used? What resource limits were applied? Did it succeed or fail?

2. **Wait**: How long did the container run? Did it exit normally, timeout, or OOM? What was the exit code?

3. **Collect**: Did the result file exist? How large was it? Was it parseable? How long did collection take?

4. **Cleanup**: Did cleanup succeed? Were volumes removed? How long did cleanup take?

Each phase gets its own OpenTelemetry span, nested under a parent span for the full container lifecycle. The parent span is nested under the existing `implement_activity` span, creating a clear trace hierarchy:

```
implement_activity
  └── container_lifecycle
        ├── container_launch
        ├── container_wait
        ├── container_collect
        └── container_cleanup
```

Container stdout/stderr are captured after container exit (not streamed) and emitted as structured log entries with the task's `correlation_id`. This connects container-internal logs to the pipeline's existing log correlation.

## Tasks

- [ ] Add span name constants to `src/observability/conventions.py`:
  - `SPAN_CONTAINER_LIFECYCLE = "thestudio.agent.container_lifecycle"`
  - `SPAN_CONTAINER_LAUNCH = "thestudio.agent.container_launch"`
  - `SPAN_CONTAINER_WAIT = "thestudio.agent.container_wait"`
  - `SPAN_CONTAINER_COLLECT = "thestudio.agent.container_collect"`
  - `SPAN_CONTAINER_CLEANUP = "thestudio.agent.container_cleanup"`
  - Attribute constants: `ATTR_CONTAINER_ID`, `ATTR_CONTAINER_IMAGE`, `ATTR_CONTAINER_EXIT_CODE`, `ATTR_CONTAINER_DURATION_MS`, `ATTR_CONTAINER_RESOURCE_CPUS`, `ATTR_CONTAINER_RESOURCE_MEMORY_MB`, `ATTR_CONTAINER_REPO_TIER`, `ATTR_CONTAINER_EXIT_REASON`
- [ ] Instrument `ContainerManager` methods with spans:
  - `launch()`: span with image, resource limits, network, container_id (set after creation)
  - `wait()`: span with container_id, timeout_seconds, exit_code, duration_ms
  - `collect_results()`: span with container_id, result_found (bool), result_size_bytes
  - `cleanup()`: span with container_id, cleanup_success (bool)
  - All spans: set `correlation_id` and `taskpacket_id` as attributes when available
- [ ] Add parent span in `implement_activity` container mode path:
  - Wrap the full container lifecycle (launch through cleanup) in a `container_lifecycle` span
  - Set attributes: container_id, repo_tier, image, resource limits
- [ ] Capture container logs after exit:
  - `ContainerManager.collect_logs()` retrieves stdout and stderr
  - In `implement_activity`, after `collect_logs()`, emit each line as a structured log entry:
    - `logger.info("container.stdout", extra={"correlation_id": ..., "container_id": ..., "line": ...})`
    - `logger.warning("container.stderr", extra={"correlation_id": ..., "container_id": ..., "line": ...})`
  - Truncate log output to configurable max (default 10,000 lines) to avoid log flooding
- [ ] Emit container lifecycle metrics as structured log events:
  - `container.launched`: emitted on successful launch
  - `container.completed`: emitted on container exit with duration_ms, exit_code, exit_reason, repo_tier
  - `container.timeout`: emitted on timeout
  - `container.oom`: emitted on OOM kill
  - `container.cleanup.completed`: emitted on successful cleanup
  - `container.orphan.reaped`: emitted by reaper for each removed container
- [ ] Write tests in `tests/agent/test_container_observability.py`:
  - Verify spans are created for each lifecycle phase
  - Verify span attributes include container_id, resource limits, exit_code
  - Verify correlation_id propagates to all spans and log entries
  - Verify container logs are emitted with correlation_id
  - Verify log truncation at configured max
  - Verify metric events are emitted for each lifecycle phase

## Acceptance Criteria

- [ ] OpenTelemetry spans cover launch, wait, collect, and cleanup
- [ ] Spans include container_id, resource limits, exit_code, duration_ms, repo_tier
- [ ] Container stdout/stderr are captured and logged with correlation_id
- [ ] Log output is truncated to prevent flooding
- [ ] Structured metric events are emitted for lifecycle phases
- [ ] All spans are children of the container_lifecycle parent span
- [ ] Container lifecycle span is a child of the implement_activity span

## Test Cases

| # | Scenario | Input | Expected Output |
|---|----------|-------|-----------------|
| 1 | Happy path spans | Container launches, runs, exits 0 | 4 spans: launch, wait, collect, cleanup — all with container_id |
| 2 | Timeout span | Container times out | Wait span has exit_code=-1, exit_reason="timeout" |
| 3 | OOM span | Container OOM-killed | Wait span has exit_reason="oom" |
| 4 | Correlation propagation | Task with correlation_id=abc-123 | All spans and logs have correlation_id=abc-123 |
| 5 | Log capture | Container writes 10 lines to stdout | 10 structured log entries with correlation_id |
| 6 | Log truncation | Container writes 20,000 lines | Only first 10,000 lines logged, truncation warning emitted |
| 7 | Metric events | Full lifecycle | Events emitted for launched, completed, cleanup.completed |

## Files Affected

| File | Action |
|------|--------|
| `src/observability/conventions.py` | Modify (add container span and attribute constants) |
| `src/agent/container_manager.py` | Modify (add span instrumentation to all methods) |
| `src/workflow/activities.py` | Modify (add parent span, log capture, metric events) |
| `tests/agent/test_container_observability.py` | Create |

## Technical Notes

- Use `get_tracer("thestudio.agent.container")` for container-specific spans, consistent with the existing `get_tracer("thestudio.agent")` for the Primary Agent.
- Span nesting: use `tracer.start_as_current_span()` context manager so child spans automatically parent to the current span.
- Container log capture: `container.logs(stdout=True, stderr=True)` returns bytes. Decode as UTF-8, split by newline, emit each line. The `stream=False` option retrieves all logs at once (not streamed).
- Log truncation: configurable via `settings.agent_container_max_log_lines: int = 10000`. When exceeded, emit a warning: `"container.logs.truncated"` with the total line count.
- OpenTelemetry span attributes have limits (typically 128 bytes per attribute value). Container logs go to structured logging, not span attributes, to avoid hitting these limits.
- If the OpenTelemetry SDK is not configured (`otel_exporter="console"`), spans are printed to console — same behavior as the rest of the pipeline.
