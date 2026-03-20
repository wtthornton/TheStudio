# Session Prompt: First Real GitHub Issue at Observe Tier

## Context

**Phase 8, Post-Sprint 2** (2026-03-20). All 34 epics complete (27 deferred). Epic 33 P0 test harness fully delivered.

**What was done in Epic 33 Sprint 2 (2026-03-20):**
- Eval preflight guard: validates container LLM provider + API key match (8 tests)
- Results persistence: per-suite cost tracking, git SHA, failure details
- False-pass validation: credential_guard.py + tests proving runner rejects bad creds (7 tests)
- Documentation: setup guide, epic tracker, epic file all updated
- 1,865 unit tests passing, 14 P0 deployed, 4 GitHub integration, 6 Postgres integration. Zero failures. 84% coverage.

**What this session delivers:** Process the first real GitHub issue through the deployed stack at Observe tier. This is the milestone that proves TheStudio works end-to-end in production.

---

## Pre-Session Checklist

Before starting, verify:

1. **Commit Sprint 2 work** — there are ~30 uncommitted files from Epic 33 Sprint 2 and prior work. Commit first.
2. **Docker stack is running** — `cd infra && docker compose -f docker-compose.prod.yml up -d`
3. **P0 tests pass** — `./scripts/run-p0-tests.sh --skip-eval` (saves $5, validates stack health)
4. **Credentials in infra/.env** — real API key, PG password, admin creds, webhook secret

---

## Goal

Process one real GitHub issue through the deployed TheStudio stack:
1. Issue labeled `agent:run` is picked up by the intake webhook
2. Pipeline runs: Intake → Context → Intent → Router → Assembler → Implement → Verify → QA → Publish
3. A draft PR with an evidence comment is created on the test repo
4. The result is visible in the Admin UI at `https://localhost:9443/admin/ui/`

**Trust tier:** Observe — TheStudio creates the draft PR but does NOT auto-merge.

---

## Execution Steps

### Step 1: Verify Stack Health (15 min)

```bash
# Health check
./scripts/run-p0-tests.sh --health

# Verify admin UI is accessible
curl -k -u admin:YOUR_PASSWORD https://localhost:9443/admin/health
```

Confirm all services healthy: Caddy, App, Temporal, NATS, Postgres, pg-proxy.

### Step 2: Register Test Repository (10 min)

The test repo `wtthornton/thestudio-production-test-rig` should already be registered from P0 tests. Verify:

```bash
curl -k -u admin:YOUR_PASSWORD https://localhost:9443/admin/repos
```

If not registered:
```bash
curl -k -u admin:YOUR_PASSWORD -X POST https://localhost:9443/admin/repos \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "wtthornton",
    "repo": "thestudio-production-test-rig",
    "installation_id": 1,
    "default_branch": "main"
  }'
```

### Step 3: Configure Webhook (15 min)

Two options for getting issues to TheStudio:

**Option A: GitHub Webhook (recommended)**
1. Go to `wtthornton/thestudio-production-test-rig` > Settings > Webhooks
2. Add webhook:
   - **URL:** `https://YOUR_HOST:9443/webhook/github` (must be publicly reachable, or use ngrok/Cloudflare tunnel)
   - **Content type:** `application/json`
   - **Secret:** value of `THESTUDIO_WEBHOOK_SECRET` from `infra/.env`
   - **Events:** Issues only
3. Test with a ping delivery

**Option B: Poll Mode (if no public endpoint)**
Enable poll-based intake in `infra/.env`:
```ini
THESTUDIO_INTAKE_POLL_ENABLED=true
THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES=2
THESTUDIO_INTAKE_POLL_TOKEN=<github token with repo access>
```
Restart the app: `docker compose -f docker-compose.prod.yml restart app`

### Step 4: Create a Test Issue (5 min)

Create a simple issue on `wtthornton/thestudio-production-test-rig`:

```bash
gh issue create \
  --repo wtthornton/thestudio-production-test-rig \
  --title "Add a hello_world function to utils.py" \
  --body "Create a simple hello_world() function in utils.py that returns the string 'Hello, World!'. Include a docstring." \
  --label "agent:run"
```

**Why this issue:** It's trivially simple — one function, one file, clear acceptance criteria. If TheStudio can't handle this, we have a problem. If it can, we've proven the end-to-end pipeline works.

### Step 5: Monitor Pipeline Execution (10-30 min)

Watch the pipeline progress:

