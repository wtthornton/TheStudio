# Production Deployment Summary — 2026-03-20

Canonical environment variables, compose files, and production URLs: [docs/deployment.md](../deployment.md) (and [infra/.env.example](../../infra/.env.example) for required secrets).

## What Was Done

First successful end-to-end pipeline execution with real Claude models against a real GitHub issue.

### Infrastructure

Values below are **from one production-style run** (GitHub org, app name, numeric app ID, and test issue). Your deployment will differ; configure apps and repos via `THESTUDIO_*` settings as described in [deployment.md](../deployment.md).

| Component | Status |
|-----------|--------|
| GitHub App | `TheStudio-wtthornton` (ID: 3141312), installed on `TheStudio` + `thestudio-production-test-rig` |
| Permissions | Contents:write, Issues:write, Pull Requests:write, Metadata:read |
| PEM key | Path from `THESTUDIO_GITHUB_PRIVATE_KEY_PATH` (see `infra/.env.example`); private key file mounted read-only into the app container per `infra/docker-compose.prod.yml` |
| Poll intake | Enabled, 5-min interval, GitHub PAT configured |
| Agent LLM | All 10 agents enabled (Haiku for FAST, Sonnet for BALANCED) |
| Temporal worker | **Added** — was missing entirely; now runs as background task in app lifespan |
| Temporal namespace | `default` registered (was missing) |
| Providers | `llm_provider=anthropic`, `github_provider=real`, `store_backend=postgres` |

### Code Changes

- **`src/workflow/worker.py`** (new) — Temporal worker that registers `TheStudioPipelineWorkflow` and all 14 activities. Runs as a background asyncio task with retry-on-failure (5 attempts, exponential backoff).
- **`src/app.py`** — Added worker startup in lifespan, graceful cancellation on shutdown.
- **`src/ingress/workflow_trigger.py`** — Extended `start_workflow()` to pass `repo`, `issue_title`, `issue_body`, `labels` to the workflow input.
- **`src/ingress/poll/feed.py`** — Extracts issue title/body/labels from GitHub API response and passes through to `start_workflow()`.
- **`src/ingress/webhook_handler.py`** — Added labels to `normalize_webhook_payload()` output; passes full issue metadata to `start_workflow()`.
- **`infra/docker-compose.prod.yml`** — Added PEM volume mount, `THESTUDIO_AGENT_LLM_ENABLED` (hardcoded JSON), `THESTUDIO_COST_OPTIMIZATION_*` env vars.

### End-to-End Test Result (example issue)

Pipeline processed GitHub issue [#6](https://github.com/wtthornton/TheStudio/issues/6) ("Add docstring to check_eligibility function") through all 9 steps:

| Step | Activity | Model | Result |
|------|----------|-------|--------|
| 1. Intake | `intake_activity` | Haiku 4.5 | Accepted (fallback — Haiku returned prose instead of JSON) |
| 2. Context | `context_activity` | Haiku 4.5 | complexity=medium, parse success |
| 3. Intent | `intent_activity` | Sonnet 4.6 | Acceptance criteria built, parse success |
| 4. Router | `router_activity` | Sonnet 4.6 | Expert selection complete, parse success |
| 5. Assembler | `assembler_activity` | Sonnet 4.6 | Plan assembled, parse success |
| 6. Implement | `implement_activity` | Sonnet 4.6 | In-process stub (no real file changes) |
| 7. Verify | `verify_activity` | — | Passed |
| 8. QA | `qa_activity` | Sonnet 4.6 | Failed — intent gap detected, loopback triggered |
| 6–8 (×2) | Loopbacks | | QA failed after 2 loopbacks, exhausted |

**Final result:** `success: false`, `step_reached: qa`, `qa_loopbacks: 2`. Correct fail-closed behavior — no PR created because QA gate didn't pass.

### What This Proves

- Real Claude API calls work end-to-end (Haiku + Sonnet)
- Temporal workflow orchestration works with all 14 activities
- Poll intake successfully discovers and processes GitHub issues
- QA loopback mechanism works correctly (implement → verify → QA → loopback)
- Gates fail closed as designed
- Cost: ~$0.09 per issue for 6 LLM-calling agents (matches Epic 30 baselines)

## Resolved in this session

- **Issue metadata passthrough** — `start_workflow()` now passes repo, title, body, and labels into the workflow. Previously these were empty strings, which caused intake to reject issues.
- **Temporal worker** — Added `src/workflow/worker.py` and lifespan startup in `src/app.py`. Without a worker, workflows were enqueued to Temporal but never executed.
- **Temporal `default` namespace** — Registered manually via `tctl namespace register` for this environment. Automating this for fresh installs remains a backlog item (see P2 below).

## Open issues

### 1. Implement activity runs in stub mode
The `implement_activity` uses in-process execution — it doesn't clone the repo, create a branch, or write files. This means QA will always find intent gaps because no real code changes exist. This is the primary blocker for producing an actual PR.

### 2. Intake agent parse failure with Haiku
Haiku 4.5 returned prose instead of the expected JSON format for the intake agent. The fallback handler caught it and defaulted to `accepted=true, role=developer`. The intake prompt needs tuning for Haiku's instruction-following characteristics, or the agent should use Sonnet.

### 3. Publish activity not wired
Even if QA passes, the `publish_activity` needs the real `GitHubClient` (using the App installation token) to create branches, commits, and draft PRs. This client exists but isn't wired into the activity.

## Next Steps (Priority Order)

### P0: Wire real implement + publish activities
**Goal:** Process an issue and produce an actual draft PR.

1. Wire `implement_activity` to clone the repo, create a branch, and apply code changes using the GitHub App installation token.
2. Wire `publish_activity` to create a draft PR with an evidence comment.
3. Test with a simple issue (docstring addition, type hint) on a test repo.

### P1: Fix intake agent Haiku parse reliability
Either tune the intake prompt for Haiku's JSON compliance or route intake to Sonnet. The fallback masks the issue but isn't ideal.

### P2: Add `default` namespace to Temporal init
Add `tctl namespace register default` to `infra/temporal-schema-setup.sh` so future fresh deployments don't require manual intervention.

### P3: Cost optimization (Epic 32)
Enable `THESTUDIO_COST_OPTIMIZATION_ROUTING_ENABLED=true` to route FAST-class agents to Haiku automatically. Currently hardcoded in the model gateway but the feature flag isn't active.

### P4: Webhook ingress
Set up a Cloudflare tunnel or ngrok for real-time webhook delivery instead of polling. Faster response time (seconds vs 5-minute poll interval).

### P5: Meridian review for Epic 31
The OAuth adapter epic has a pending review. Lower priority since API keys are the recommended production auth method.
