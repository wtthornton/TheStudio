# Idea: Poll for Issues as a Backup to Webhooks

**Status:** Idea (not planned)  
**Context:** TheStudio today receives GitHub issue events only via webhook. GitHub must POST to a URL that is reachable from the internet. If the deployment has no public URL (e.g. local or private network only), webhooks never arrive and the pipeline is not triggered by real issue events.

## Problem

- **Webhook requirement:** GitHub's servers need a public (or at least internet-reachable) URL to deliver events. No public URL ⇒ no automatic trigger from GitHub.
- **Impact:** Deployments without a public URL can run TheStudio with mock GitHub and use Admin UI, APIs, and the production test rig, but they cannot receive real issue events. Users who want "open an issue → pipeline runs" without exposing a webhook endpoint have no built-in alternative today.

## Idea: Poll for Issues as a Backup

Add an optional **polling** intake path that periodically checks configured repos for new or updated issues and enqueues work (e.g. creates TaskPackets or triggers the same pipeline as the webhook path). This would act as a **backup** when webhooks are not available, or as the **primary** intake in environments where the app is not publicly reachable.

### High-level behavior

1. **Configuration:** Per repo (or globally), enable "poll for issues" and set an interval (e.g. every 5 minutes). Use existing repo registration (owner, repo, installation_id) and GitHub App or PAT for API access.
2. **Poll step:** For each registered repo with polling enabled, call GitHub API (e.g. `GET /repos/{owner}/{repo}/issues`) with `since` or `state=open` and optional `sort=updated`. Identify issues not yet seen (e.g. by issue number + repo in a small store or DB).
3. **Feed pipeline:** For each new/updated issue, invoke the same intake path the webhook uses (build payload in webhook shape, create TaskPacket, start workflow) so the rest of the pipeline is unchanged.
4. **Deduplication:** Use a stable notion of "issue seen" (e.g. repo + issue number + optional updated_at) so the same issue is not processed repeatedly. Optionally align with existing webhook dedupe (delivery ID) by generating a synthetic delivery ID for poll-originated events.
5. **Rate limiting:** Respect GitHub API rate limits; back off or skip repos when near limits. Prefer GitHub App installation tokens over PAT when available.

### Benefits

- Works in environments with **no public URL** (e.g. dev, air-gapped, or NAT-only).
- **Backup** if webhooks are misconfigured or temporarily unreachable.
- Same pipeline and behavior as webhook; only the trigger mechanism differs.

### Considerations

- **Latency:** Polling is delayed (e.g. 5–15 minutes) vs near-instant webhooks. Acceptable for "backup" or "no webhook" scenarios; not a replacement for low-latency webhook where a public URL exists.
- **API usage:** More GitHub API calls; need to stay within rate limits and avoid unnecessary polling when webhooks are healthy.
- **Scope:** Document as "backup / no-public-URL" option; webhook remains the primary and preferred path when a public URL is available.

### Non-goals (for this idea)

- Replacing webhooks where a public URL exists.
- Real-time or sub-minute latency.
- Supporting all GitHub event types (issues-only is enough for the backup use case).

### Possible placement

- **Intake / ingress:** New module or background task (scheduler or Temporal workflow) that runs on an interval, calls GitHub API, and feeds the existing webhook-handler logic or TaskPacket creation.
- **Feature flag:** e.g. `THESTUDIO_INTAKE_POLL_ENABLED` and per-repo or global interval config, so polling is opt-in.

### References

- Current intake: `src/ingress/webhook_handler.py` (webhook only).
- Repo registration: Admin API and `src/repo/` (owner, repo, installation_id).
- Contract: Webhooks require a public URL; see `docs/deployment.md` and discussion of "no public URL" in handoff/sessions.

---

## Research & best practices (2025–2026)

*Review added to align the idea with GitHub API guidance and current codebase.*

### GitHub's stance on polling

- **Official guidance:** [Best practices for using the REST API](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api) states: *"You should subscribe to webhook events instead of polling the API for data."* So polling is explicitly a fallback; the doc's framing (backup / no-public-URL only) matches this.

### Rate limits and secondary limits

- **Primary:** 5,000 requests/hour (authenticated); GitHub App installation tokens are preferred over PATs (doc already calls this out).
- **Secondary limits:** 403/429 if too many requests too fast. Best practices:
  - Make requests **serially**, not concurrently.
  - For **mutative** requests (POST/PATCH/PUT/DELETE), wait ≥1 second between calls. Polling is GET-only, so this mainly affects any follow-up writes.
  - On rate limit: wait ≥1 minute, then exponential backoff; honor `retry-after` and `x-ratelimit-reset`.

### Reducing API usage when polling

1. **`GET /repos/{owner}/{repo}/issues`** supports:
   - `since` (ISO 8601) — only issues updated after that time.
   - `sort=updated`, `state=open` (or `all` if closed issues must be considered).
   - Pagination via `Link` headers (use them; do not construct URLs manually).
2. **Conditional requests:** Use `If-None-Match` (ETag) or `If-Modified-Since` (Last-Modified). A **304 Not Modified** response does **not** count against the primary rate limit (per GitHub docs). For list endpoints, Last-Modified is often more reliable than ETag when both exist.
3. **Per-repo ETag/Last-Modified:** Store the value from the last successful list response; on the next poll, send it. If 304, skip processing for that repo and avoid pagination for that run.

### Deduplication and pipeline alignment

- **Synthetic delivery ID:** The doc's suggestion to generate a synthetic delivery ID for poll-originated events is correct. The codebase uses `(delivery_id, repo)` as the unique key (`ix_taskpacket_delivery_repo`). A stable synthetic ID per (repo, issue_number, updated_at or similar) keeps dedupe in one place and preserves "at most once" semantics.
- **Webhook payload shape:** Reusing the same payload shape and `TaskPacketCreate(repo, issue_id, delivery_id, correlation_id)` so that `create_taskpacket` + `start_workflow` stay unchanged is the right approach (verified against `webhook_handler.py`).

### Implementation notes

- **PRs in issues endpoint:** `GET /repos/.../issues` returns both issues and PRs. Filter by absence of `pull_request` key in each item so only issues are fed into the pipeline (webhook is `issues`-event only).
- **Serial requests:** Process repos one after another and, within a repo, use pagination serially to avoid secondary rate limits.
- **Feature flag:** `THESTUDIO_INTAKE_POLL_ENABLED` plus per-repo or global interval is consistent with existing `THESTUDIO_*` feature flags in `docs/deployment.md`.

### Summary

The idea is consistent with 2025–2026 GitHub API best practices provided: (1) polling is clearly a backup when webhooks are unavailable or no public URL exists, (2) rate limits and conditional requests are handled as above, and (3) synthetic delivery IDs and existing webhook path reuse keep behavior and dedupe correct.