```bash
# Tail app logs
docker compose -f docker-compose.prod.yml logs -f app

# Check Admin UI for TaskPacket status
curl -k -u admin:YOUR_PASSWORD https://localhost:9443/admin/workflows
```

**Expected pipeline stages:**
1. `RECEIVED` — Webhook accepted, TaskPacket created
2. `INTAKE_COMPLETE` — Eligibility checked, issue is valid
3. `CONTEXT_COMPLETE` — Repository context enriched
4. `INTENT_COMPLETE` — Intent specification generated
5. `ROUTED` — Expert panel selected
6. `ASSEMBLED` — Expert outputs merged
7. `IMPLEMENTED` — Code changes generated
8. `VERIFIED` — Ruff + pytest passed on changes
9. `QA_COMPLETE` — QA agent validated intent compliance
10. `PUBLISHED` — Draft PR created with evidence comment

**If pipeline stalls:** Check logs for the specific stage failure. Common issues:
- `CONTEXT` stage: GitHub API rate limits or repo access
- `INTENT` stage: LLM timeout or malformed response
- `IMPLEMENT` stage: Code generation quality
- `VERIFY` stage: Lint or test failures (triggers loopback)
- `PUBLISH` stage: GitHub token permissions for PR creation

### Step 6: Validate the Output (15 min)

Once the TaskPacket reaches `PUBLISHED`:

1. **Check the draft PR** on `wtthornton/thestudio-production-test-rig`
   - Is there a new draft PR?
   - Does it contain the `hello_world()` function?
   - Is there an evidence comment with verification results?
   - Are lifecycle labels applied (`thestudio:draft`, `thestudio:observe`)?

2. **Check the Admin UI** at `https://localhost:9443/admin/ui/`
   - Is the TaskPacket visible in the workflow list?
   - Does the timeline show all 9 pipeline stages?

3. **Record the result** in `docs/eval-results/first-real-issue.md`:
   - Issue URL
   - PR URL
   - Pipeline duration
   - API cost (from admin cost dashboard)
   - Pass/fail for each pipeline stage
   - Any loopbacks or retries

### Step 7: Celebrate or Debug (variable)

**If it works:** TheStudio has successfully processed its first real GitHub issue. Document the result, take a screenshot of the Admin UI, and plan the next milestone (processing a harder issue, multi-repo, Execute tier promotion).

**If it fails:** This is expected and valuable — the failure reveals what to fix next. Document:
- Which pipeline stage failed
- The error message
- What fix is needed
- Whether it's a code bug, config issue, or LLM quality problem

---

## Technical Reference

**Key files:**
- `src/app.py` — FastAPI app with lifespan (auto-migration)
- `src/ingress/webhook_handler.py` — GitHub webhook intake
- `src/ingress/workflow_trigger.py` — Temporal workflow trigger
- `src/workflow/activities.py` — All pipeline stage activities
- `src/publisher/` — Draft PR creation + evidence comment
- `infra/docker-compose.prod.yml` — Production stack
- `docs/deployment.md` — Full deployment runbook
- `docs/URLs.md` — All endpoint URLs

**Feature flags that must be set for real execution:**
```ini
THESTUDIO_LLM_PROVIDER=anthropic
THESTUDIO_GITHUB_PROVIDER=real
THESTUDIO_STORE_BACKEND=postgres
```

**Observe tier behavior:**
- Draft PRs only (no auto-merge)
- Evidence comments included
- Lifecycle labels applied
- Human review required before merge

---

## Risks

| # | Risk | Mitigation |
|---|------|------------|
| R1 | Webhook endpoint not publicly reachable | Use poll mode (Option B) or ngrok/Cloudflare tunnel |
| R2 | LLM response quality poor for simple task | The hello_world issue is designed to be trivially simple |
| R3 | Pipeline stage timeout | Check Temporal UI at localhost:8088 for workflow status |
| R4 | GitHub token lacks push/PR permissions | Verify token scopes: `repo`, `workflow` |
| R5 | Cost exceeds expectations | Monitor via admin cost dashboard; budget ~$0.50 for one simple issue |

---

## After This Session

If the first real issue is processed successfully:

1. **Process a harder issue** — multi-file change, test generation, or bug fix
2. **Onboard a second repo** — test multi-repo support
3. **Review Observe tier metrics** — intent quality, verification pass rate, QA defect detection
4. **Plan Execute tier promotion** — when ready for auto-merge (with human approval gates)
5. **Production monitoring** — set up alerts for pipeline failures, cost anomalies, API rate limits
