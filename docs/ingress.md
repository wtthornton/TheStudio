# Ingress — Issue Intake Architecture

TheStudio supports two intake paths for discovering GitHub issues. Both converge at the same point: a **TaskPacket** is created and a pipeline workflow is started.

## Paths

### 1. Webhook Path (Primary)

GitHub sends a `issues` webhook event to `POST /webhook`. The intake module:

1. Verifies the webhook signature against the repo's stored secret
2. Checks eligibility (label filter, repo registered, not paused, no active workflow)
3. Creates a **TaskPacket** with the GitHub delivery ID
4. Starts the pipeline workflow via Temporal

**Preferred when:** The TheStudio instance has a public URL reachable by GitHub.

### 2. Poll Path (Backup — Epic 17)

A background scheduler periodically fetches `GET /repos/{owner}/{repo}/issues` from the GitHub API. The poll path:

1. **Scheduler** (`src/ingress/poll/scheduler.py`) — runs every `THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES`. Queries repos with `poll_enabled=True`. Respects per-repo `poll_interval_minutes` via `poll_last_run_at` tracking.
2. **Client** (`src/ingress/poll/client.py`) — fetches issues with conditional requests (`If-None-Match` / `If-Modified-Since`). Filters out pull requests. Raises `RateLimitError` on 403/429.
3. **Feed** (`src/ingress/poll/feed.py`) — generates a deterministic **synthetic delivery ID** (`poll-{owner}-{repo}-{issue}-{updated_at}`) for deduplication. Creates a TaskPacket and starts the workflow for each new issue.

**Preferred when:** No public URL (local dev, air-gapped, NAT-only), or as a backup when webhooks may be misconfigured.

## Convergence

Both paths produce the same output:

```
Webhook Event ─┐
               ├──► TaskPacket + Temporal Workflow ──► Pipeline (9 steps)
Poll Cycle ────┘
```

The **delivery ID** ensures at-most-once processing:
- Webhook: uses GitHub's `X-GitHub-Delivery` header
- Poll: uses `poll-{owner}-{repo}-{issue_number}-{updated_at}` (deterministic)

A unique constraint on `(delivery_id, repo)` in the `task_packet` table prevents duplicates regardless of intake path.

## Configuration

### Global (environment variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `THESTUDIO_INTAKE_POLL_ENABLED` | `false` | Master switch for poll intake |
| `THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES` | `10` | Global poll cycle interval |
| `THESTUDIO_INTAKE_POLL_TOKEN` | `""` | GitHub PAT or installation token |

### Per-repo (Admin UI or API)

| Field | Default | Description |
|-------|---------|-------------|
| `poll_enabled` | `false` | Enable polling for this repo |
| `poll_interval_minutes` | `null` (use global) | Override poll interval for this repo |

Set via Admin UI (repo detail > Repo Profile) or `PATCH /admin/repos/{id}/profile`.

## Rate Limit Protection

The poll path includes multiple layers of rate limit protection:

1. **Conditional requests** — `If-None-Match` (ETag) and `If-Modified-Since` headers minimize API calls. GitHub returns 304 (no rate limit cost) when nothing changed.
2. **Early exit** — when `x-ratelimit-remaining` drops below 50, the current cycle skips remaining repos.
3. **Retry-after** — on 403/429, the `retry-after` header is honored.
4. **Exponential backoff** — consecutive rate limits double the wait time (capped at 15 minutes).
5. **Cycle skip** — on any rate limit, remaining repos in the current cycle are skipped and retried next cycle.

## When to Use Each Path

| Scenario | Recommended Path |
|----------|-----------------|
| Public URL available | Webhook (real-time, no polling overhead) |
| No public URL (local dev, NAT) | Poll |
| Webhook delivery unreliable | Poll as backup |
| Air-gapped / firewall restrictions | Poll |
| High-volume repos (100+ issues/day) | Webhook (lower API usage) |

## Files

| File | Purpose |
|------|---------|
| `src/intake/` | Webhook intake (eligibility, label filter) |
| `src/ingress/poll/client.py` | GitHub API client with conditional requests |
| `src/ingress/poll/feed.py` | Synthetic delivery ID + pipeline feed |
| `src/ingress/poll/scheduler.py` | Background poll loop with per-repo intervals |
| `src/ingress/poll/models.py` | PollConfig, PollResult, RateLimitError |
| `src/ingress/dedupe.py` | Shared deduplication (both paths) |

## Further Reading

- [Poll-for-Issues Idea Doc](ideas/poll-for-issues-backup.md) — rationale and research
- [Deployment Guide](deployment.md) — environment variable reference
