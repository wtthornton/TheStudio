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
| 6. Implement | `implement_activity` | Sonnet 4.6 | In-process stub (no real file changes) — **wired later this session** |
| 7. Verify | `verify_activity` | — | Passed (stub) — **wired later this session** |
| 8. QA | `qa_activity` | Sonnet 4.6 | Failed — intent gap detected, loopback triggered |
| 6–8 (×2) | Loopbacks | | QA failed after 2 loopbacks, exhausted |

**Initial result:** `success: false`, `step_reached: qa`, `qa_loopbacks: 2`. Correct fail-closed behavior — QA correctly rejected stub implementation.

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

## Resolved Issues (all fixed 2026-03-20)

### 1. Implement activity — RESOLVED
**Was:** Stub returning hardcoded filenames.
**Fix:** `_implement_in_process()` now calls Claude to generate code, parses JSON output, and pushes files to a GitHub branch via the Contents API. See [first-real-issue.md](../eval-results/first-real-issue.md).

### 2. Intake agent parse failure with Haiku — KNOWN, LOW PRIORITY
Haiku 4.5 returns prose instead of JSON for the intake agent. The fallback handler catches it and defaults to `accepted=true, role=developer`. Works but should be tuned.

### 3. Publish activity — RESOLVED
**Was:** Not wired to real GitHubClient.
**Fix:** `_publish_real()` creates branch, draft PR, evidence comment, lifecycle labels. Also added `find_pr_by_head`, `create_or_update_file`, `mark_ready_for_review`, `enable_auto_merge` to `ResilientGitHubClient`.

### 4. Verify activity — RESOLVED
**Was:** Always returned `passed: True`.
**Fix:** Now validates that implement step produced actual file changes.

### 5. Intent spec not persisted — RESOLVED
**Was:** `intent_activity` returned output but never saved to DB.
**Fix:** Now persists intent spec via `create_intent()` so publisher can load it for evidence comment.

### 6. TaskPacket status transitions — RESOLVED
**Was:** Publisher tried `received → published` (invalid transition).
**Fix:** Publish activity advances through required status chain (`received → enriched → intent_built → in_progress → verification_passed`) before publishing.

## First Successful End-to-End Run (2026-03-20)

Pipeline processed [Issue #19](https://github.com/wtthornton/thestudio-production-test-rig/issues/19) → [Draft PR #20](https://github.com/wtthornton/thestudio-production-test-rig/pull/20):

| Step | Activity | Result |
|------|----------|--------|
| 1-5 | Intake → Assembler | All passed (LLM-powered) |
| 6 | Implement | LLM generated `text.py` + `test_text.py`, pushed to branch |
| 7 | Verify | 2 files confirmed on branch |
| 8 | QA | Passed first try (0 defects, no intent gaps) |
| 9 | Publish | Draft PR #20 created, evidence comment, `agent:done` + `tier:observe` labels |

**Duration:** ~2 minutes. **Cost:** ~$0.30. **Loopbacks:** 0.

## Remaining Next Steps

### P1: Process harder issues
Multi-file changes, bug fixes, refactoring tasks to validate pipeline robustness.

### P1: Onboard second repo
Test multi-repo support with real issues.

### P2: Wire remote verification
Run ruff/pytest on target repo via GitHub Actions or container (currently only checks file existence).

### P2: Fix intake agent Haiku parse reliability
Tune prompt or route intake to Sonnet.

### P3: Execute tier promotion
When ready for auto-merge with human approval gates.

### P3: Webhook ingress
Cloudflare tunnel or ngrok for real-time webhook delivery instead of polling.
