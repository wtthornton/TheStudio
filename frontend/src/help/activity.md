# Activity Log

The Activity Log records every significant action taken by the system and by human operators. It is the authoritative audit trail for TheStudio — a permanent, immutable record of what happened, when, and why.

## What is logged

- **Pipeline events** — task state transitions, stage gate results (pass/fail), loopback triggers and their reasons
- **Steering actions** — trust tier changes, routing overrides, budget limit updates, triage decisions
- **Agent decisions** — intent spec generation, expert assignments, QA outcomes and rejection reasons
- **Webhook events** — incoming GitHub events, eligibility check results, and any parsing errors
- **System events** — service restarts, configuration changes, health check failures

## Reading log entries

Each entry shows:

| Field | Content |
|-------|---------|
| Timestamp | When the event occurred (UTC, millisecond precision) |
| Category | pipeline, steering, agent, webhook, or system |
| Task ID | The affected TaskPacket — click to open in the Pipeline tab |
| Message | Human-readable description of the event |
| Evidence | Structured JSON payload with full context for the event |

Expand any entry to see the raw evidence payload. This is especially useful when debugging a gate failure — the evidence bundle explains exactly why the gate rejected the task.

## Filtering

Use the filter controls to narrow the log to what you need:

- **Time range** — last hour, last day, last week, or a custom date range
- **Category** — show only pipeline events, or only steering actions
- **Repository** — scope to a single repo's activity
- **Task ID or correlation ID** — find all events for a specific task

## Audit trail and compliance

The activity log provides a complete, tamper-proof audit trail. All entries are immutable once written. If you need to export the log for compliance review or incident investigation, use the **Download CSV** button to export the current filtered view.

## Correlation IDs

Every pipeline run generates a unique `correlation_id` that links all log entries for that task across all stages and services. Search by correlation ID to reconstruct the complete history of any task from webhook receipt through to PR publication — or failure. This is the fastest path to root-cause analysis when something goes wrong.
