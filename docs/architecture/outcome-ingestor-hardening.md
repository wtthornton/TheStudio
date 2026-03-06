# Outcome Ingestor Hardening (Story 2.3)

## Overview

Story 2.3 adds quarantine, dead-letter, and replay mechanisms to the Outcome Ingestor to ensure malformed or uncorrelated signals do not poison learning.

Architecture reference: `thestudioarc/12-outcome-ingestor.md` lines 83-105

## Components

### QuarantineStore

Location: `src/outcome/quarantine.py`

Persists signals that fail validation for operator review and potential replay.

**Operations:**
- `quarantine(event_payload, reason, repo_id?, category?)` - Quarantine an event
- `list_quarantined(repo_id?, category?, reason?, include_replayed?, limit, offset)` - List events
- `get_quarantined(quarantine_id)` - Get single event with full payload
- `mark_corrected(quarantine_id, corrected_payload)` - Mark as corrected with fixed payload
- `mark_replayed(quarantine_id)` - Mark as replayed after successful replay
- `count_by_reason(repo_id?)` - Count by quarantine reason

### DeadLetterStore

Location: `src/outcome/dead_letter.py`

Terminal storage for events that cannot be parsed or validated after max attempts.

**Operations:**
- `add_dead_letter(raw_payload, failure_reason, attempt_count)` - Add event
- `list_dead_letters(limit, offset)` - List events
- `get_dead_letter(id)` - Get single event
- `delete(id)` - Delete after manual resolution

### FailureTracker

Location: `src/outcome/dead_letter.py`

Tracks processing failures per event to determine dead-letter eligibility.

**Configuration:**
- `max_attempts` (default 3) - Attempts before dead-letter

### Replay Mechanism

Location: `src/outcome/replay.py`

Replays quarantined events after correction.

**Operations:**
- `replay_quarantined(quarantine_id, ingest_fn)` - Replay single event
- `replay_batch(quarantine_ids, ingest_fn)` - Replay multiple in order
- `replay_deterministic(events, ingest_fn)` - Sync replay for backfill

## Quarantine Rules

Per `thestudioarc/12-outcome-ingestor.md` lines 87-93:

| Condition | QuarantineReason |
|-----------|------------------|
| Missing correlation_id | `missing_correlation_id` |
| Unknown TaskPacket | `unknown_taskpacket` |
| Unknown repo_id | `unknown_repo` |
| Invalid event type | `invalid_event` |
| Invalid defect category/severity | `invalid_category_severity` |
| Duplicate with conflicting payload | `idempotency_conflict` |

## Dead-Letter Rules

- Events that fail parsing/validation after `max_attempts` (default 3) are moved to dead-letter
- Raw payload and failure reason preserved for debugging
- Dead-letter events are terminal — manual investigation required

## Replay Contract

1. Uses `corrected_payload` if available, otherwise `event_payload`
2. Processes events in provided order (deterministic)
3. Links replayed signals to original quarantine_id for audit
4. Marks event as replayed on success

## Database Schema

### quarantined_events Table

```sql
CREATE TABLE quarantined_events (
    quarantine_id UUID PRIMARY KEY,
    event_payload JSONB NOT NULL,
    reason quarantine_reason NOT NULL,
    repo_id VARCHAR(255),
    category VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    corrected_at TIMESTAMPTZ,
    corrected_payload JSONB,
    replayed_at TIMESTAMPTZ
);
```

### dead_letter_events Table

```sql
CREATE TABLE dead_letter_events (
    id UUID PRIMARY KEY,
    raw_payload BYTEA NOT NULL,
    failure_reason TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## Signals Emitted

- `event_quarantined` - When an event is quarantined
- `event_dead_lettered` - When an event is moved to dead-letter
- `event_replayed` - When a quarantined event is successfully replayed

## Admin UI Integration

Per `thestudioarc/12-outcome-ingestor.md` lines 101-104:

- Show quarantined count by repo and category
- Provide drill-down to failure reason and payload pointer
- Provide replay action with audit log
