# Onboarding a Real Repo at Observe Tier

Step-by-step guide for registering your first GitHub repository with TheStudio.

## Prerequisites

1. **Docker stack running:** `docker compose -f docker-compose.dev.yml up -d`
2. **Health check passes:** `curl http://localhost:8000/healthz` returns `{"status": "ok"}`
3. **GitHub App installed** on target repo (or use mock providers for testing)

## Step 1: Register the Repo

```bash
curl -X POST http://localhost:8000/admin/repos \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "your-org",
    "repo": "your-repo",
    "installation_id": 12345,
    "default_branch": "main"
  }'
```

Expected response: `201 Created` with repo profile JSON.

Or use the Admin UI: navigate to `http://localhost:8000/admin/ui/repos` and click "Register Repo".

## Step 2: Configure Webhook

In your GitHub repo settings:

1. Go to **Settings > Webhooks > Add webhook**
2. **Payload URL:** `https://your-domain/webhook/github` (or `http://localhost:8000/webhook/github` for local)
3. **Content type:** `application/json`
4. **Secret:** Match `THESTUDIO_WEBHOOK_SECRET` in your environment
5. **Events:** Select "Issues" (and optionally "Issue comments")

## Step 3: Verify Connectivity

Create a test issue in your repo with the label `agent:run`. TheStudio will:

1. Receive the webhook (check `/admin/ui/workflows` for the TaskPacket)
2. Run the 9-step pipeline: Intake > Context > Intent > Router > Assembler > Agent > Verify > QA > Publish
3. Create a draft PR with an evidence comment

## Step 4: Monitor

- **Dashboard:** `http://localhost:8000/admin/ui/dashboard` — fleet health, queue depth
- **Workflows:** `http://localhost:8000/admin/ui/workflows` — individual task status
- **Metrics:** `http://localhost:8000/admin/ui/metrics` — success rates, loopback counts

## Trust Tiers

| Tier | Behavior | Promotion Criteria |
|------|----------|-------------------|
| **Observe** (default) | Draft PRs only, human review required | Initial registration |
| **Suggest** | PRs marked ready-for-review when V+QA pass | Compliance checker passes |
| **Execute** | Auto-merge (future) | Full compliance + track record |

New repos always start at Observe. Promote via Admin UI or API.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| Webhook returns 401 | Verify `THESTUDIO_WEBHOOK_SECRET` matches GitHub webhook secret |
| Webhook returns 200 (no TaskPacket) | Issue missing `agent:run` label, or duplicate delivery ID |
| Pipeline stuck at "in_progress" | Check Temporal UI at `localhost:8233` for workflow status |
| Verification fails repeatedly | Check ruff/pytest output in workflow history; max 2 loopbacks |
| No PR created | Check Publisher logs; verify GitHub token has repo write permissions |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `THESTUDIO_DATABASE_URL` | Yes | PostgreSQL connection string |
| `THESTUDIO_TEMPORAL_HOST` | Yes | Temporal server address |
| `THESTUDIO_NATS_URL` | Yes | NATS JetStream address |
| `THESTUDIO_WEBHOOK_SECRET` | Yes | GitHub webhook HMAC secret |
| `THESTUDIO_ENCRYPTION_KEY` | Yes | Fernet key for secret encryption |
| `THESTUDIO_LLM_PROVIDER` | No | `anthropic` (real) or `mock` (default) |
| `THESTUDIO_GITHUB_PROVIDER` | No | `github` (real) or `mock` (default) |
