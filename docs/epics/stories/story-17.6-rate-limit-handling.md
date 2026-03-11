# Story 17.6 — Rate Limit Handling and Backoff

> **As a** platform operator,
> **I want** robust rate limit handling so polling never causes GitHub API abuse,
> **so that** the integration remains in good standing with GitHub.

**Purpose:** Repeated rate limit violations can result in GitHub blocking the integration. This story hardens rate limit handling so we honor `retry-after`, back off exponentially, and skip repos when near limits.

**Intent:** On 403/429, wait `retry_after` (or 60s), skip remaining repos this cycle, and log. If rate limited repeatedly, double wait (cap 15 min). Check `x-ratelimit-remaining` before each request; skip when < 50. No hammering; no secondary limit abuse.

**Points:** 3 | **Size:** S  
**Epic:** 17 — Poll for Issues as Backup to Webhooks  
**Sprint:** C (Stories 17.6–17.8)  
**Depends on:** Story 17.1, 17.3

---

## Description

Harden rate limit handling per GitHub best practices: honor `retry-after`, exponential backoff on repeated failures, and skip remaining repos when near rate limit.

## Tasks

- [ ] In poll client: on 403/429, raise `RateLimitError(retry_after=...)`; parse `retry-after` header (seconds)
- [ ] In scheduler: catch `RateLimitError`, wait `retry_after` seconds (or 60 if absent)
- [ ] On rate limit: skip remaining repos for this cycle; resume next cycle
- [ ] Exponential backoff: if rate limited N times in a row, double wait time (cap 15 min)
- [ ] Check `x-ratelimit-remaining` before each request; if < 50, skip remaining repos
- [ ] Structured log: `ingress.poll.rate_limited` with repo, retry_after

## Acceptance Criteria

- [ ] 403/429 triggers backoff and repo skip
- [ ] `retry-after` honored when present
- [ ] No repeated hammering after rate limit
- [ ] Unit tests: rate limit response handling

## Files Affected

| File | Action |
|------|--------|
| `src/ingress/poll/client.py` | Modify (rate limit detection) |
| `src/ingress/poll/scheduler.py` | Modify (backoff logic) |
| `tests/unit/test_ingress/test_poll_*.py` | Add rate limit tests |
