# Story 17.2 — Synthetic Delivery ID and Feed Pipeline

> **As a** platform developer,
> **I want** a stable synthetic delivery ID for poll-originated events and a feed that creates TaskPackets and starts workflows,
> **so that** poll-discovered issues enter the pipeline exactly like webhook events.

**Purpose:** Poll-originated issues need a stable synthetic delivery ID that aligns with existing `(delivery_id, repo)` dedupe. Without it, duplicates could be created or the pipeline would not recognize poll-originated events. This story delivers the feed so polled issues flow into the same TaskPacket + workflow path as webhooks.

**Intent:** Generate deterministic synthetic delivery IDs per (repo, issue_number, updated_at). Feed issues through dedupe, `create_taskpacket`, and `start_workflow` using the same contracts as the webhook handler. At-most-once semantics via existing `ix_taskpacket_delivery_repo` constraint.

**Points:** 5 | **Size:** M
**Epic:** 17 — Poll for Issues as Backup to Webhooks
**Sprint:** A (Stories 17.1–17.2)
**Depends on:** Story 17.1 (Poll Client)
**Status:** COMPLETE (2026-03-13)

---

## Description

Poll-originated issues need a stable synthetic delivery ID that aligns with the existing `(delivery_id, repo)` dedupe in the TaskPacket model. The feed pipeline takes raw issues from the poll client, computes synthetic IDs, checks for duplicates, and creates TaskPackets and starts workflows using the same logic as the webhook handler.

## Tasks

- [x] Create `src/ingress/poll/feed.py`:
  - `synthetic_delivery_id(repo_full_name: str, issue_number: int, updated_at: str) -> str`
    - Format: `poll-{owner}-{repo}-{issue_number}-{updated_at_normalized}`
    - Normalize `updated_at` to ISO 8601 (replace colons with hyphens for uniqueness)
  - `feed_issues_to_pipeline(session: AsyncSession, issues: list[dict], repo_full_name: str) -> int`
    - For each issue: extract `number`, `updated_at`
    - Compute `delivery_id = synthetic_delivery_id(repo_full_name, number, updated_at)`
    - Call `is_duplicate(session, delivery_id, repo_full_name)` — skip if True
    - Build `TaskPacketCreate(repo=repo_full_name, issue_id=number, delivery_id=delivery_id, correlation_id=uuid4())`
    - Call `create_taskpacket`, then `start_workflow`
    - Return count of TaskPackets created
- [x] Reuse `src/ingress/dedupe.is_duplicate`
- [x] Reuse `src/ingress/workflow_trigger.start_workflow`
- [x] Reuse `src/models/taskpacket_crud.create`
- [x] Write unit tests: synthetic ID format, dedupe behavior, feed with mocked CRUD

## Acceptance Criteria

- [x] Synthetic ID is deterministic (same input → same ID)
- [x] Synthetic ID is unique per (repo, issue_number, updated_at)
- [x] Duplicate (delivery_id, repo) skips creation
- [x] Created TaskPackets match webhook format (repo, issue_id, delivery_id, correlation_id)
- [x] Unit tests cover ID generation, dedupe, feed

## Test Cases

| # | Scenario | Input | Expected Output | Status |
|---|----------|-------|-----------------|--------|
| 1 | New issues | 2 issues not in DB | 2 TaskPackets created, 2 workflows started | PASS |
| 2 | Duplicate issue | Same (repo, issue, updated_at) already exists | Skip, count=0 | PASS |
| 3 | Mixed new/dup | 1 duplicate + 1 new | 1 TaskPacket created | PASS |
| 4 | ID determinism | Same (repo, 42, updated_at) twice | Same synthetic delivery ID | PASS |
| 5 | ID differs on issue | Same repo, different issue numbers | Different IDs | PASS |
| 6 | ID differs on update | Same issue, different updated_at | Different IDs | PASS |
| 7 | Missing fields | Issues without number or updated_at | Skipped, count=0 | PASS |
| 8 | ID format | Valid inputs | Starts with "poll-", contains repo and issue | PASS |

## Files Affected

| File | Action |
|------|--------|
| `src/ingress/poll/feed.py` | Created |
| `tests/unit/test_ingress/test_poll_feed.py` | Created (8 tests) |

## Technical Notes

- TaskPacket unique constraint: `(delivery_id, repo)` — synthetic ID must be distinct per update
- Webhook handler: `TaskPacketCreate(repo, issue_id, delivery_id, correlation_id)` — same shape
- `updated_at` from GitHub API is ISO 8601; normalized for deterministic ID (colons → hyphens)
- Correlation ID generated per issue via OpenTelemetry baggage propagation
