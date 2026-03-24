# Activity Log

The Activity Log records every significant action taken by the system and by human operators.

## What is logged

- **Pipeline events** — task state transitions, gate results, loopback triggers
- **Steering actions** — trust tier changes, routing overrides, budget updates
- **Agent decisions** — intent spec generation, expert assignments, QA outcomes
- **Webhook events** — incoming GitHub events and their handling

## Reading log entries

Each entry shows:
- **Timestamp** — when the event occurred
- **Category** — pipeline, steering, agent, or webhook
- **Task ID** — the affected TaskPacket (click to open in Pipeline tab)
- **Message** — human-readable description of the event
- **Evidence** — structured data payload attached to the event

## Filtering

Use the filter controls to narrow down the log by:
- Time range (last hour, day, week, custom)
- Category
- Repository
- Task ID

## Audit trail

The activity log provides a complete audit trail for compliance purposes. All entries are immutable once written. Export to CSV using the download button.

## Correlation IDs

Each pipeline run has a unique `correlation_id` that links all log entries for that task. Search by correlation ID to reconstruct the full history of any task.
